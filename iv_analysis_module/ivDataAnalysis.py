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
import numpy as np
#import debugpy

class IVDataAnalysis(QObject):
    runEnd = pyqtSignal()
    logger = MyLog("IVDataAnalysis", BASEDIR)

    def __init__(self, keyPara):
        super().__init__()
        self.keyPara = keyPara
        self.datasets = None

    def run(self):
        #debugpy.debug_this_thread()
        keyPara = self.keyPara
        args = []
        fileList = keyPara["FILE_PATHS"]
        
        if keyPara["FILE_TYPE"] == "tdms":
            for file in fileList:
                args.append((file, keyPara))
            cpuCount = cpu_count()
            # 进程池
            pool = Pool(cpuCount - 1)
            self.logger.debug(f"Number of CPU core:{cpuCount},Process pool size:{cpuCount - 1}")
            t1 = time.perf_counter()

            self.datasets = pool.starmap_async(self.dataReactor, args).get()
            pool.close()
            pool.join()

            t2 = time.perf_counter()
            self.logger.debug(f"Parallel time:{int(t2 - t1)}")
            self.runEnd.emit()
        elif keyPara["FILE_TYPE"] == "npz":
            data = np.load(fileList[0], allow_pickle=True)
            c_for = data['c_for']
            v_for = data['v_for']
            cond_for = data['cond_for']
            c_reve = data['c_rev']
            v_reve = data['v_rev']
            cond_reve = data['cond_rev']
            cond_traces = data['cond']
            
            for_length = np.array([len(c_for[i]) for i in range(len(c_for))])
            reve_length = np.array([len(c_reve[i]) for i in range(len(c_reve))])
            
            self.datasets = [(
                np.concatenate(v_for), np.concatenate(c_for), np.concatenate(cond_for),
                np.concatenate(v_reve), np.concatenate(c_reve), np.concatenate(cond_reve),
                cond_traces, len(c_for), for_length, reve_length
                )]
            self.runEnd.emit()
            
    @classmethod
    def dataReactor(cls, filePath, keyPara):
        cls.logger.debug(
            f"Computing process PID: {os.getpid()},Calculates the start time of the process: {time.perf_counter()}")

        try:
            currentData, condData, biasVData, condTrace = DataProcessUtils.hysteresis(filePath, keyPara)
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
                numberOfTrace, for_length, reve_length = DataProcessUtils.getPartitionData(currentData, condData, biasVData)
            except Exception as e:
                errMsg = f"PARTITION DATA ERROR:{e}"
                cls.logger.error(errMsg)
                return None
            else:
                # 返回一个电导原始数据用来判断是否在范围内
                return biasVDataFor, currentDataFor, condDataFor, biasVDataReve, currentDataReve, condDataReve, condTrace[:numberOfTrace],numberOfTrace, for_length, reve_length
