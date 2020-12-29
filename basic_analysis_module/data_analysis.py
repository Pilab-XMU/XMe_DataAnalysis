# -*- coding: utf-8 -*-
# @Time   : 2020/11/17 17:01
# @Author : Gang
# @File   : data_analysis.py
from PyQt5.QtCore import pyqtSignal, QObject
from multiprocessing import cpu_count, Pool
from load_data import *
import time, os


class DataAnalysis(QObject):
    pbar = pyqtSignal(int)
    tbw = pyqtSignal(str)
    sbar = pyqtSignal(str)
    run_end = pyqtSignal()

    def __init__(self, key_para):
        super(DataAnalysis, self).__init__()
        self.key_para = key_para

    def run(self):
        key_para = self.key_para
        args = []
        file_list = self.key_para["FILE_PATHS"]
        for file in file_list:
            args.append((file, key_para))
        cpu_N = cpu_count()
        pool = Pool(cpu_N - 1)
        t1 = time.perf_counter()
        self.pbar.emit(10)
        self.dataset = pool.starmap_async(self.get_cut_trace, args).get()
        pool.close()
        pool.join()
        t2 = time.perf_counter()
        print("并行执行时间：", int(t2 - t1))
        self.pbar.emit(25)
        self.run_end.emit()

    @staticmethod
    def get_cut_trace(file_path, key_para):
        print(f"{os.getpid()}, {time.perf_counter()}, {__name__}")
        log_G = get_logG(file_path, key_para)
        SELECT_OPTION = key_para["SELECT_OPTION"]
        if key_para["PROCESS"] == 0:
            if not SELECT_OPTION:
                start, zero, end, len_high, len_low, start1, end1, start2, end2 = cut_open_trace(log_G, key_para)
            else:
                start, zero, end, len_high, len_low, start1, end1, start2, end2 = cut_open_trace_with_select(log_G,
                                                                                                             key_para)
        else:
            pass

        return [log_G, start, zero, end, len_high, len_low, start1, end1, start2, end2]
        # 这里两个处理类的处理函数的返回值写为list的原因是，方便修改，因为set不可以修改
