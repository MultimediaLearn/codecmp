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
                bd["psnr"], bd["ssim"], bd["vmaf"],
                ref_key, par_key
                ])

if __name__ == "__main__":
    print "Input arguments list:",
    print(pretty_args(args, tabs="  "))

    enc = args.enc
    refs = args.refs
    resume = args.resume
    res_path = args.res
    make_dir(res_path)
    
    if os.path.isfile(refs):
        pwarn("single file mode: %s" % refs)
        [_, ref_conf_name, _] = sep_path_segs(refs)
        csv_file = res_path + "bdmetrics_" + ref_conf_name + ".csv"
        pinfo(csv_file)
        with open_csv(csv_file, "w") as f:
            writer = csv.writer(f, delimiter=",")
            res = score.eval(enc, refs, resume)
            save_refs(writer, res)
    elif os.path.isdir(refs):
        pwarn("single file mode: %s" % refs)
        for fname in glob.iglob(refs + "*.json"):
            pinfo(fname)
            [_, ref_conf_name, _] = sep_path_segs(fname)
            csv_file = res_path + "bdmetrics_" + ref_conf_name + ".csv"
            pinfo(csv_file)
            with open_csv(csv_file, "w") as f:
                writer = csv.writer(f, delimiter=",")
                res = score.eval(enc, fname, resume)
                save_refs(writer, res)
    else:
        perror("unknown refs file/dir [%s]" % refs)

