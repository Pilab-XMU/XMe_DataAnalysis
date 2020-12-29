# -*- coding: utf-8 -*-
# @Time   : 2020/12/18 14:38
# @Author : Gang
# @File   : other_function_single.py
import os,time


def get_desktop_path():
    """
    获取桌面路径
    :return: 桌面路径
    """
    return os.path.join(os.path.expanduser("~"), "Desktop")

def get_current_time():
    """
    获取当前的系统时间，以'2020-12-22-10:40'的形式返回
    :return:字符串格式的时间
    """
    return time.strftime("%Y-%m-%d-%H:%M", time.localtime())
