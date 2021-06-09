#encoding=utf-8
import json
import os

import vutil

exe = False
def exe_cmd(cmd):
    print(cmd)
    if (not exe):
        return

    process = os.popen(cmd)
    output = process.read()

def get_main_name(val):
    return "out_" + val;

def get_json_name(ref, main):
    return ref + "_" + main;

def load_config(conf_path):
    with open(conf_path, 'r') as conf_file:
        conf = json.load(conf_file)
    if (not "test" in conf or
        not "x264" in conf):
        print("section test or x264 not in configure file")
        exit(1)
    return conf

eval_cmd_patern = 'ffmpeg -i {main} -s:v {ref_dim} -i {ref} -filter_complex \
[0:v][1:v]libvmaf=psnr=1:ssim=1:phone_model=0:log_path={log_path}:log_fmt=json \
-f null -'
x264_cmd_patern = "{x264_bin} {in_par} {comm_par} {test_par} {test_val} -o {out} {in_file}"
out_dir = "out/"
log_dir = out_dir + "log/"
vutil.make_dir(out_dir)
vutil.make_dir(log_dir)

if __name__ == "__main__":
    out_files = []
    conf = load_config("conf.json")
    conf_test = conf["test"]
    ref_file = conf_test["ref"]["file"]
    [_, ref_name, _] = vutil.sep_path_segs(ref_file)

    conf_x264 = conf["x264"]
    for val in conf_x264["test_value"]:
        main_file = out_dir + get_main_name(val) + ".264"
        x264_cmd = x264_cmd_patern.format(
                x264_bin=conf_x264["bin_path"],
                comm_par=conf_x264["comm_par"],
                test_par=conf_x264["test_par"],
                in_file=conf["test"]["ref"]["file"],
                in_par="--input-res " + conf["test"]["ref"]["dim"],
                test_val=val,
                out=main_file
                )
        exe_cmd(x264_cmd)
        out_files.append(main_file)

    for main_file in out_files:
        [_, main_name, _] = vutil.sep_path_segs(main_file)
        cmd = eval_cmd_patern.format(
                    main = main_file,
                    ref = ref_file,
                    ref_dim="1920x1080", 
                    log_path=log_dir + get_json_name(ref_name, main_name) + ".json"
                    )
        exe_cmd(cmd)

    scores = {}
    for val in conf_x264["test_value"]:
        main = get_main_name(val)
        main_file = out_dir + main + ".264"
        json_path = log_dir + get_json_name(ref_name, main) + ".json"
        with open(json_path, 'r') as score_f:
            score = json.load(score_f)
            scores[val] = {
                    "vmaf": round(score["VMAF score"], 5),
                    "psnr": round(score["PSNR score"], 5),
                    "ssim": round(score["SSIM score"], 5),
                    "size": os.path.getsize(main_file)
                }
            print(scores[val])

