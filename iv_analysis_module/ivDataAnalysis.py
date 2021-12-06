# -*- coding: utf-8 -*-
# @Time   : 2021/9/22 8:53
# @Author : Gang
# @File   : ivDataAnalysis.py
import time

from PyQt5.QtCore import QObject, pyqtSignal
from multiprocessing import cpu_count, Pool

from gangLogger.myLog import MyLog
from ivAnalysisConst import *
from ivDataProcessUtils import IVDataProcessUtils as DataProcessUtils


class IVDataAnalysis(QObject):
    runEnd = pyqtSignal()
    logger = MyLog("IVDataAnalysis", BASEDIR)

    def __init__(self, keyPara):
        super().__init__()
        self.keyPara = keyPara
        self.datasets = None

    def run(self):
        keyPara = self.keyPara
        args = []
        fileList = keyPara["FILE_PATHS"]
        for file in fileList:
            args.append((file, keyPara))
        cpuCount = cpu_count()
        pool = Pool(cpuCount - 1)
        self.logger.debug(f"Number of CPU core:{cpuCount},Process pool size:{cpuCount - 1}")
        t1 = time.perf_counter()

        self.datasets = pool.starmap_async(self.dataReactor, args).get()
        pool.close()
        pool.join()

        t2 = time.perf_counter()
        self.logger.debug(f"Parallel time:{int(t2 - t1)}")
        self.runEnd.emit()

    @classmethod
    def dataReactor(cls, filePath, keyPara):
        cls.logger.debug(
            f"Computing process PID: {os.getpid()},Calculates the start time of the process: {time.perf_counter()}")

        try:
            currentData, condData, biasVData = DataProcessUtils.hysteresis(filePath, keyPara)
        except Exception as e:
            errMsg = f"HYSTERESIS ERROR:{e}"
            cls.logger.error(errMsg)
            return None
        else:
            if currentData is None:
                return None

            try:
                biasVDataFor, currentDataFor, condDataFor,\
                biasVDataReve, currentDataReve, condDataReve,\
                biasVDataFlat, currentDataFlat, condDataFlat = DataProcessUtils.getPartitionData(
                    currentData, condData, biasVData)
            except Exception as e:
                errMsg = f"PARTITION DATA ERROR:{e}"
                cls.logger.error(errMsg)
                return None
            else:
                return biasVDataFor, currentDataFor, condDataFor, biasVDataReve, currentDataReve, condDataReve, biasVDataFlat, currentDataFlat, condDataFlat
