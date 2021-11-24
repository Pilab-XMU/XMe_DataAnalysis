# -*- coding: utf-8 -*-
# @Time   : 2021/9/26 16:40
# @Author : Gang
# @File   : psdStaticDataAnalysis.py
import time

from PyQt5.QtCore import QObject, pyqtSignal
from gangLogger.myLog import MyLog
from psdStaticConst import *
from psdStaticDataProcessUtils import PSDStaticDataProcessUtils as DataProcessUtils


class PSDStaticDataAnalysis(QObject):
    runEnd = pyqtSignal()
    logger = MyLog("PSDStaticDataAnalysis", BASEDIR)

    def __init__(self, keyPara):
        super().__init__()
        self.keyPara = keyPara
        self.dataset = None

    def run(self):
        try:
            t1 = time.perf_counter()
            gMean, integPSD = DataProcessUtils.getIntegInterval(self.keyPara)
            minN = DataProcessUtils.getMinNInterval(gMean, integPSD)
            t2 = time.perf_counter()
            self.logger.debug(f"Core computing time:{int(t2 - t1)}")
        except Exception as e:
            errMsg = f"CALCULATE ERROR:{e}"
            self.logger.error(errMsg)
            self.dataset = None
        else:
            self.dataset = [gMean, integPSD, minN]
        finally:
            self.runEnd.emit()
