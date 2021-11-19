# -*- coding: utf-8 -*-
# @Time   : 2021/8/31 9:17
# @Author : Gang
# @File   : myLog.py

import logging, os

# 日志打印等级
LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


class MyLog:

    def __init__(self, name="default", baseDir=".", level="debug"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LEVELS.get(level))
        self.baseDir = baseDir
        if not self.logger.handlers:
            self.initSet()

    def initSet(self):
        logFile = self.baseDir + "/Log/log.log"
        errFile = self.baseDir + "/Log/err.log"
        self.createFile(logFile)
        self.createFile(errFile)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] [%(processName)s] %(message)s',
                                      '%Y-%m-%d %H:%M:%S')

        self.logHandler = logging.FileHandler(logFile, encoding='utf-8')
        self.logHandler.setLevel(logging.DEBUG)
        self.logHandler.setFormatter(formatter)
        self.logger.addHandler(self.logHandler)

        self.errHandler = logging.FileHandler(errFile, encoding='utf-8')
        self.errHandler.setLevel(logging.ERROR)
        self.errHandler.setFormatter(formatter)
        self.logger.addHandler(self.errHandler)

        self.streamHandler = logging.StreamHandler()
        self.streamHandler.setLevel(logging.DEBUG)
        self.streamHandler.setFormatter(formatter)
        self.logger.addHandler(self.streamHandler)

    def createFile(self, filepath):
        if self.creatFolder(self.baseDir, "Log"):
            if os.path.exists(filepath):
                return
            else:
                fd = open(filepath, mode='w', encoding='utf-8')
                fd.close()
        else:
            errMsg = "新建文件异常"
            self.error(errMsg)

    def debug(self, logMsg):
        self.logger.debug(logMsg)

    def error(self, logMsg):
        self.logger.error(logMsg)

    def creatFolder(self, baseDir, folderName):
        try:
            folderPath = os.path.join(baseDir, folderName)
            if not os.path.exists(folderPath):
                os.mkdir(folderPath)
            return True
        except Exception as e:
            errMsg = f"新建文件夹异常：{e}"
            self.error(errMsg)
            return False
