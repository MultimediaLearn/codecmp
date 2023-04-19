import subprocess
import re
import os

def exe_log_cmd(cmd, log_process):
    print(cmd)
    output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    print("out=[\n%s]" % output)
    if log_process is None:
        return None
    return log_process(output)

probe_res = re.compile('.*Video.*, (?P<resolution>[\dx]+), (?P<bitrate>[\d]+) kb/s, (?P<fps>[\d]+) fps.*')
def _log_process(msg: str):
    res_match = probe_res.search(msg, re.DOTALL)
    if res_match is None:
        print("match is None")
        return None
    score_dict = res_match.groupdict()
    ret = { "resolution": str(score_dict["resolution"]),
            "bitrate" : float(score_dict["bitrate"]),
            "fps" : float(score_dict["fps"]),
          }
    return ret

convert_pattern = "ffmpeg -i {file} -pix_fmt yuv420p -f rawvideo {out} -y"
probe_pattern = "ffprobe -hide_banner {file}"
def process_video(in_file, out_path):
    probe_cmd = probe_pattern.format(file=in_file)
    out = exe_log_cmd(probe_cmd, _log_process)
    if out is None:
        print(f"process {in_file} failed")
        return

    resolution = out["resolution"]
    bitrate = out["bitrate"]
    fps = out["fps"]
    _, filename = os.path.split(in_file)
    in_name, _ = os.path.splitext(filename)
    out_file = os.path.join(out_path,
                            "_".join([in_name, resolution, str(int(fps+0.5))+"fps", str(int(bitrate))+"kbps"]) +
                            ".yuv")
    convert_cmd = convert_pattern.format(file=in_file, out=out_file)
    exe_log_cmd(convert_cmd, None)

if __name__ == "__main__":
    in_path = "/data/home/vacingfang/video/trtc_test"
    out_path = "/data/home/vacingfang/video/trtc_test/yuv"
    video_suffix = ".mp4"
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    for filename in os.listdir(in_path):
        if not filename.endswith(video_suffix):
            print(f"file ignored {filename}")
            continue

        in_file = os.path.join(in_path, filename)
        process_video(in_file, out_path)



