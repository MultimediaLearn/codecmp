import os
from .vutil import *

_ffmpeg_path = '/data/home/vacingfang/FFmpeg/install_vmaf/bin/ffmpeg'
_cmd_patern = '{ffmpeg_path} -i {main} -s:v {ref_dim} -i {ref} -filter_complex \
[0:v][1:v]libvmaf=feature="name=psnr|name=float_ssim":\
log_path={log_path}:log_fmt=json:shortest=1 \
-f null -'

def run_eval(main_file, ref_file, dim, log_path):
    cmd = _cmd_patern.format(
                ffmpeg_path = _ffmpeg_path,
                main = main_file,
                ref = ref_file,
                ref_dim=dim,
                log_path=log_path
                )

    return exe_cmd(cmd)
