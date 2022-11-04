# -*- coding: utf-8 -*-
# @Time   : 2021/9/20 22:21
# @Author : Gang
# @File   : ivDataProcessUtils.py
import numpy as np
from nptdms import TdmsFile
from gangLogger.myLog import MyLog
from ivAnalysisConst import *


class IVDataProcessUtils:
    logger = MyLog("IVDataProcessUtils", BASEDIR)

    @classmethod
    def loadTMDSFile(cls, filePath):
        """
        加载tdms文件（单个）
        :param file_path:tdms文件路径
        :return:采样电压（numpy）
        """
        with TdmsFile.open(filePath) as tdmsFile:
            biasVolt = tdmsFile.groups()[0].channels()[0][:]  # 此处读完数据就是numpy数组了
            current = tdmsFile.groups()[0].channels()[1][:]
            cond = tdmsFile.groups()[0].channels()[2][:]
        return [biasVolt, current, cond]

    @classmethod
    def hysteresis(cls, filePath, keyPara):
        biasVolt, current, cond = cls.loadTMDSFile(filePath)
        bias_base = keyPara['le_Bias']
        biasVTrace, currentTrace, condTrace = [], [], []
        diffBiasV = np.concatenate((np.diff(biasVolt), np.array([10.0])))
        # 偏压从0.1到0.2阶跃中0.2v处的索引
        start_candi = \
            np.where((np.isclose(biasVolt, bias_base, 0.0001)) & (np.isclose(diffBiasV, bias_base, 0.0001)))[0] + 1

        # 从0.2到0.1的阶跃中0.2处的索引
        end_candi = \
            np.where((np.isclose(biasVolt, bias_base*2, 0.0001)) & (np.isclose(diffBiasV, -bias_base, 0.0001)))[0]
        # 确保每个对应位置上结束点索引大于起始点索引
        startIdx = []
        endIdx = []
        for i in range(len(start_candi)):
            end_i = end_candi[end_candi > start_candi[i]]
            if len(end_i) > 0:
                startIdx.append(start_candi[i])
                endIdx.append(end_i[0])
        startIdx = np.array(startIdx)
        endIdx = np.array(endIdx)

        # 确保扫描区间没有超过总长度，同时保证结束点的电压是0.1
        # strat是第一个为0.2的index  end是最后一个为0.2的点！！
        endIdx = endIdx + 200
        trueIdx = endIdx < biasVolt.shape[0]
        endIdx = endIdx[trueIdx]  # 这里直接使用了布尔索引！！
        startIdx = startIdx[trueIdx]
        biasVoltEnd = biasVolt[endIdx]
        tempIdx = np.where(np.isclose(biasVoltEnd, bias_base, 0.0001))[0]
        endIdx = endIdx[tempIdx]
        startIdx = startIdx[tempIdx]

        # 得到扫面区间，接下来就是把中间的切开！！
        for i in range(startIdx.shape[0]):
            biasVTrace.append(biasVolt[startIdx[i]:endIdx[i]])
            currentTrace.append(current[startIdx[i]:endIdx[i]])
            condTrace.append(cond[startIdx[i]:endIdx[i]])
        biasVTrace = np.array(biasVTrace, dtype='object')
        currentTrace = np.array(currentTrace, dtype='object')
        condTrace = np.array(condTrace, dtype='object')

        if biasVTrace.shape[0] == 0:
            return None, None, None

        # 寻找电压是0v的起始和终点
        cutStart, cutEnd = np.ones(biasVTrace.shape[0], dtype=int), np.ones(biasVTrace.shape[0], dtype=int)
        for i in range(biasVTrace.shape[0]):
            zero_idx = np.where(np.isclose(biasVTrace[i], 0, 0.0001))[0]
            # TODO 起点处可以也有波动，起点可以按照开始阶段的最后一个0来算，但终点需要根据最后一个peak来计算，从peak开始遍历找到第一个变号的地方
            for j in range(zero_idx.shape[0] - 1): # 找到正式扫描的起点
                if (zero_idx[j+1] - zero_idx[j] > 1) and (biasVTrace[i][zero_idx[j]+1] != 0):
                    cutStart[i] = zero_idx[j]
                    break
            if cutStart[i] == 1:
                continue
            # 寻找可能的终点
            zero_end = 1
            for j in range(zero_idx.shape[0]-1, 0, -1):
                if zero_idx[j] - zero_idx[j - 1] > 1:
                    zero_end = zero_idx[j]
                    break
            if zero_end == 1:
                continue
            trace = biasVTrace[i]
            peak_index = np.where((trace == trace.min()) | (trace == trace.max()))[0]
            first_peak = peak_index[0]
            if biasVTrace[i][first_peak] > 0 and biasVTrace[i][zero_end - 1] > 0:  # 从0到1，结尾必须从-1到0
                for j in range(zero_end - 1, 0, -1):
                    if biasVTrace[i][j] <= 0 and biasVTrace[i][j + 1] > 0:
                        zero_end = j
                        break
            elif biasVTrace[i][first_peak] < 0 and biasVTrace[i][zero_end - 1] < 0:  # 从0到-1，结尾必须从1到0
                for j in range(zero_end - 1, 0, -1):
                    if biasVTrace[i][j] >= 0 and biasVTrace[i][j + 1] < 0:
                        zero_end = j
                        break
            cutEnd[i] = zero_end
        
        # 删除bad boys
        trueIndex = np.where((cutStart == 1) | (cutEnd == 1), False, True)
        biasVTrace = biasVTrace[trueIndex]
        currentTrace = currentTrace[trueIndex]
        condTrace = condTrace[trueIndex]
        cutStart = cutStart[trueIndex]
        cutEnd = cutEnd[trueIndex]

        # 再次检查！！！
        if biasVTrace.shape[0] == 0:
            return None, None, None

        max_len = np.max([len(i) for i in biasVTrace])
        biasVTrace_same_len = [np.pad(trace, (0, max_len-len(trace)), 'edge') for trace in biasVTrace]
        biasVTrace_same_len = np.array(biasVTrace_same_len)
        diffBiasTrace = np.concatenate(
            (np.diff(biasVTrace_same_len), np.array([10.0] * biasVTrace_same_len.shape[0]).reshape(biasVTrace_same_len.shape[0], -1)), axis=1)
        frontCheckBIdx = np.where(
            np.isclose(biasVTrace_same_len, bias_base * 2, 0.001) & np.isclose(diffBiasTrace, -bias_base * 2, 0.001),
            True,
            False) # 从0.2 下降到0
        backCheckFIdx = np.where(
            np.isclose(biasVTrace_same_len, 0, 0.001) & np.isclose(diffBiasTrace, bias_base * 2, 0.001),
            True,
            False) # 从 0 上升到0.2
        backCheckBIdx = np.where(
            np.isclose(biasVTrace_same_len, bias_base * 2, 0.001) & np.isclose(diffBiasTrace, -bias_base, 0.001),
            True,
            False) # 从0.2下降到0.1

        # 此处对原来的程序做改动，此处应该应该对这三个check中的异常值进行删除
        trueIdx = np.apply_along_axis(np.any, 1, frontCheckBIdx) & np.apply_along_axis(np.any, 1,
                                                                                       backCheckFIdx) & np.apply_along_axis(
            np.any, 1, backCheckBIdx)
        """
        上面的写法，还可以这样写：
        eg:
        b=array([[1., 2., 3., 4.],
                [0., 0., 0., 0.],
                [0., 0., 0., 0.]])
        
        np.any(b,axis=1)
        Out[61]: array([ True, False, False])
        
        即np.any  np.all 都是可以指定axis这个轴参数的
        """
        biasVTrace = biasVTrace[trueIdx]
        currentTrace = currentTrace[trueIdx]
        condTrace = condTrace[trueIdx]
        cutStart = cutStart[trueIdx]
        cutEnd = cutEnd[trueIdx]
        frontCheckBIdx = frontCheckBIdx[trueIdx]
        backCheckFIdx = backCheckFIdx[trueIdx]
        backCheckBIdx = backCheckBIdx[trueIdx]

        # 再次检查！！！
        if biasVTrace.shape[0] == 0:
            return None, None, None

        frontCheckB = np.array([np.where(temp)[0][0] for temp in frontCheckBIdx])
        backCheckF = np.array([np.where(temp)[0][0] for temp in backCheckFIdx])
        backCheckB = np.array([np.where(temp)[0][0] for temp in backCheckBIdx])

        # 其实这里我担心是有问题的，因为万一frontCheckB[i]-100比100 还小呢。。。。就离谱了
        condCheckF = np.array([np.mean(condTrace[i][100:frontCheckB[i] - 100]) for i in range(biasVTrace.shape[0])])
        condCheckB = np.array(
            [np.mean(condTrace[i][backCheckF[i] + 100:backCheckB[i] - 100]) for i in range(biasVTrace.shape[0])])

        # 通过偏压把电导曲线切出来
        # 注意这里的这几个data其中每一行的数据维度都是不一致的！
        biasVData = np.empty(biasVTrace.shape[0], dtype=object)
        currentData = np.empty(biasVTrace.shape[0], dtype=object)
        condData = np.empty(biasVTrace.shape[0], dtype=object)

        for i in range(biasVTrace.shape[0]):
            biasVData[i] = biasVTrace[i][cutStart[i]:cutEnd[i]+1]
            currentData[i] = currentTrace[i][cutStart[i]:cutEnd[i]+1]
            condData[i] = condTrace[i][cutStart[i]:cutEnd[i]+1]

        # 删除超过scanRange的数据
        scanRange = keyPara["le_ScanRange"]
        trueIdx = [(data <= scanRange).all() for data in biasVData]
        biasVData = biasVData[trueIdx]
        currentData = currentData[trueIdx]
        condData = condData[trueIdx]
        condCheckB = condCheckB[trueIdx]
        condCheckF = condCheckF[trueIdx]

        # 再次检查！！！
        if biasVData.shape[0] == 0:
            return None, None, None

        # 整流判定  这个一般是不用开启的！！！
        selectRetificate = int(keyPara["le_SelectRetificate"])
        if selectRetificate == 0:
            retificationCheckGF = np.zeros(biasVData.shape[0])
            retificationCheckGB = np.zeros(biasVData.shape[0])
            quarterBiasV = round(0.35 * len(biasVTrace[0]))
            if biasVTrace[0][quarterBiasV] < 0:
                for i in range(biasVData.shape[0]):
                    retificationCheckGF = np.mean(
                        condData[i][(biasVData >= -scanRange - 0.001) & (biasVData <= -scanRange + 0.001)])
                    retificationCheckGB = np.mean(
                        condData[i][(biasVData >= scanRange - 0.001) & (biasVData <= scanRange + 0.001)])
            else:
                for i in range(biasVData.shape[0]):
                    retificationCheckGB = np.mean(
                        condData[i][(biasVData >= -scanRange - 0.001) & (biasVData <= -scanRange + 0.001)])
                    retificationCheckGF = np.mean(
                        condData[i][(biasVData >= scanRange - 0.001) & (biasVData <= scanRange + 0.001)])

            biasVData = np.where(retificationCheckGF >= retificationCheckGB, -biasVData, biasVData)
        # 完成整流判定

        # 对电流进行处理
        for i in range(currentData.shape[0]):
            currentData[i] = np.log10(np.abs(currentData[i])) + 6
            currentData[i] = np.where(currentData[i] == -np.inf, -3, currentData[i])

        # 判断是否处于悬停状态
        peakStart = keyPara["le_PeakStart"]
        peakEnd = keyPara["le_PeakEnd"]
        trueIdx = np.where(
            (condCheckB >= peakEnd) & (condCheckB <= peakStart) & (condCheckF >= peakEnd) & (
                    condCheckF <= peakStart),
            True, False)
        currentData = currentData[trueIdx]
        condData = condData[trueIdx]
        biasVData = biasVData[trueIdx]

        # 再次检查！！！
        if biasVData.shape[0] == 0:
            return None, None, None
        else:
            return currentData, condData, biasVData

    @classmethod
    def getPartitionData(cls, currentData, condData, biasVData):

        """
        在matlab的版本里面，还要将数据叠加成矩阵，然后再绘图，这里我认为不再需要这样操作！直接hisd2d绘图就可以了！！
        另外此处应该将数据扁平化处理！！
        """
        # 这里的数据已经经过所需处理，这里只是负责拆分， 至少有一组数据
        biasVDataFor = []
        currentDataFor = []
        condDataFor = []

        biasVDataReve = []
        currentDataReve = []
        condDataReve = []

        biasVDataFlat = []
        currentDataFlat = []
        condDataFlat = []
        for i in range(biasVData.shape[0]):
            trace = biasVData[i]
            peak_idx = np.where((trace == trace.max()) | (trace == trace.min()))[0]
            forward_scan = []
            reverse_scan = []
            if trace[peak_idx[0]] == trace.max(): # 起始是从0 到 1正扫
                forward_scan.append((0, peak_idx[0]))
                forward_scan.append((peak_idx[-1], len(trace)-1))
            if trace[peak_idx[0]] == trace.min(): # 起始是从0到-1 反扫
                reverse_scan.append((0, peak_idx[0]))
                reverse_scan.append((peak_idx[-1], len(trace)-1))
            for j in range(len(peak_idx)-1):
                cur_idx = peak_idx[j]
                next_idx = peak_idx[j+1]
                if trace[cur_idx] < trace[next_idx]: # 正扫
                    forward_scan.append((cur_idx, next_idx))
                elif trace[cur_idx] > trace[next_idx]: #反扫
                    reverse_scan.append((cur_idx, next_idx))
            # 正向数据提取
            for v in forward_scan:
                biasVDataFor.append(biasVData[i][v[0]:v[1]+1])
                currentDataFor.append(currentData[i][v[0]:v[1]+1])
                condDataFor.append(condData[i][v[0]:v[1]+1])
                
                biasVDataFlat.append(biasVData[i][v[0]:v[1]+1])
                currentDataFlat.append(currentData[i][v[0]:v[1]+1])
                condDataFlat.append(condData[i][v[0]:v[1]+1])
            # 反向数据提取
            for v in reverse_scan:
                biasVDataReve.append(biasVData[i][v[0]:v[1]+1])
                currentDataReve.append(currentData[i][v[0]:v[1]+1])
                condDataReve.append(condData[i][v[0]:v[1]+1])
                
                biasVDataFlat.append(biasVData[i][v[0]:v[1]+1])
                currentDataFlat.append(currentData[i][v[0]:v[1]+1])
                condDataFlat.append(condData[i][v[0]:v[1]+1])
        
        biasVDataFor = np.concatenate(biasVDataFor)
        currentDataFor = np.concatenate(currentDataFor)
        condDataFor = np.concatenate(condDataFor)

        biasVDataReve = np.concatenate(biasVDataReve)
        currentDataReve = np.concatenate(currentDataReve)
        condDataReve = np.concatenate(condDataReve)

        biasVDataFlat = np.concatenate(biasVDataFlat)
        currentDataFlat = np.concatenate(currentDataFlat)
        condDataFlat = np.concatenate(condDataFlat)
        return biasVDataFor, currentDataFor, condDataFor, biasVDataReve, currentDataReve, condDataReve, biasVDataFlat, currentDataFlat, condDataFlat
