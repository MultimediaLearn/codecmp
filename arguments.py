import argparse

import vutil
parser = argparse.ArgumentParser(description='Produce BD score report')
parser.add_argument('--enc', default="resources/enc_x264.json",
        help='encoder configure json file')
parser.add_argument('--refs', default="resources/games.json",
        help='references configure json file or directorie')
parser.add_argument('--res', default="out/res/",
        help='final result save path')
parser.add_argument('--resume', default=False, type=vutil.str2bool,
        help='continue the score process')

args = parser.parse_args()

