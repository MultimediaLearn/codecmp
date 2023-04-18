#encoding=utf-8
import csv
import numpy as np

from .bdmetric import BD_RATE
from .vutil import *

def bdrate(ref_bitrate, ref_metric, main_bitrate, main_metric):
    return BD_RATE(np.array(ref_bitrate), np.array(ref_metric),
                      np.array(main_bitrate), np.array(main_metric))

# scores = {}, key1: test_value, key2: bitrates, value: vmaf/psnr/ssim
# bdmetrics()
def scores_calc(csv_file, ref_name, bd_ref_name, val_ref, scores):
    bd_ref = []         # bdrate 计算参考数据，[(码率，[psnrs, ssims, vmafs]), ...]
    bd_mains = {}       # {"enc_name": {"test_val": bd_in}}

    # 汇总原始码率和 psnr/vmaf/ssim 信息
    with open_csv(csv_file, "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["enc_name", "target_kbps", "kbps", "real_kbps", "bps_error", "file_size",
                         "psnr", "ssim", "vmaf", "parameter"])
        for enc_name in scores:
            if enc_name in ["_ref_"]:
                continue
            enc_score = scores[enc_name]
            for test_val in enc_score:
                bd_in = []
                scores_test = enc_score[test_val]
                target_sorted = sorted(scores_test, reverse=True)
                kbitrates = []
                metrics = {}
                metrics["psnr"] = []
                metrics["ssim"] = []
                metrics["vmaf"] = []
                for kbps in target_sorted:
                    score = scores_test[kbps]
                    writer.writerow([
                        enc_name,
                        score["rc"],
                        round(score["bitrate"], 2),
                        round(score["rbitrate"], 2),
                        score["size"],
                        round(score["psnr"], 5),
                        round(score["ssim"], 5),
                        round(score["vmaf"], 5),
                        score["test_par"] + " " + score["test_val"]
                        ])
                    kbitrates.append(score["rbitrate"])
                    metrics["psnr"].append(score["psnr"])
                    metrics["ssim"].append(score["ssim"])
                    metrics["vmaf"].append(score["vmaf"])
                # [0]: [1000, 2000, 3000, ...]
                # [1]: {
                #       "psnr": [80, 90, 91, ...]
                #       "ssim": [81, 90, 92, ...]
                #       "vmaf": [82, 90, 93, ...]
                #       }
                bd_in.append(kbitrates)
                bd_in.append(metrics)

                if enc_name == bd_ref_name and (val_ref is None or test_val == val_ref):
                    bd_ref = bd_in
                    bd_ref_name = enc_name
                else:
                    if enc_name not in bd_mains:
                        bd_mains[enc_name] = {}
                    bd_mains[enc_name][test_val] = bd_in

    print(bd_mains)
    bd_ref_bitrates = bd_ref[0]
    bd_ref_metrics = bd_ref[1]
    bdrates_ref = {}
    for enc_name in bd_mains: # 多个测试条件bdrate计算
        print("*" * 100, enc_name)
        enc_item = bd_mains[enc_name]
        for key_main in enc_item:
            print("---------[" + bd_ref_name + " " + str(val_ref) + "] VS [" +
                                 enc_name + " " + str(key_main) + "]------------")
            bd_in = enc_item[key_main]
            kbitrates = bd_in[0]
            metrics = bd_in[1]
            bds = {}
            for key in metrics: # psnr, ssim vmaf
                print("---------[" + str(key) + "]------------")
                metric = metrics[key]
                pdebug(np.array(bd_ref_bitrates))
                pdebug(np.array(bd_ref_metrics[key]))
                pdebug(np.array(kbitrates))
                pdebug(np.array(metric))
                bd = bdrate(bd_ref_bitrates, bd_ref_metrics[key], kbitrates, metric)
                pinfo(bd) # 一个值
                bds[key] = bd
            bdrates_ref[enc_name + ' ' + str(key_main)] = bds

    return bdrates_ref
