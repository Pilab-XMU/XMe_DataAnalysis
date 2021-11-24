# -*- coding: utf-8 -*-
# @Time   : 2021/9/26 16:49
# @Author : Gang
# @File   : psdStaticDataProcessUtils.py
import numpy as np
from gangLogger.myLog import MyLog
from psdStaticConst import *
# from scipy.fft import fft
# from scipy import integrate
from numpy.fft import fft
import matplotlib.mlab as mlab


# TODO
# 注意此处的两个scipy的包都可以换成nunpy的！！


class PSDStaticDataProcessUtils:
    logger = MyLog("PSDStaticDataProcessUtils", BASEDIR)

    @classmethod
    def loadData(cls, keyPara):
        filePath = keyPara["FILE_PATH"]
        logGArray = np.load(filePath)["conductance_array"]
        cls.logger.debug("数据读取完成...")
        return logGArray

    @classmethod
    def getIntegPSD(cls, GArray, freqLow, freqHigh, keyPara, mode="mlab"):
        """
        使用mlab.psd()或幅度谱平方求psd；并返回电导均值
        :param keyPara: 界面配置参数
        :param condData: 对数电导单条曲线
        :param mode:计算模式
        :return: psd的积分, 平均电导
        """
        windowSize = int(keyPara["le_WindowSize"])
        if np.count_nonzero(GArray) < windowSize:
            return 0.0, 0.0
        else:
            try:
                GArray = GArray[GArray != 0][:windowSize]
                gMean = np.mean(GArray)
                N = len(GArray)
                sampFreq = keyPara["le_Frequence"]
                if mode == "mlab":
                    psd, freqs = mlab.psd(GArray, NFFT=N, sides='onesided',
                                          Fs=sampFreq, window=mlab.window_hanning,
                                          pad_to=N, scale_by_freq=False)
                    psd *= 2  # 与手算的相差系数2
                else:
                    fftRes = fft(GArray)
                    fftResAbs = np.abs(fftRes)
                    resNorm = fftResAbs / (N / 2)
                    resNorm[0] /= 2

                    freqs = np.linspace(0, sampFreq // 2, N // 2)
                    oneSideFFT = resNorm[:N // 2]
                    psd = oneSideFFT ** 2

                integRangeIdx = np.where((freqs >= freqLow) & (freqs <= freqHigh))[0]
                # integPSD = integrate.trapz(psd[integRangeIdx], freqs[integRangeIdx])
                integPSD = np.trapz(psd[integRangeIdx], freqs[integRangeIdx])
            except Exception as e:
                errMsg = f"单条psd计算异常{e}"
                cls.logger.error(errMsg)
                return 0.0, 0.0
            else:
                return integPSD, gMean

    @classmethod
    def getIntegInterval(cls, keyPara):
        """
        这个函数是整个数组进行求解
        :param keyPara:
        :return:
        """
        logGArray = cls.loadData(keyPara)

        logGHigh, logGLow = keyPara["le_CondHigh"], keyPara["le_CondLow"]
        logGArraySelect = np.where((logGArray >= logGLow) & (logGArray <= logGHigh), logGArray, -np.inf)
        gArraySelect = np.power(10.0, logGArraySelect)
        resultTemp = np.apply_along_axis(cls.getIntegPSD, 1, gArraySelect, 100, 1000, keyPara)
        integPSD, gMean = resultTemp[:, 0], resultTemp[:, 1]

        finalIdx = np.where(integPSD != 0.0)
        gMean = gMean[finalIdx]
        integPSD = integPSD[finalIdx]

        return gMean, integPSD

    @classmethod
    def getMinNInterval(cls, gMean, integPSD):
        """

        :param gMean:
        :param integPSD:
        :return:
        """
        if gMean.shape[0] == 0:
            raise Exception("无符合条件数据")
        exponentIdx = np.arange(0.5, 2.5, 0.005)
        minNIdx = [cls.getMinHelper(gMean, integPSD, k) for k in exponentIdx]
        return sorted(minNIdx)[0][1]

    @classmethod
    def getMinHelper(cls, gMean, integPSD, exponent):
        try:
            gMeanPower = np.power(gMean, exponent)
            scaledPSD = integPSD / gMeanPower
            coef = np.corrcoef(scaledPSD, gMean)[0, 1]
        except Exception as e:
            errMsg = f"minNIdx计算异常：{e}"
            cls.logger.error(errMsg)
            return np.inf, exponent
        else:
            return np.abs(coef), exponent
