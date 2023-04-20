import re

from .vutil import *

# x264 conclusion demo:
# encoded 100 frames, 18.98 fps, 770.82 kb/s
x264_res = re.compile('encoded (?P<frames>\d+) frames, (?P<fps>[\d.]+) fps, (?P<kbps>[\d.]+) kb/s')
def _log_process(msg: str):
    lines = msg.split('\n')
    res = lines[-2]
    res_match = x264_res.match(res)
    score_dict = res_match.groupdict()
    ret = { "total_frames": int(score_dict["frames"]),
            "process_fps" : float(score_dict["fps"]),
            "bitrate" : float(score_dict["kbps"]),
          }
    return ret

# -r 不指定framerate，指定的是 fps
_cmd_pattern = "{enc_bin} {in_par} {comm_par} {rc} --fps {fps} --keyint {key_gap} --min-keyint {key_gap} \
{test_par} {test_val} -o {out} {in_file}"
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
    x264_cmd = _cmd_pattern.format(
            enc_bin=conf_enc["bin_path"],
            comm_par=" ".join(conf_enc["comm_pars"]),
            test_par=test_par,
            test_val=test_val,
            in_file=ref["file"],
            in_par="--input-res " + str(ref["dim_w"]) + "x" + str(ref["dim_h"]),
            rc=rc_str,
            fps=ref["fps"],
            key_gap=ref["fps"] * 2,
            out=main_file
            )
    res = exe_log_cmd(x264_cmd, _log_process)
    return res

