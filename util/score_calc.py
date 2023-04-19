#encoding=utf-8
import os
import csv
import numpy as np
import openpyxl
import matplotlib.pyplot as plt
from openpyxl import Workbook

from .bdmetric import BD_RATE
from .vutil import *
from .xlsx_tool import xlsx_ws_bold_row

def bdrate(ref_bitrate, ref_metric, main_bitrate, main_metric):
    return BD_RATE(np.array(ref_bitrate), np.array(ref_metric),
                      np.array(main_bitrate), np.array(main_metric))

# scores = {}, key1: test_value, key2: bitrates, value: vmaf/psnr/ssim
# bdmetrics()
def scores_calc(csv_file, yuv_file, bd_ref_name, val_ref, scores, wb: Workbook):
    val_ref_key = ""
    bd_ref = []         # bdrate 计算参考数据，[(码率，[psnrs, ssims, vmafs]), ...]
    bd_mains = {}       # {"enc_name": {"test_val": bd_in}}
    ws = wb.get_sheet_by_name("details")
    _, yuv_file = os.path.split(yuv_file)
    csv_path, _ = os.path.split(csv_file)

    # 汇总原始码率和 psnr/vmaf/ssim 信息
    with open_csv(csv_file, "w") as f:
        writer = csv.writer(f, delimiter=",")
        head = ["yuv_name", "enc_name", "kbps", "real_kbps", "bps_error",
                "psnr", "ssim", "vmaf", "parameter"]
        writer.writerow(head)
        if ws.dimensions == "A1:A1":
            ws.append(head)
            xlsx_ws_bold_row(ws, 1)

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
                    bps_error = (score["rbitrate"] - score["bitrate"]) / score["bitrate"] * 100
                    content = [
                        yuv_file,
                        enc_name,
                        round(score["bitrate"], 2),
                        round(score["rbitrate"], 2),
                        round(bps_error, 2),
                        round(score["psnr"], 5),
                        round(score["ssim"], 5),
                        round(score["vmaf"], 5),
                        score["test_par"] + " " + score["test_val"]
                        ]
                    # yuv_file = ""   # 清空 yuv_file
                    writer.writerow(content)
                    ws.append(content)
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
                    val_ref_key = score["test_par"] + " " + test_val
                else:
                    if enc_name not in bd_mains:
                        bd_mains[enc_name] = {}
                    bd_mains[enc_name][score["test_par"] + "_" + test_val] = (bd_in)

    bd_ref_bitrates = bd_ref[0]
    bd_ref_metrics = bd_ref[1]
    bdrates_ref = {}
    for enc_name in bd_mains: # 多个测试条件bdrate计算
        enc_item = bd_mains[enc_name]
        for key_main in enc_item:
            pdebug("---------[" + bd_ref_name + " " + str(val_ref_key) + "] VS [" +
                                 enc_name + " " + str(key_main) + "]------------")
            bd_in = enc_item[key_main]
            kbitrates = bd_in[0]
            metrics = bd_in[1]
            bds = {}
            fig, axes = plt.subplots(1, len(metrics))
            fig.set_size_inches(10, 3)
            ind = 0
            for key in metrics: # psnr, ssim vmaf
                pdebug("---------[" + str(key) + "]------------")
                metric_main = metrics[key]
                ref_metric = bd_ref_metrics[key]
                pdebug(np.array(bd_ref_bitrates))
                pdebug(np.array(ref_metric))
                pdebug(np.array(kbitrates))
                pdebug(np.array(metric_main))
                bd, rets = bdrate(bd_ref_bitrates, ref_metric, kbitrates, metric_main)
                pinfo("%s %s %s %s: bdrate=%.2f", yuv_file, enc_name, key_main, key, bd) # 一个值
                axs = axes[ind]
                ind += 1
                axs.plot(rets[0], rets[1], linestyle='dotted', marker='o', color="green")   # ref
                axs.plot(rets[2], rets[3], linestyle='solid', marker='*', color="blue")    # main
                axs.set_title(key, fontsize=11, color="red")
                bds[key] = bd
            png_tmp = os.path.join(csv_path, "_".join([yuv_file, enc_name, key_main]) + ".png")
            fig.suptitle(yuv_file, fontsize=12)
            fig.savefig(png_tmp)
            plt.close()

            bdrates_ref[str(key_main)] = (enc_name, bds, png_tmp)

    return bdrates_ref
