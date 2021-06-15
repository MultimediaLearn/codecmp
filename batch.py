import os
import csv
import glob

import score

from vutil import *
from arguments import *

def save_refs(writer, res):
    print(res)
    for ref_key in res:
        bd_refs = res[ref_key]
        for par_key in bd_refs:
            bd = bd_refs[par_key]
            writer.writerow([
                round(bd["psnr"], 5), round(bd["ssim"], 5), round(bd["vmaf"], 5),
                ref_key, par_key
                ])

if __name__ == "__main__":
    print "Input arguments list:",
    print(pretty_args(args, tabs="  "))

    enc = args.enc
    refs = args.refs
    resume = args.resume
    uid = args.id
    res_path = args.res
    res_path_open_mode = "w"

    # create path directory
    [csv_path, _, _] = sep_path_segs(res_path)
    if (csv_path):
        print csv_path
        make_dir(csv_path)

    if os.path.isfile(res_path):
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
        with open_csv(csv_file, "w") as f:
            writer = csv.writer(f, delimiter=",")
            res = score.eval(enc, refs, resume)
            save_refs(writer, res)
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
            with open_csv(csv_file, res_path_open_mode) as f:
                writer = csv.writer(f, delimiter=",")
                res = score.eval(enc, fname, resume)
                save_refs(writer, res)
    else:
        perror("unknown refs file/dir [%s]" % refs)
        exit(-1)

