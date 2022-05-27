# -*- coding: utf-8 -*-
# @Time   : 2020/11/17 17:01
# @Author : Gang
# @File   : dataAnalysis.py
from PyQt5.QtCore import pyqtSignal, QObject
from multiprocessing import cpu_count, Pool
from dataProcessUtils import *
from gangLogger.myLog import MyLog
import time
from basicAnalysisConst import *


class DataAnalysis(QObject):
    pbar = pyqtSignal(int)
    tbw = pyqtSignal(str)
    sbar = pyqtSignal(str)
    run_end = pyqtSignal()
    logger = MyLog("DataAnalysis", BASEDIR)

    def __init__(self, key_para):
        super().__init__()
        self.key_para = key_para

    def run(self):
        key_para = self.key_para
        args = []
        file_list = self.key_para["FILE_PATHS"]
        for file in file_list:
            args.append((file, key_para))
        cpu_N = cpu_count()
        pool = Pool(cpu_N - 1)
        self.logger.debug(f"Number of CPU core:{cpu_N},Process pool size:{cpu_N - 1}")
        t1 = time.perf_counter()
        self.pbar.emit(10)

        self.dataset = pool.starmap_async(self.get_cut_trace, args).get()
        pool.close()
        pool.join()
        t2 = time.perf_counter()
        self.logger.debug(f"Parallel time:{int(t2 - t1)}")
        self.pbar.emit(25)
        self.run_end.emit()

    @classmethod
    def get_cut_trace(cls, file_path, key_para):
        cls.logger.debug(
            f"Computing process PID: {os.getpid()},Calculates the start time of the process: {time.perf_counter()}")
        SELECT_OPTION = key_para["SELECT_OPTION"]
        start, zero, end, len_high, len_low, start1, end1, start2, end2 = None, None, None, None, None, None, None, None, None

        try:
            log_G = DataProcessUtils.get_logG(file_path, key_para)
        except Exception as e:
            errMsg = f"DATA READ ERROR:{e}"
            cls.logger.error(errMsg)
            return None
        else:
            try:
                if key_para["PROCESS"] == 0:
                    if not SELECT_OPTION:
                        start, zero, end, len_high, len_low, start1, end1, start2, end2 = DataProcessUtils.cut_open_trace(
                            log_G, key_para)
                    else:
                        start, zero, end, len_high, len_low, start1, end1, start2, end2 = DataProcessUtils.cut_open_trace_with_select(
                            log_G, key_para)
                else:
                    # 开始添加close处理过程
                    if not SELECT_OPTION:
                        start, zero, end, len_high, len_low, start1, end1, start2, end2 = DataProcessUtils.cut_close_trace(
                            log_G, key_para
                        )
                    else:
                        start, zero, end, len_high, len_low, start1, end1, start2, end2 = DataProcessUtils.cut_close_trace_with_select(
                            log_G, key_para
                        )
            except Exception as e:
                errMsg = f"DATA CUT ERROR:{e}"
                cls.logger.error(errMsg)
                return None
            else:
                return [log_G, start, zero, end, len_high, len_low, start1, end1, start2, end2]
                # 这里两个处理类的处理函数的返回值写为list的原因是，方便修改，因为set不可以修改
