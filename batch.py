import os
import csv
import glob

import score
from openpyxl import Workbook

from util.vutil import *
from arguments import *

def save_refs(writer, res, ws):
    print(res)
    head = ["file", "enc_name", "psnr", "ssim", "vmaf", "par"]
    writer.writerow(head)
    ws.append(head)
    for ref_key in res:
        bd_refs = res[ref_key]
        _, yuv_file = os.path.split(ref_key)
        for par_key in bd_refs:
            enc_name, bd = bd_refs[par_key]
            content = [ yuv_file, enc_name,
                round(bd["psnr"], 5), round(bd["ssim"], 5), round(bd["vmaf"], 5),
                par_key
                ]
            writer.writerow(content)
            ws.append(content)

if __name__ == "__main__":
    print("Input arguments list:")
    print(pretty_args(args, tabs="  "))

    enc = args.enc
    refs = args.refs
    resume = args.resume
    uid = args.id
    res_path = args.res
    res_path_open_mode = "w"
    wb = Workbook()

    # create path directory
    [csv_path, _, _] = sep_path_segs(res_path)
    if (csv_path):
        print(csv_path)
        make_dir(csv_path)

    if not os.path.exists(res_path) or os.path.isfile(res_path):
        # if is path, has been created, not exists
        # if exists, check is file (may existed file)
        # so, is file, recreate it
        res_path_open_mode = "a"
        # create first, or isfile() check would be fail
        with open_csv(res_path, "w") as f:
            pass
    
    if os.path.isfile(refs):
        pwarn("single file mode: %s" % refs)
        if os.path.isfile(res_path):
            csv_file = res_path
        else:
            [_, ref_conf_name, _] = sep_path_segs(refs)
            csv_file = res_path + "bdmetrics_" + ref_conf_name + "_" + str(uid) + ".csv"
        pinfo(csv_file)
        _, yuv_name = os.path.split(refs)
        ws = wb.create_sheet(yuv_name)
        with open_csv(csv_file, "w") as f:
            writer = csv.writer(f, delimiter=",")
            res = score.eval(enc, refs, resume, wb)
            save_refs(writer, res, ws)
    elif os.path.isdir(refs):
        pwarn("directory/batch mode: %s" % refs)
        for fname in glob.iglob(refs + "*.json"):
            pinfo(fname)
            if os.path.isfile(res_path):
                csv_file = res_path
            else:
                [_, ref_conf_name, _] = sep_path_segs(fname)
                csv_file = res_path + "bdmetrics_" + ref_conf_name + ".csv"
            pinfo(csv_file)
            _, yuv_name = os.path.split(fname)
            ws = wb.create_sheet(yuv_name)
            with open_csv(csv_file, res_path_open_mode) as f:
                writer = csv.writer(f, delimiter=",")
                res = score.eval(enc, fname, resume, wb)
                save_refs(writer, res, ws)
    else:
        perror("unknown refs file/dir [%s]" % refs)
        exit(-1)

wb.save("res.xlsx")
