import re

from .vutil import *

# Width:          160
# Height:         120
# Frames:         100
# encode time:    0.029496 sec
# FPS:            3390.290209 fps
re_res = re.compile('.*Frames:\s+(?P<frames>\d+);encode time:\s+(?P<fps>[\d.]+) sec;FPS:.*')
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

# -rc 0 must set
_cmd_pattern = "{enc_bin} -org {in_file} {comm_par} {test_par} {test_val} \
-sw {sw} -sh {sh} -frin {in_fps} -iper {iper} \
-dw 0 {d0w} -dh 0 {d0h} -frout 0 {out0_fps} \
{rc} -bf {out} -trace 3" # open warning log
def run_eval(conf_enc, ref, kbps, val, main_file):
    test_par = ""
    test_val = ""
    if val is not None:
        test_val = val
        test_par = conf_enc["test_par"]
    rc_str = " ".join(conf_enc["rcs"])
    rc_str = rc_str.format(
        target_br=int(kbps),
        vbv_br=int(kbps * 1.05)
    )
    cmd = _cmd_pattern.format(
            enc_bin=conf_enc["bin_path"],
            comm_par=" ".join(conf_enc["comm_pars"]),
            test_par=test_par,
            test_val=test_val,
            in_file=ref["file"],
            rc=rc_str,
            sw=ref["dim_w"],
            sh=ref["dim_h"],
            d0w=ref["dim_w"],
            d0h=ref["dim_h"],
            in_fps=ref["fps"],
            iper=ref["fps"] * 2,
            out0_fps=ref["fps"],
            out=main_file
            )

    res = exe_log_cmd(cmd, _log_process)
    return res

