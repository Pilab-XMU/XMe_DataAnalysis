# -*- coding: utf-8 -*-
# @Time   : 2020/11/30 9:45
# @Author : Gang
# @File   : cal_draw_data.py
from PyQt5.QtCore import QObject, pyqtSignal
from multiprocessing import cpu_count,Pool
import time,os
from cal_data import *

class CalDrawData(QObject):
    sbar = pyqtSignal(str)
    pbar = pyqtSignal(int)
    tbw = pyqtSignal(str)
    run_end = pyqtSignal()

    def __init__(self,key_para,dataset):
        super(CalDrawData, self).__init__()
        self.key_para=key_para
        self.dataset=dataset

    def run(self):
        key_para=self.key_para
        dataset=self.dataset
        args=[]
        for data in  dataset:
            args.append((data,key_para))
        cpu_N=cpu_count()
        pool=Pool(cpu_N-1)
        t1 = time.perf_counter()
        self.pbar.emit(40)
        self.draw_dataset=pool.starmap_async(self.get_draw_data,args).get()
        pool.close()
        pool.join()
        t2 = time.perf_counter()
        print("计算绘图所需数据的并行执行时间：", int(t2 - t1))
        self.pbar.emit(60)
        self.run_end.emit()

    @staticmethod
    def get_draw_data(data,key_para):
        print(f"{os.getpid()}, {time.perf_counter()}, {__name__}")
        SELECT_OPTION = key_para["SELECT_OPTION"]
        if key_para["PROCESS"] == 0:
            if not SELECT_OPTION:
                distance,condutance,length,distance_draw,condutance_draw,ALL_TRACE_NUM,SELECT_TRACE_NUM = calculate_draw_data(data,key_para)
            else:
                distance,condutance,length,distance_draw,condutance_draw,ALL_TRACE_NUM,SELECT_TRACE_NUM = calculate_draw_data_with_select(data,key_para)
        else:
            pass

        return [distance,condutance,length,distance_draw,condutance_draw,ALL_TRACE_NUM,SELECT_TRACE_NUM]
