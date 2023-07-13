import os
import re
from .vutil import *

# [Parsed_ssim_8 @ 0x4130740] SSIM Y:0.985482 (18.381053) U:0.990687 (20.309243) V:0.990750 (20.338605) All:0.987228 (18.937352)
# [Parsed_psnr_7 @ 0x2daaa40] PSNR y:42.074994 u:48.509772 v:48.124636 average:43.348000 min:40.409366 max:48.395323
ssim_res = re.compile('\[Parsed_ssim_.*\] SSIM.* All:(?P<ssim_all>[\d.]+) \(.*\)')
psnr_res = re.compile('\[Parsed_psnr_.*\] PSNR.* average:(?P<psnr_avg>[\d.]+) min:.*')
def ff_metric_get(msg: str):
    ssim_all = 0
    psnr_avg = 0
    lines = msg.split('\n')
    for res in lines:
        res_match = ssim_res.match(res)
        if res_match:
            ssim_all = float(res_match.groupdict()["ssim_all"])
        res_match = psnr_res.match(res)
        if res_match:
            psnr_avg = float(res_match.groupdict()["psnr_avg"])
    return {ssim_all, psnr_avg}

_ffmpeg_path = '/data/home/vacingfang/FFmpeg/install_vmaf/bin/ffmpeg'
_cmd_patern = '{ffmpeg_path} -i {main} -s:v {ref_dim} -i {ref} -filter_complex "\
[0:v]settb=AVTB,setpts=PTS-STARTPTS[main];[1:v]settb=AVTB,setpts=PTS-STARTPTS[ref];\
[main]split=3[main1][main2][main3];[ref]split=3[ref1][ref2][ref3];\
[main1][ref1]libvmaf=feature=name=psnr|name=float_ssim:log_path={vmaf_log_path}:log_fmt=json:shortest=1;\
[main2][ref2]psnr=stats_file={psnr_log_path};\
[main3][ref3]ssim=stats_file={ssim_log_path}\
" -f null -'

def run_eval(main_file, ref_file, dim, log_path):
    cmd = _cmd_patern.format(
                ffmpeg_path = _ffmpeg_path,
                main = main_file,
                ref = ref_file,
                ref_dim=dim,
                vmaf_log_path=log_path,
                psnr_log_path=log_path + "_psnr.log",
                ssim_log_path=log_path + "_ssim.log",
                )

    return exe_log_cmd(cmd, ff_metric_get)
