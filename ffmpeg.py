import os
from vutil import *

_cmd_patern = 'ffmpeg -i {main} -s:v {ref_dim} -i {ref} -filter_complex \
[0:v][1:v]libvmaf=psnr=1:ssim=1:phone_model=0:log_path={log_path}:log_fmt=json \
-f null -'

def run_eval(main_file, ref_file, dim, log_path):
    cmd = _cmd_patern.format(
                main = main_file,
                ref = ref_file,
                ref_dim=dim,
                log_path=log_path
                )

    return exe_cmd(cmd)
