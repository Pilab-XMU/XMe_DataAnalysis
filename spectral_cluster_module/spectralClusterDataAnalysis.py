# -*- coding: utf-8 -*-
# @Time   : 2021/11/10 11:03
# @Author : Gang
# @File   : spectralClusterDataAnalysis.py
import time

from PyQt5.QtCore import QObject, pyqtSignal
from gangLogger.myLog import MyLog
from spectralClusterConst import *
from spectralClusterDataProcessUtils import SpectralClusterDataProcessUtils as DataProcessUtils


class SpectralClusterDataAnalysis(QObject):
    runEnd = pyqtSignal()
    logger = MyLog("SpectralClusterDataAnalysis", BASEDIR)

    def __init__(self, keyPara):
        super().__init__()
        self.keyPara = keyPara
        self.dataset = None

    def run(self):
        try:
            t1 = time.perf_counter()

            conductance, distance, length_arr, additional_length= DataProcessUtils.loadData(self.keyPara)
            dataHistAll, dataHistAll_X = DataProcessUtils.getHist1D(
                self.keyPara,
                conductance
            )
            labelsList, dataHistAllSelect = DataProcessUtils.clusterWithSP(
                self.keyPara,
                dataHistAll,
                dataHistAll_X
            )
            calinskiHarabaszIndex = DataProcessUtils.getCHI(
                self.keyPara,
                labelsList,
                dataHistAllSelect
            )

            t2 = time.perf_counter()
            self.logger.debug(f"Core computing time:{int(t2 - t1)}")
        except Exception as e:
            errMsg = f"CALCULATE ERROR:{e}"
            self.logger.error(errMsg)
            self.dataset = None
        else:
            self.dataset = [conductance, distance, length_arr, additional_length,
                            dataHistAll, dataHistAll_X,
                            labelsList, calinskiHarabaszIndex]
        finally:
            self.runEnd.emit()
