import re

from vutil import *

# Width:          160
# Height:         120
# Frames:         100
# encode time:    0.029496 sec
# FPS:            3390.290209 fps
re_res = re.compile('.*Frames:\s+(?P<frames>\d+);encode time:\s+(?P<fps>[\d.]+) sec.*')
def _log_process(msg):
    lines = msg.split('\n')
    msg = ";".join(lines)
    res_match = re_res.match(msg)
    if (not res_match):
        return
    score_dict = res_match.groupdict()
    ret = { "total_frames": int(score_dict["frames"]),
            "process_fps" : float(score_dict["fps"])
          }
    return ret

_cmd_pattern = "{enc_bin} -org {in_file} {comm_par} -sw {sw} -sh {sh} -frin {in_fps}\
        -dw 0 {d0w} -dh 0 {d0h} -ltarb 0 {bitrate} -frout 0 {out0_fps}  -bf {out} -trace 1"
def run_eval(conf_enc, ref, kbps, val, main_file):
    cmd = _cmd_pattern.format(
            enc_bin=conf_enc["bin_path"],
            comm_par=conf_enc["comm_par"],
            test_par=conf_enc["test_par"],
            test_val=val,
            in_file=ref["file"],
            bitrate=str(kbps),
            sw=ref["dim_w"],
            sh=ref["dim_h"],
            d0w=ref["dim_w"],
            d0h=ref["dim_h"],
            in_fps=ref["fps"],
            out0_fps=ref["fps"],
            out=main_file
            )

    res = exe_enc_cmd(cmd, _log_process)
    return res

