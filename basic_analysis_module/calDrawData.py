# -*- coding: utf-8 -*-
# @Time   : 2020/11/30 9:45
# @Author : Gang
# @File   : calDrawData.py
from PyQt5.QtCore import QObject, pyqtSignal
from multiprocessing import cpu_count, Pool
import time
from drawDataProcessUtils import *


class CalDrawData(QObject):
    sbar = pyqtSignal(str)
    pbar = pyqtSignal(int)
    tbw = pyqtSignal(str)
    run_end = pyqtSignal()
    logger = MyLog("CalDrawData", BASEDIR)

    def __init__(self, key_para, dataset):
        super().__init__()
        self.key_para = key_para
        self.dataset = dataset

    def run(self):
        key_para = self.key_para
        dataset = self.dataset
        args = []
        for data in dataset:
            args.append((data, key_para))
        cpu_N = cpu_count()
        pool = Pool(cpu_N - 1)
        t1 = time.perf_counter()
        self.pbar.emit(40)
        self.draw_dataset = pool.starmap_async(self.get_draw_data, args).get()
        pool.close()
        pool.join()
        t2 = time.perf_counter()
        self.logger.debug(f"Computes the parallel time of the data required for drawing: {int(t2 - t1)}")
        self.pbar.emit(60)
        self.run_end.emit()

    @classmethod
    def get_draw_data(cls,data, key_para):
        cls.logger.debug(f"Drawing process pid：{os.getpid()},Start time of drawing calculation process:{time.perf_counter()}")
        SELECT_OPTION = key_para["SELECT_OPTION"]
        distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = None, None, None, None, None, None, None,
        try:
            if key_para["PROCESS"] == 0:
                if not SELECT_OPTION:
                    distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = DrawDataProcessUtils.calculate_draw_data(
                        data, key_para)
                else:
                    distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = DrawDataProcessUtils.calculate_draw_data_with_select(
                        data, key_para)
            else:
                # 添加close过程的处理
                if not SELECT_OPTION:
                    distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = DrawDataProcessUtils.calculate_draw_data_close(
                        data, key_para)
                else:
                    distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = DrawDataProcessUtils.calculate_draw_data_close_with_select(
                        data, key_para)

        except Exception as e:
            errMsg = f"CALCULATE DRAW DATA ERROR: {e}"
            cls.logger.error(errMsg)
            return None
        else:
            return [distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM]
