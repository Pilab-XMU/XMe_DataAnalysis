# -*- coding: utf-8 -*-
# @Time   : 2021/10/20 14:28
# @Author : Gang
# @File   : generalUtils.py

import time
from gangUtils.utilsConst import *
from gangUtils.myLog import *


class GeneralUtils:
    logger = MyLog("GeneralUtils", BASEDIR)

    @classmethod
    def getDesktopPath(cls):
        """
        获取桌面路径
        :return: 桌面路径
        """
        return os.path.join(os.path.expanduser("~"), "Desktop")

    @classmethod
    def creatFolder(cls, baseDir, folderName):
        folderPath = os.path.join(baseDir, folderName)
        if os.path.exists(folderPath):
            cls.logger.debug(f"The destination path already exists：{folderPath}")
        else:
            os.mkdir(folderPath)
            cls.logger.debug(f"A target path has been created:{folderPath}")

    @classmethod
    def getCurrentTime(cls):
        """
        获取当前的系统时间，以“2016-03-20 11:45:39”的形式返回
        :return:字符串格式的时间
        """
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


