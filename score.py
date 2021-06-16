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
    return "ares_" + ref + "_"+ uid;

def get_main_name(ref_name, val, kbps):
    return "main_" + ref_name + "_" + val + "_"+ str(kbps) + "kpbs_" + uid;

def get_json_name(main):
    return main + "_score";

def load_config(conf_path):
    pinfo("load config file [%s]" % conf_path)
    with open(conf_path, 'r') as conf_file:
        conf = json.load(conf_file)
    if (not "type" in conf or
        not conf["type"] in ["encoder", "refs"]):
        perror("section type not in configure file or type is wrong[type=%s]" % conf_path)
        exit(1)
    return conf

# ref with different encode parameters: bitrate x test_value
# TODO(vacing): split loop by json generation to support resume
def score_ref_calc(conf_enc, ref):
    out_files = {}
    ref_file = ref["file"]
    [_, ref_name, _] = sep_path_segs(ref_file)

    # encode
    for val in conf_enc["test_value"]:
        for kbps in ref["bitrates"]:
            main_file = ref_dir + get_main_name(ref_name, val, kbps) + ".264"
            if (conf_enc["class"] == "x264"):
                res = x264.run_eval(conf_enc, ref, kbps, val, main_file)
            elif (conf_enc["class"] == "openh264"):
                res = openh264.run_eval(conf_enc, ref, kbps, val, main_file)
            out_files[main_file] = res;

    # calc psnr/vmaf/ssim score and save to json
    pdebug(out_files)
    for main_file in out_files:
        [_, main_name, _] = sep_path_segs(main_file)
        log_path=log_dir + get_json_name(main_name) + ".json"
        dim = str(ref["dim_w"]) + "x" + str(ref["dim_h"])
        ff.run_eval(main_file, ref_file, dim, log_path)

    scores = {}     # key1: test_value, key2: bitrates, value: vmaf/psnr/ssim
    for val in conf_enc["test_value"]:
        print(conf_enc["test_par"] + " " + val + ":")
        scores_tmp = {}
        for kbps in ref["bitrates"]:
            main_name = get_main_name(ref_name, val, kbps)
            main_file = ref_dir + main_name + ".264"
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
                    bitrate = filesize / frames * ref["fps"]
                    pwarn("estimated bitrate=%f" % bitrate)

                scores_tmp[kbps] = {
                        "ref": ref_file,
                        "main": main_file,
                        "test_par": conf_enc["test_par"],
                        "test": val,
                        "target": kbps,
                        "bitrate": bitrate,
                        "frames": frames,
                        "vmaf": score["VMAF score"],
                        "psnr": score["PSNR score"],
                        "ssim": score["SSIM score"],
                        "size": filesize
                    }
            print "bitrate:" + str(kbps) + "\t",
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
    bd_ref = []
    bd_mains = {}
    test_par = str()

    with open_csv(csv_file, "w") as f:
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
                writer = csv.writer(f, delimiter=",")
                writer.writerow([
                    score["target"], score["bitrate"],
                    score["psnr"], score["ssim"], score["vmaf"],
                    score["test_par"] + " " + score["test"]
                    ])
                kbitrates.append(score["bitrate"])
                metrics["psnr"].append(score["psnr"])
                metrics["ssim"].append(score["ssim"])
                metrics["vmaf"].append(score["vmaf"])
            bd_in.append(kbitrates)
            bd_in.append(metrics)
            if test_val != val_ref:
                bd_mains[test_val] = bd_in

    bd_ref_bitrates = bd_ref[0]
    bd_ref_metrics = bd_ref[1]
    bdrates_ref = {}
    for key_main in bd_mains:
        print("---------[" + test_par + " " + str(val_ref) + "] VS [" +
                             test_par + " " + str(key_main) + "]------------")
        bd_in = bd_mains[key_main]
        kbitrates = bd_in[0]
        metrics = bd_in[1]
        bds = {}
        for key in metrics:
            print("---------[" + str(key) + "]------------")
            metric = metrics[key]
            pdebug(np.array(bd_ref_bitrates))
            pdebug(np.array(bd_ref_metrics[key]))
            pdebug(np.array(kbitrates))
            pdebug(np.array(metric))
            bd = bdrate(bd_ref_bitrates, bd_ref_metrics[key],
                   kbitrates, metric)
            pinfo(bd)
            bds[key] = bd
        bdrates_ref[test_par + ' ' + str(key_main)] = bds

    return bdrates_ref

def eval(enc_json, refs_json, resume):
    conf_enc = load_config(enc_json)
    conf_enc = conf_enc["enc"]
    conf_refs = load_config(refs_json)
    conf_refs = conf_refs["refs"]

    bdrates_all = {}
    for ref in conf_refs:
        ref_file = ref["file"]
        [_, ref_name, _] = sep_path_segs(ref_file)
        scores_cache_path = cache_dir + ref_name + "_scores_cache.pkl"
        if (resume and os.path.isfile(scores_cache_path)):
            with open(scores_cache_path, "r") as f:
                scores = pickle.load(f)
        else:
            scores = score_ref_calc(conf_enc, ref)
            with open(scores_cache_path, "w") as f:
                pickle.dump(scores, f)

        test_val_ref_ind = conf_enc["test_value_ref_ind"]
        test_val_ref = conf_enc["test_value"][test_val_ref_ind]
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

if __name__ == "__main__":
    print "Input arguments list:",
    print(pretty_args(args, tabs="  "))
    if args.resume:
        pwarn("will resume the previous process")
    else:
        pwarn("will rerun all process")

    print(eval(args.enc, args.refs, args.resume))

