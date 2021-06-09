# encoding=utf-8
import logging
import sys
import os
import shutil
import glob
import logging
import random

def pretty_args_str(args):
    args_str = ''
    for arg in vars(args):
        args_str += '\n\t%s:\t[%s]' % (arg, repr(getattr(args, arg)))

    return args_str

def perror(msg):
    print("\033[1;31mERROR: %s\033[1;0m" % msg)

def pwarning(msg):
    print("\033[1;33mWARNING: %s\033[1;0m" % msg)

def pinfo(msg):
    print("\033[1;34mINFO: %s\033[1;0m" % msg)

def init_logger(fn=None):
    from imp import reload
    reload(logging)

    logging_params = { 
        'level': logging.INFO,
        'format': '%(asctime)s__[%(levelname)s, %(module)s.%(funcName)s](%(name)s)__[L%(lineno)d] %(message)s',
    }   

    if fn is not None:
        logging_params['filename'] = fn

    logging.basicConfig(**logging_params)
    logging.debug('init basic configure of logging success')


def make_dir(p, del_old=False):
    if os.path.exists(p):  # 文件夹存在
        if del_old:
            shutil.rmtree(p)        # 删除旧文件夹
    else:
        try:
            os.mkdir(p)  # 创建文件夹
        except FileNotFoundError:
            os.makedirs(p, exist_ok=True)


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

