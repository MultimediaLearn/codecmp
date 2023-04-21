#encoding=utf-8
import json
import subprocess
import re
import csv
import argparse
import pickle
import numpy as np
from openpyxl import Workbook

import util.bdmetric as bd
import util.ffmpeg as ff
import util.x264 as x264
import util.openh264 as openh264

from util.vutil import *
from util.score_calc import scores_calc
from arguments import *

def get_csv_name(ref):
    return "ares_" + ref + "_"+ uid

def get_main_name(enc_name, ref_name, val_str, rc):
    rc_str = str(rc)
    return ref_name + "_" + enc_name + "_" + val_str + "_"+ rc_str + "_" + uid

def load_config(conf_path):
    pinfo("load config file [%s]" % conf_path)
    with open(conf_path, 'r') as conf_file:
        conf = json.load(conf_file)
    if (not "type" in conf or
        not conf["type"] in ["encoder", "refs"]):
        perror("section type not in configure file or type is wrong[type=%s]" % conf_path)
        exit(1)
    return conf

# ref with different encode parameters: rc x test_value
def enc_score_calc(conf_enc, ref):
    out_files = {}
    ref_file = ref["file"]
    [_, ref_name, _] = sep_path_segs(ref_file)
    enc_name = conf_enc["name"]

    scores = {}     # key1: test_value, key2: rc, value: vmaf/psnr/ssim
    vals = conf_enc["test_value"]
    for val in vals:
        val_str = "None" if val is None else val
        par_str = "None" if val is None else conf_enc["test_par"]
        score_rcs = {}
        for rc_val in ref["bitrates"]:
            score_tmp = {}
            main_name = get_main_name(enc_name, ref_name, val_str, rc_val)
            score_cache = os.path.join(log_dir, main_name + ".pkl")
            if resume and os.path.isfile(score_cache):
                pwarn("encode result %s use CACHED result", score_cache)
                with open(score_cache, "rb") as f:
                    score_tmp = pickle.load(f)
                score_rcs[rc_val] = score_tmp
                continue

            main_file = os.path.join(ref_dir, main_name + ".264")
            json_path = os.path.join(log_dir, main_name + ".json")

            # step1: encode, 遍历码率点和测试参数设定，得到编码输出信息(264文件名，帧数、fps、码率)
            if (conf_enc["class"] == "x264"):
                res = x264.run_eval(conf_enc, ref, rc_val, val, main_file)
            elif (conf_enc["class"] == "openh264"):
                res = openh264.run_eval(conf_enc, ref, rc_val, val, main_file)
            else:
                perror("unkonwn encoder " + conf_enc["class"])
                exit(-1)
            out_files[main_file] = res

            # step2: 使用ffmpeg 命令行，calc psnr/vmaf/ssim score and save to json
            dim = str(ref["dim_w"]) + "x" + str(ref["dim_h"])
            ff.run_eval(main_file, ref_file, dim, json_path)

            # step3: 汇总分析
            with open(json_path, 'r') as score_f:
                score = json.load(score_f)
                filesize = os.path.getsize(main_file)
                frames = out_files[main_file]["total_frames"]
                # TODO(vacing): unify bitrate caculation
                bitrate = 0
                if ("bitrate" in out_files[main_file] and
                    out_files[main_file]["bitrate"]):
                    bitrate = out_files[main_file]["bitrate"]
                else:
                    bitrate = filesize * 8.0 / 1000 / frames * ref["fps"]
                    pwarn("estimated bitrate=%f" % bitrate)

                # 汇总step1 和 step2结果
                score_tmp = {
                        "ref": ref_file,
                        "main": main_file,
                        "test_par": par_str,
                        "test_val": val_str,
                        "bitrate": rc_val,   # kbps
                        "rbitrate": bitrate, # kbps
                        "frames": frames,
                        "vmaf": score['pooled_metrics']["vmaf"]['mean'],
                        "psnr": score['pooled_metrics']["psnr_y"]['mean'],
                        "ssim": score['pooled_metrics']["float_ssim"]['mean'],
                        "size": filesize
                    }

            # 缓存一个码点的编码结果
            score_rcs[rc_val] = score_tmp
            with open(score_cache, "wb") as f:
                pickle.dump(score_tmp, f)
        scores[val_str] = score_rcs

    return scores

def eval(enc_json, refs_json, resume, wb: Workbook):
    ref_yuvs = load_config(refs_json)  # 加载编码参考YUV文件信息
    ref_yuvs = ref_yuvs["refs"]

    enc_scores = {}     # {"enc_name": {"test_val": {"rc": {infos} } } }
    bdrates_all = {}
    conf_encs = load_config(enc_json)    # 加载编码配置信息
    for yuv in ref_yuvs:
        yuv_file = yuv["file"]
        pinfo(f"process {yuv_file}")
        [_, ref_name, _] = sep_path_segs(yuv_file)
        csv_file = os.path.join(cache_dir, get_csv_name(ref_name) + ".csv")
        scores_cache_path = os.path.join(cache_dir, ref_name + "_scores_cache.pkl")

        if (resume and os.path.isfile(scores_cache_path)):
            # 恢复状态
            pwarn("yuv file %s use CACHED result", yuv_file)
            with open(scores_cache_path, "rb") as f:
                enc_scores = pickle.load(f)
        else:
            for conf_enc in conf_encs["encs"]:
                enc_name = conf_enc["name"]
                has_test_value = True
                if "test_value" not in conf_enc:
                    has_test_value = False
                    conf_enc["test_value"] = [None]
                    conf_enc["test_par"] = [None]
                if "ref_ind" in conf_enc:
                    ref_ind = conf_enc["ref_ind"] if has_test_value else None
                    enc_scores["_ref_"] = (conf_enc, ref_ind)

                # 重新计算
                enc_score = enc_score_calc(conf_enc, yuv)
                enc_scores[enc_name] = enc_score

            # 保存状态
            with open(scores_cache_path, "wb") as f:
                pickle.dump(enc_scores, f)

        # 得到 bdrate计算基准
        if "_ref_" not in enc_scores:
            perror("reference not found in scores:")
            perror(enc_scores)
            return None
        (bd_ref_enc, bd_ref_ind) = enc_scores["_ref_"]
        bd_ref_name = bd_ref_enc["name"]
        test_val_ref = None
        if bd_ref_ind is not None:
            test_val_ref = bd_ref_enc["test_value"][bd_ref_ind]
        # 计算bdrate
        bdrates_ref = scores_calc(csv_file, yuv_file, bd_ref_name, test_val_ref, enc_scores, wb)
        bdrates_all[yuv_file] = bdrates_ref

    return bdrates_all

resume = args.resume
uid = args.id
out_dir = "out_" + str(uid) + "/"
log_dir = out_dir + "log/"
ref_dir = out_dir + "res_ref/"
cache_dir = out_dir + "cache/"
make_dir(out_dir)
make_dir(log_dir)
make_dir(ref_dir)
make_dir(cache_dir)

# Input:
#   - 一个文件
#   - (码点集合 x 测试参数取值序列)
# Output:
#  - 每个参数取值的bdrate 曲线(3条：psnr, ssim, vmaf)(由多个码点计算得到)
if __name__ == "__main__":
    wb = Workbook()
    pwarn("Input arguments list:")
    pwarn(pretty_args(args, tabs="  "))
    if args.resume:
        pwarn("will resume the previous process")
    else:
        pwarn("will rerun all process")

    pinfo(eval(args.enc, args.refs, args.resume, wb))

