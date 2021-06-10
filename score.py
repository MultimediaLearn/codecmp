#encoding=utf-8
import json
import os
import subprocess
import re
import csv

import vutil

exe = True

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
    vutil.pinfo(cmd)
    if (not exe):
        return

    output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
    print("out=[\n%s]" % output)
    return x264_log_process(output)

def exe_cmd(cmd):
    vutil.pinfo(cmd)
    if (not exe):
        return

    process = os.popen(cmd)
    output = process.read()
    # output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
    # print("out=[%s]" % output)

def open_csv(filename, mode='r'):
    """Open a csv file in proper mode depending on Python verion."""
    return(open(filename, mode=mode+'b') if bytes is str else
           open(filename, mode=mode, newline=''))

def get_csv_name(val, kbps):
    return "res_" + val + "_"+ str(kbps) + "kpbs";

def get_main_name(val, kbps):
    return "main_" + val + "_"+ str(kbps) + "kpbs";

def get_json_name(ref, main):
    return ref + "_" + main;

def scores2csv(scores):
    csv_file = res_dir + "res.csv"
    print(csv_file)
    with open_csv(csv_file, "w") as f:
        for key in scores:
            score = scores[key]
            writer = csv.writer(f, delimiter=",")
            writer.writerow([
                score["test"], score["target"], score["bitrate"],
                score["psnr"], score["ssim"], score["vmaf"]
                ])

def load_config(conf_path):
    with open(conf_path, 'r') as conf_file:
        conf = json.load(conf_file)
    if (not "test" in conf or
        not "x264" in conf):
        vutil.perror("section test or x264 not in configure file")
        exit(1)
    return conf

eval_cmd_patern = 'ffmpeg -i {main} -s:v {ref_dim} -i {ref} -filter_complex \
[0:v][1:v]libvmaf=psnr=1:ssim=1:phone_model=0:log_path={log_path}:log_fmt=json \
-f null -'
x264_cmd_patern = "{x264_bin} {in_par} {comm_par} --bitrate {bitrate} \
{test_par} {test_val} -o {out} {in_file}"

out_dir = "out/"
log_dir = out_dir + "log/"
res_dir = out_dir + "res/"
vutil.make_dir(out_dir)
vutil.make_dir(log_dir)
vutil.make_dir(res_dir)

if __name__ == "__main__":
    out_files = {}
    conf = load_config("conf.json")
    conf_test = conf["test"]
    ref_file = conf_test["ref"]["file"]
    [_, ref_name, _] = vutil.sep_path_segs(ref_file)

    conf_x264 = conf["x264"]
    for val in conf_x264["test_value"]:
        for kbps in conf_test["ref"]["bitrate"]:
            main_file = out_dir + get_main_name(val, kbps) + ".264"
            x264_cmd = x264_cmd_patern.format(
                    x264_bin=conf_x264["bin_path"],
                    comm_par=conf_x264["comm_par"],
                    test_par=conf_x264["test_par"],
                    in_file=conf["test"]["ref"]["file"],
                    in_par="--input-res " + conf["test"]["ref"]["dim"],
                    bitrate=str(kbps),
                    test_val=val,
                    out=main_file
                    )
            res = exe_x264_cmd(x264_cmd)
            print(res)
            out_files[main_file] = res;

    print(out_files)
    for main_file in out_files:
        print(main_file)
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
        print(conf_x264["test_par"] + " " + val + ":")
        for kbps in conf_test["ref"]["bitrate"]:
            main = get_main_name(val, kbps)
            main_file = out_dir + main + ".264"
            json_path = log_dir + get_json_name(ref_name, main) + ".json"
            with open(json_path, 'r') as score_f:
                score = json.load(score_f)
                scores[main_file] = {
                        "test": val,
                        "vmaf": round(score["VMAF score"], 5),
                        "psnr": round(score["PSNR score"], 5),
                        "ssim": round(score["SSIM score"], 5),
                        "size": os.path.getsize(main_file),
                        "target": kbps,
                        "bitrate": out_files[main_file]["bitrate"]
                    }
            print "bitrate:" + str(kbps) + "\t",
            print(scores[main_file])
    scores2csv(scores)
