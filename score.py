#encoding=utf-8
import json
import os
import subprocess
import re
import csv
import argparse
import pickle
import numpy as np

import bdmetric as bd

from vutil import *
from arguments import *

# x264 conclusion demo:
# encoded 100 frames, 18.98 fps, 770.82 kb/s
x264_res = re.compile('encoded (?P<frames>\d+) frames, (?P<fps>[\d.]+) fps, (?P<kbps>[\d.]+) kb/s')
def x264_log_process(msg):
    lines = msg.split('\n')
    res = lines[-2]
    x264_match = x264_res.match(res)
    score_dict = x264_match.groupdict()
    ret = { "total_frames": int(score_dict["frames"]),
            "process_fps" : float(score_dict["fps"]),
            "bitrate" : float(score_dict["kbps"]),
          }
    return ret

def exe_x264_cmd(cmd):
    pinfo(cmd)
    output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
    print("out=[\n%s]" % output)
    return x264_log_process(output)

def exe_cmd(cmd):
    pinfo(cmd)
    process = os.popen(cmd)
    output = process.read()
    # output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
    # print("out=[%s]" % output)

def get_csv_name(val, kbps):
    return "res_" + val + "_"+ str(kbps) + "kpbs";

def get_main_name(ref_name, val, kbps):
    return "main_" + ref_name + "_" + val + "_"+ str(kbps) + "kpbs";

def get_json_name(main):
    return main + "_score";

def load_config(conf_path):
    pinfo("load config file [%s]" % conf_path)
    with open(conf_path, 'r') as conf_file:
        conf = json.load(conf_file)
    if (not "type" in conf or
        not conf["type"] in ["encoder", "refs"]):
        perror("section type not in configure file or type is wrong[type=%s]" % conf["type"])
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
            x264_cmd = enc_cmd_patern.format(
                    x264_bin=conf_enc["bin_path"],
                    comm_par=conf_enc["comm_par"],
                    test_par=conf_enc["test_par"],
                    in_file=ref["file"],
                    in_par="--input-res " + ref["dim"],
                    bitrate=str(kbps),
                    test_val=val,
                    out=main_file
                    )
            res = exe_x264_cmd(x264_cmd)
            out_files[main_file] = res;

    # calc psnr/vmaf/ssim score and save to json
    pdebug(out_files)
    for main_file in out_files:
        print(main_file)
        [_, main_name, _] = sep_path_segs(main_file)
        cmd = eval_cmd_patern.format(
                    main = main_file,
                    ref = ref_file,
                    ref_dim=ref["dim"],
                    log_path=log_dir + get_json_name(main_name) + ".json"
                    )
        exe_cmd(cmd)

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
                scores_tmp[kbps] = {
                        "ref": ref_file,
                        "main": main_file,
                        "test_par": conf_enc["test_par"],
                        "test": val,
                        "target": kbps,
                        "bitrate": out_files[main_file]["bitrate"],
                        "vmaf": score["VMAF score"],
                        "psnr": score["PSNR score"],
                        "ssim": score["SSIM score"],
                        "size": os.path.getsize(main_file)
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
    csv_file = log_dir + "ares_" + ref_name + ".csv"
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
                    score["test"], score["target"], score["bitrate"],
                    score["psnr"], score["ssim"], score["vmaf"]
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

eval_cmd_patern = 'ffmpeg -i {main} -s:v {ref_dim} -i {ref} -filter_complex \
[0:v][1:v]libvmaf=psnr=1:ssim=1:phone_model=0:log_path={log_path}:log_fmt=json \
-f null -'
enc_cmd_patern = "{x264_bin} {in_par} {comm_par} --bitrate {bitrate} \
{test_par} {test_val} -o {out} {in_file}"

out_dir = "out/"
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

