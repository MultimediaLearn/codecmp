import os
import csv
import glob

import score
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font

from util.vutil import *
from arguments import *
from util.xlsx_tool import *

def save_refs(res, ws, ws_fig):
    # print(res)
    head = ["file", "psnr", "ssim", "vmaf", "enc_name", "par"]
    if ws.dimensions == "A1:A1":
        print(head)
        ws.append(head)
        xlsx_ws_bold_row(ws, 1)
    fig_pos_row = 1
    for ref_key in res:
        bd_refs = res[ref_key]
        _, yuv_file = os.path.split(ref_key)
        for par_key in bd_refs:
            enc_name, bd, bd_fig = bd_refs[par_key]
            content = [ yuv_file,
                round(bd["psnr"], 5), round(bd["ssim"], 5), round(bd["vmaf"], 5),
                enc_name, par_key
                ]
            ws.append(content)
            print(content)
            anchor_cell = "A" + str(fig_pos_row)
            ws_fig[anchor_cell] = yuv_file
            ws_fig[anchor_cell].font = Font(bold=True)
            anchor_cell = "A" + str(fig_pos_row + 1)
            img = openpyxl.drawing.image.Image(bd_fig)
            ws_fig.add_image(img, anchor_cell)
            fig_pos_row += 20
    xlsx_ws_neg_bg(ws, 1, 1)
    xlsx_ws_bold_col(ws, "A")

if __name__ == "__main__":
    print("Input arguments list:")
    print(pretty_args(args, tabs="  "))
    init_logger(level=logging.INFO, logfile=args.res + "." + str(args.resume) + ".log")
    pwarn("Input arguments list:")
    pwarn(pretty_args(args, tabs="  "))

    enc = args.enc
    refs = args.refs
    resume = args.resume
    uid = args.id
    res_file = args.res
    wb = Workbook()
    ws_bdrate = wb.active
    ws_bdrate.title = "bdrate"
    ws_fig = wb.create_sheet("figure")
    ws_infos = wb.create_sheet("details")

    # create path directory
    [res_path, _, _] = sep_path_segs(res_file)
    if (res_path):
        make_dir(res_path)

    if os.path.isfile(refs):
        pwarn("single file mode: %s" % refs)
        csv_file = res_file
        _, yuv_name = os.path.split(refs)
        res = score.eval(enc, refs, resume, wb)
        save_refs(res, ws_bdrate, ws_fig)
        xlsx_col_fit(wb)
        wb.save(res_file)
    elif os.path.isdir(refs):
        pwarn("directory/batch mode: %s" % refs)
        for fname in glob.iglob(refs + "*.json"):
            csv_file = res_file
            _, yuv_name = os.path.split(fname)
            res = score.eval(enc, fname, resume, wb)
            save_refs(res, ws_bdrate, ws_fig)
            xlsx_col_fit(wb)
            wb.save(res_file)
    else:
        perror("unknown refs file/dir [%s]" % refs)
        exit(-1)

xlsx_col_fit(wb)
wb.save(res_file)
