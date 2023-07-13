# encoding=utf-8
import logging
import sys
import os
import shutil
import glob
import logging
import random
import subprocess
import resource

def pretty_args(args, tabs=''):
    args_str = ''
    for arg in vars(args):
        args_str += '\n' + tabs + '%s:\t[%s]' % (arg, repr(getattr(args, arg)))
    return args_str

perror = logging.error
pwarn  = logging.warning
pinfo  = logging.info
pdebug = logging.debug

# def perror(msg):
#     # print("\033[1;31mERROR: %s\033[1;0m" % msg)
# def pwarn(msg):
#     # print("\033[1;33mWARNING: %s\033[1;0m" % msg)
# def pinfo(msg):
#     # print("\033[1;34mINFO: %s\033[1;0m" % msg)
# def pdebug(msg):
#     logging.debug(msg)

def init_logger(level=logging.INFO, logfile=None):
    from imp import reload
    reload(logging)

    logging_params = {
        'level': level,
        'filemode': 'w',
        'format': '%(asctime)s[%(levelname)s, %(module)s.%(funcName)s:L%(lineno)d](%(name)s) %(message)s',
    }

    if logfile is not None:
        logging_params['filename'] = logfile

    logging.basicConfig(**logging_params)
    logging.debug('init basic configure of logging success')

class ExeCost:
    def __init__(self):
        self.utime = 0
        self.stime  = 0

    def __init__(self, res_start: resource, res_end: resource):
        self.utime = res_end.ru_utime - res_start.ru_utime
        self.stime = res_end.ru_stime - res_start.ru_stime

def exe_log_cmd(cmd, log_process):
    pwarn(cmd)
    usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
    usage_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    output = output.decode('utf-8')
    if log_process is None:
        return None
    pinfo("out=[\n%s]" % output)
    return (log_process(output), ExeCost(usage_start, usage_end))

def exe_cmd(cmd):
    pwarn(cmd)
    usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    process = os.popen(cmd)
    usage_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    output = process.read()
    # output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
    # print("out=[%s]" % output)
    return ExeCost(usage_start, usage_end)

def open_csv(filename, mode='r'):
    """Open a csv file in proper mode depending on Python verion."""
    return(open(filename, mode=mode+'b') if bytes is str else
           open(filename, mode=mode, newline=''))

def make_dir(p, del_old=False):
    if os.path.exists(p):  # 文件夹存在
        if del_old:
            shutil.rmtree(p)        # 删除旧文件夹

    if not os.path.exists(p):
        os.makedirs(p)  # 创建文件夹

def sep_path_segs(path):
    filepath, tempfilename= os.path.split(path)
    shortname, extension = os.path.splitext(tempfilename)
    return filepath, shortname, extension

def copy_file_noexcept(src, dst, force=True):
    ret = False
    try:
        # 文件已存在，且非强制拷贝
        if not force and os.path.exists(dst):
            pass
        elif os.path.exists(dst) and os.path.samefile(src, dst):
            logging.info('copy source and dst are the same file [%s]' % src)
        else:
            shutil.copyfile(src, dst)
            ret = True
    except:
        logging.error(sys.exc_info()[1])

    return ret


def move_file_noexcept(src, dst, force=True):
    ret = False
    try:
        # 文件已存在，且非强制移动
        if not force and os.path.exists(dst):
            pass
        elif os.path.exists(dst) and os.path.samefile(src, dst):
            logging.info('source and dst are the same file [%s]' % src)
        else:
            shutil.move(src, dst)
            ret = True
    except:
        logging.error(sys.exc_info()[1])

    return ret

if __name__ == '__main__':
    # path = '../'
    # # print(sep_path_segs('./a/b c/de f.txt'))
    # # print(sep_path_segs(r'.\a\b c\de f.txt'))
    # # make_dir(r'D:\DataTemp\game_type_new\p2p\csgo_dst\\')
    # files = find_files_recursively('util.py', path, level=2)
    # print(files)

    init_logger()
    logging.error(2)
    logging.getLogger().setLevel(logging.DEBUG)

