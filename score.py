#encoding=utf-8
import json
import subprocess
import re
import csv
import argparse
import pickle
import numpy as np

import util.bdmetric as bd
import util.ffmpeg as ff
import util.x264 as x264
import util.openh264 as openh264

from util.vutil import *
from arguments import *

def get_csv_name(ref):
    return "ares_" + ref + "_"+ uid

def get_main_name(ref_name, val, rc):
    rc_str = rc.replace(" ", "_").replace("-", "")
    return "main_" + ref_name + "_" + val + "_"+ rc_str + "_" + uid

def get_json_name(main):
    return main + "_score"

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
# TODO(vacing): split loop by json generation to support resume
def score_ref_calc(conf_enc, ref):
    out_files = {}
    ref_file = ref["file"]
    [_, ref_name, _] = sep_path_segs(ref_file)

    # step1: encode, 遍历码率点和测试参数设定，得到编码输出信息(264文件名，帧数、fps、码率)
    for val in conf_enc["test_value"]:
        for rc in conf_enc["bitrate_points"]:
            main_file = ref_dir + get_main_name(ref_name, val, rc) + ".264"
            # 分开类别方便解析输出
            if (conf_enc["class"] == "x264"):
                res = x264.run_eval(conf_enc, ref, rc, val, main_file)
            elif (conf_enc["class"] == "openh264"):
                res = openh264.run_eval(conf_enc, ref, rc, val, main_file)
            else:
                perror("unkonwn encoder " + conf_enc["class"])
                exit(-1)
            out_files[main_file] = res

    # step2: 使用ffmpeg 命令行，calc psnr/vmaf/ssim score and save to json
    pdebug(out_files)
    for main_file in out_files:
        [_, main_name, _] = sep_path_segs(main_file)
        log_path=log_dir + get_json_name(main_name) + ".json"
        dim = str(ref["dim_w"]) + "x" + str(ref["dim_h"])
        ff.run_eval(main_file, ref_file, dim, log_path)

    # 汇总分析
    scores = {}     # key1: test_value, key2: rc, value: vmaf/psnr/ssim
    for val in conf_enc["test_value"]:
        print(conf_enc["test_par"] + " " + val + ":")
        scores_tmp = {}
        for rc in conf_enc["bitrate_points"]:
            # 重新得到 264 文件名(step1 key)
            main_name = get_main_name(ref_name, val, rc)
            main_file = ref_dir + main_name + ".264"
            # 重新得到 json 文件名(step2 结果)
            json_path = log_dir + get_json_name(main_name) + ".json"
            with open(json_path, 'r') as score_f:
                score = json.load(score_f)
                filesize = os.path.getsize(main_file)
                frames = out_files[main_file]["total_frames"]
                bitrate = 0
                if ("bitrate" in out_files[main_file] and
                    out_files[main_file]["bitrate"]):
                    bitrate = out_files[main_file]["bitrate"]
                else:
                    bitrate = filesize * 8.0 / 1000 / frames * ref["fps"]
                    pwarn("estimated bitrate=%f" % bitrate)

                # 汇总step1 和 step2结果
                # TODO(vacing): unify bitrate caculation
                scores_tmp[rc] = {
                        "ref": ref_file,
                        "main": main_file,
                        "test_par": conf_enc["test_par"],
                        "test": val,
                        "rc": rc,
                        "rbitrate": bitrate, # kbps
                        "frames": frames,
                        "vmaf": score['pooled_metrics']["vmaf"]['mean'],
                        "psnr": score['pooled_metrics']["psnr_y"]['mean'],
                        "ssim": score['pooled_metrics']["float_ssim"]['mean'],
                        "size": filesize
                    }
            print("rc:" + rc + "\t")
            print(scores_tmp)
        scores[val] = scores_tmp

    return scores

def bdrate(ref_bitrate, ref_metric, main_bitrate, main_metric):
    return bd.BD_RATE(np.array(ref_bitrate), np.array(ref_metric),
                      np.array(main_bitrate), np.array(main_metric))

# scores = {}, key1: test_value, key2: bitrates, value: vmaf/psnr/ssim
# bdmetrics()
def scores_calc(ref_name, val_ref, scores):
    csv_file = log_dir + get_csv_name(ref_name) + ".csv"
    pinfo(csv_file)
    bd_ref = []         # bdrate 计算参考数据，[(码率，[psnrs, ssims, vmafs]), ...]
    bd_mains = {}       # bdrate 目标数据集，多个bdrate数据
    test_par = str()

    # 汇总原始码率和 psnr/vmaf/ssim 信息
    with open_csv(csv_file, "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["target_kbps", "real_kbps", "bps_error", "file_size",
                         "psnr", "ssim", "vmaf", "parameter"])
        for test_val in scores:
            bd_in = []
            if test_val == val_ref:
                bd_in = bd_ref

            scores_test = scores[test_val]
            target_sorted = sorted(scores_test, reverse=True)
            kbitrates = []
            metrics = {}
            metrics["psnr"] = []
            metrics["ssim"] = []
            metrics["vmaf"] = []
            for kbps in target_sorted:
                score = scores_test[kbps]
                if not test_par:
                    test_par = score["test_par"]
                writer.writerow([
                    score["rc"],
                    round(score["rbitrate"], 2),
                    score["size"],
                    round(score["psnr"], 5),
                    round(score["ssim"], 5),
                    round(score["vmaf"], 5),
                    score["test_par"] + " " + score["test"]
                    ])
                kbitrates.append(score["rbitrate"])
                metrics["psnr"].append(score["psnr"])
                metrics["ssim"].append(score["ssim"])
                metrics["vmaf"].append(score["vmaf"])
            # [0]: [1000, 2000, 3000, ...]
            # [1]: {
            #       "psnr": [80, 90, 91, ...]
            #       "ssim": [81, 90, 92, ...]
            #       "vmaf": [82, 90, 93, ...]
            #       }
            bd_in.append(kbitrates)
            bd_in.append(metrics)
            if test_val != val_ref:
                bd_mains[test_val] = bd_in

    bd_ref_bitrates = bd_ref[0]
    bd_ref_metrics = bd_ref[1]
    bdrates_ref = {}
    for key_main in bd_mains: # 多个测试条件bdrate计算
        print("---------[" + test_par + " " + str(val_ref) + "] VS [" +
                             test_par + " " + str(key_main) + "]------------")
        bd_in = bd_mains[key_main]
        kbitrates = bd_in[0]
        metrics = bd_in[1]
        bds = {}
        for key in metrics: # psnr, ssim vmaf
            print("---------[" + str(key) + "]------------")
            metric = metrics[key]
            pdebug(np.array(bd_ref_bitrates))
            pdebug(np.array(bd_ref_metrics[key]))
            pdebug(np.array(kbitrates))
            pdebug(np.array(metric))
            bd = bdrate(bd_ref_bitrates, bd_ref_metrics[key], kbitrates, metric)
            pinfo(bd) # 一个值
            bds[key] = bd
        bdrates_ref[test_par + ' ' + str(key_main)] = bds

    return bdrates_ref

def eval(enc_json, refs_json, resume):
    conf_enc = load_config(enc_json)    # 加载编码配置信息
    conf_enc = conf_enc["encs"][0]
    conf_refs = load_config(refs_json)  # 加载编码参考YUV文件信息
    conf_refs = conf_refs["refs"]

    bdrates_all = {}
    for ref in conf_refs:
        ref_file = ref["file"]
        [_, ref_name, _] = sep_path_segs(ref_file)
        scores_cache_path = cache_dir + ref_name + "_scores_cache.pkl"
        if (resume and os.path.isfile(scores_cache_path)):
            # 恢复状态
            with open(scores_cache_path, "rb") as f:
                scores = pickle.load(f)
        else:
            # 重新计算
            scores = score_ref_calc(conf_enc, ref)
            with open(scores_cache_path, "wb") as f:
                pickle.dump(scores, f)

        # 得到 bdrate计算基准
        test_val_ref_ind = conf_enc["test_value_ref_ind"]
        test_val_ref = conf_enc["test_value"][test_val_ref_ind]
        # 计算bdrate
        bdrates_ref = scores_calc(ref_name, test_val_ref, scores)
        bdrates_all[ref_file] = bdrates_ref

    return bdrates_all

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
    print("Input arguments list:")
    print(pretty_args(args, tabs="  "))
    if args.resume:
        pwarn("will resume the previous process")
    else:
        pwarn("will rerun all process")

    print(eval(args.enc, args.refs, args.resume))

