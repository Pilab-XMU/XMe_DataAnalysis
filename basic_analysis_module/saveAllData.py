# -*- coding: utf-8 -*-
# @Time   : 2020/12/29 20:20
# @Author : Gang
# @File   : saveAllData.py

from PyQt5.QtCore import QObject, pyqtSignal
import time
import numpy as np

from gangLogger.myLog import MyLog
from gangUtils.generalUtils import GeneralUtils
from basicAnalysisConst import *


class SaveAllData(QObject):
    tbw = pyqtSignal(str)
    run_end = pyqtSignal()
    logger = MyLog("SaveAllData", BASEDIR)

    def __init__(self, *args):
        super().__init__()
        self.distance, self.conductance, self.length, self.distance_draw, self.conductance_draw, self.key_para = args

    def run(self):
        t1 = time.perf_counter()
        try:
            self.save_singletrace()
        except Exception as e:
            errMsg = f"单条数据保存异常：{e}"
            self.logger.error(errMsg)

        try:
            self.save_goodtrace()
        except Exception as e:
            errMsg = f"goodtrace数据保存异常：{e}"
            self.logger.error(errMsg)

        try:
            self.save_analysis_data()
        except Exception as e:
            errMsg = f"analysis数据保存异常：{e}"
            self.logger.error(errMsg)

        t2 = time.perf_counter()

        logMsg = f"并行执行时间：{int(t2 - t1)}"
        self.logger.debug(logMsg)
        self.run_end.emit()

    def save_singletrace(self):
        # 思来想去，把数据保存为npy加快读取速度
        data_save_path = self.key_para["Data_Save_Path"]
        distance, conductance, length = self.distance, self.conductance, self.length

        ADDITIONAL_LENGTH = self.key_para["le_Additional_Length"]
        single_trace_path = os.path.join(data_save_path, "Single_Trace")
        GeneralUtils.creatFolder(data_save_path, "Single_Trace")
        np.savez(single_trace_path + "/single_trace.npz", distance_array=distance, conductance_array=conductance,
                 length_array=length,
                 additional_length=ADDITIONAL_LENGTH)

    def save_goodtrace(self):
        data_save_path = self.key_para["Data_Save_Path"]
        distance_draw, conductance_draw = self.distance_draw, self.conductance_draw

        trace_path = os.path.join(data_save_path, "Goodtrace")
        GeneralUtils.creatFolder(data_save_path, "Goodtrace")
        data = np.array([distance_draw, conductance_draw]).T
        np.savetxt(trace_path + "/goodtrace.txt", data, fmt='%.5e', delimiter='\t')

    def save_analysis_data(self):
        data_save_path = self.key_para["Data_Save_Path"]
        distance_draw, conductance_draw, length = self.distance_draw, self.conductance_draw, self.length

        analysis_path = os.path.join(data_save_path, "Analysis")
        GeneralUtils.creatFolder(data_save_path, "Analysis")

        H_2D_cond, x_2D_edges, y_2D_edges = np.histogram2d(distance_draw, conductance_draw, bins=[500, 1000],
                                                           range=[[-0.5, 3], [-10, 1]])
        H_1D_cond, bins_1D_edges = np.histogram(conductance_draw, bins=1100, range=[-10, 1])

        # 此处修改将长度统计的柱状图改为所见即所得
        _1D_LENG_XLEFT = self.key_para["le_1D_Leng_Xleft"]
        _1D_LENG_XRIGHT = self.key_para["le_1D_Leng_Xright"]
        _1D_LENG_BINS = int(self.key_para["le_1D_Leng_Bins"])
        # H_1D_length, bins_1D_length_edges = np.histogram(length, bins=100, range=[0, 3])
        H_1D_length, bins_1D_length_edges = np.histogram(length, bins=_1D_LENG_BINS,
                                                         range=[_1D_LENG_XLEFT, _1D_LENG_XRIGHT])

        x_2D_edges_pad, y_2D_edges_pad = self.zero_pad(x_2D_edges, y_2D_edges)

        np.savetxt(analysis_path + "/WA-BJ_3Dhist.txt", H_2D_cond * 2, fmt='%d', delimiter='\t')
        hist_2D_scales = np.array([x_2D_edges_pad, y_2D_edges_pad]).T
        np.savetxt(analysis_path + "/WA-BJ_3Dhist_scales.txt", hist_2D_scales, fmt='%.5e', delimiter='\t')
        hist_1D_cond = np.array([bins_1D_edges[:-1], H_1D_cond]).T
        np.savetxt(analysis_path + "/WA-BJ_logHist.txt", hist_1D_cond, fmt='%.5e', delimiter='\t')
        hist_1D_length = np.array([bins_1D_length_edges[:-1], H_1D_length]).T
        np.savetxt(analysis_path + "/WA-BJ_plateau.txt", hist_1D_length, fmt='%.5e', delimiter='\t')

    def zero_pad(self, x_2D_edges, y_2D_edges):
        _2D_CONDUCTANCE_BINS_X = 500
        _2D_CONDUCTANCE_BINS_Y = 1000
        _PAD_NUM = 500
        x_2D_edges_pad = np.pad(x_2D_edges[1:], (0, _PAD_NUM), 'constant', constant_values=(0))
        y_2D_edges_pad = y_2D_edges[1:]
        return x_2D_edges_pad, y_2D_edges_pad
