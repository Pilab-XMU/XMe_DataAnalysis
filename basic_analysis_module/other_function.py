# -*- coding: utf-8 -*-
# @Time   : 2020/12/8 16:32
# @Author : Gang
# @File   : other_function_single.py
import os
import time
import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class MyNavigationToolbar(NavigationToolbar):
    toolitems =(
        ('Home', 'Reset original view', 'home', 'home'),
        (None, None, None, None),
        ('Pan',
         'Left button pans, Right button zooms\n'
         'x/y fixes axis, CTRL fixes aspect',
         'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis, CTRL fixes aspect',
         'zoom_to_rect', 'zoom'),
        ("Customize", "Edit axis, curve and image parameters",
         "qt4_editor_options", "edit_parameters"),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure')
    )

def get_desktop_path():
    """
    获取桌面路径
    :return: 桌面路径
    """
    return os.path.join(os.path.expanduser("~"), "Desktop")

def get_current_time():
    """
    获取当前的系统时间，以“2016-03-20 11:45:39”的形式返回
    :return:字符串格式的时间
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def zero_pad(x_2D_edges, y_2D_edges):
    _2D_CONDUTANCE_BINS_X=500
    _2D_CONDUTANCE_BINS_Y=1000
    _PAD_NUM=500
    x_2D_edges_pad= np.pad(x_2D_edges[1:],(0,_PAD_NUM),'constant', constant_values=(0))
    y_2D_edges_pad=y_2D_edges[1:]
    return x_2D_edges_pad,y_2D_edges_pad