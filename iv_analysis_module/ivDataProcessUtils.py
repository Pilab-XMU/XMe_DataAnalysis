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
        """返回偏压，电导，电流三个二维数组，每一条占用一行
        """
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

        # 得到扫面区间，接下来就是把中间的切开！！
        for i in range(startIdx.shape[0]):
            biasVTrace.append(biasVolt[startIdx[i]:endIdx[i]+1])
            currentTrace.append(current[startIdx[i]:endIdx[i]+1])
            condTrace.append(cond[startIdx[i]:endIdx[i]])
        biasVTrace = np.array(biasVTrace, dtype='object')
        currentTrace = np.array(currentTrace, dtype='object')
        condTrace = np.array(condTrace, dtype='object')

        if biasVTrace.shape[0] == 0:
            return None, None, None
        

        condPeakStart = keyPara["le_PeakStart"]
        condPeakEnd = keyPara["le_PeakEnd"]
        # 寻找电压是0v的起始和终点
        cutStart, cutEnd = np.ones(biasVTrace.shape[0], dtype=int), np.ones(biasVTrace.shape[0], dtype=int)
        for i in range(biasVTrace.shape[0]):
            trace = biasVTrace[i]
            zero_idx = np.where(np.isclose(trace, 0, 0.0001))[0]

            # 条件1 至少3个零点
            # if (len(zero_idx) < 3):
            #     continue

            # 条件2 必须有从2*bias_base-> 0 和 从 0 -> 2*bias_base的跳跃
            if abs(trace[zero_idx[0]-1] - 2 * bias_base) > 0.0001 and abs(trace[zero_idx[-1]+1] - 2*bias_base) > 0.0001:
                continue

            # 条件3 偏压在2*bias_base时的平均电导必须在范围内
            cond_start = condTrace[i][:zero_idx[0]-1]
            cond_end = condTrace[i][zero_idx[-1]+1:]
            cond_start_mean = cond_start[np.isfinite(cond_start)].mean()
            cond_end_mean = cond_end[np.isfinite(cond_end)].mean()
            if cond_start_mean < condPeakEnd or cond_start_mean > condPeakStart or cond_end_mean < condPeakEnd or cond_end_mean > condPeakStart:
                continue

            for j in range(zero_idx.shape[0] - 1): # 找到正式扫描的起点
                if (zero_idx[j+1] - zero_idx[j] > 1) and (trace[zero_idx[j]+1] != 0):
                    cutStart[i] = zero_idx[j]
                    break
            if cutStart[i] == 1:
                continue
            # 寻找可能的终点
            temp_end = 1
            for j in range(zero_idx.shape[0]-1, 0, -1):
                if zero_idx[j] - zero_idx[j - 1] > 1:
                    temp_end = zero_idx[j]
                    break
            if temp_end == 1:
                continue
            # 此时cut_start[i] 和 temp_end 必然不是1
            peak_index = np.where((trace == trace.min()) | (trace == trace.max()))[0]
            first_peak = peak_index[0]
            if trace[first_peak] > 0 and trace[temp_end - 1] > 0:  # 从0到1，结尾必须从-1到0
                for j in range(temp_end - 1, 0, -1):
                    if trace[j] <= 0 and trace[j + 1] > 0:
                        temp_end = j
                        break
            elif trace[first_peak] < 0 and trace[temp_end - 1] < 0:  # 从0到-1，结尾必须从1到0
                for j in range(temp_end - 1, 0, -1):
                    if trace[j] >= 0 and trace[i][j + 1] < 0:
                        temp_end = j
                        break
            cutEnd[i] = temp_end
        
        # 删除不完整的
        trueIndex = np.where((cutStart == 1) | (cutEnd == 1), False, True)
        biasVTrace = biasVTrace[trueIndex]
        currentTrace = currentTrace[trueIndex]
        condTrace = condTrace[trueIndex]
        cutStart = cutStart[trueIndex]
        cutEnd = cutEnd[trueIndex]
        # 再次检查！！！
        if biasVTrace.shape[0] == 0:
            return None, None, None

        # 通过偏压把电导曲线切出来
        # 注意这里的这几个data其中每一行的数据维度都是不一致的！
        biasVData = np.empty(biasVTrace.shape[0], dtype=object)
        currentData = np.empty(biasVTrace.shape[0], dtype=object)
        condData = np.empty(biasVTrace.shape[0], dtype=object)

        for i in range(biasVTrace.shape[0]):
            biasVData[i] = biasVTrace[i][cutStart[i]:cutEnd[i]+1]
            currentData[i] = currentTrace[i][cutStart[i]:cutEnd[i]+1]
            condData[i] = condTrace[i][cutStart[i]:cutEnd[i]+1]

        # 对电流进行处理
        for i in range(currentData.shape[0]):
            currentData[i] = np.log10(np.abs(currentData[i])) + 6
            currentData[i] = np.where(currentData[i] == -np.inf, -3, currentData[i])

        # 删除超过scanRange的数据
        scanRange = keyPara["le_ScanRange"] + 0.0001
        tureIdx = [(data <= scanRange).all() for data in biasVData]
        biasVData = biasVData[tureIdx]
        currentData = currentData[tureIdx]
        condData = condData[tureIdx]
        condTrace = condTrace[tureIdx]
        # 再次检查！！！
        if biasVData.shape[0] == 0:
            return None, None, None
        else:
            return currentData, condData, biasVData, condTrace

    @classmethod
    def getPartitionData(cls, currentData, condData, biasVData):
        # 这里的数据已经经过所需处理，这里只是负责拆分， 至少有一组数据
        biasVDataFor = []
        currentDataFor = []
        condDataFor = []

        biasVDataReve = []
        currentDataReve = []
        condDataReve = []

        for_length = []
        reve_length = []
        for i in range(biasVData.shape[0]):
            trace = np.asarray(biasVData[i])
            peak_idx = np.where((trace == trace.max()) | (trace == trace.min()))[0]
            forward_scan = []
            reverse_scan = []
            if trace[peak_idx[0]] == trace.max(): # 起始是从0 到 1正扫
                biasVDataFor.append(np.concatenate([trace[peak_idx[-1]:], trace[:peak_idx[0]+1]]))
                currentDataFor.append(np.concatenate([currentData[i][peak_idx[-1]:], currentData[i][:peak_idx[0]+1]]))
                condDataFor.append(np.concatenate([condData[i][peak_idx[-1]:], condData[i][:peak_idx[0]+1]]))
                for_length.append(len(biasVDataFor[-1]))
            if trace[peak_idx[0]] == trace.min(): # 起始是从0到-1 反扫
                biasVDataReve.append(np.concatenate([trace[peak_idx[-1]:], trace[:peak_idx[0]+1]]))
                currentDataReve.append(np.concatenate([currentData[i][peak_idx[-1]:], currentData[i][:peak_idx[0]+1]]))
                condDataReve.append(np.concatenate([condData[i][peak_idx[-1]:], condData[i][:peak_idx[0]+1]]))
                reve_length.append(len(biasVDataReve[-1]))
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
                for_length.append(len(biasVDataFor[-1]))
            # 反向数据提取
            for v in reverse_scan:
                biasVDataReve.append(biasVData[i][v[0]:v[1]+1])
                currentDataReve.append(currentData[i][v[0]:v[1]+1])
                condDataReve.append(condData[i][v[0]:v[1]+1])
                reve_length.append(len(biasVDataReve[-1]))
        numOfTrace = min(len(biasVDataFor), len(biasVDataReve))
        biasVDataFor = np.concatenate(biasVDataFor[:numOfTrace])
        currentDataFor = np.concatenate(currentDataFor[:numOfTrace])
        condDataFor = np.concatenate(condDataFor[:numOfTrace])

        biasVDataReve = np.concatenate(biasVDataReve[:numOfTrace])
        currentDataReve = np.concatenate(currentDataReve[:numOfTrace])
        condDataReve = np.concatenate(condDataReve[:numOfTrace])
        return biasVDataFor, currentDataFor, condDataFor, biasVDataReve, currentDataReve, condDataReve, numOfTrace, for_length, reve_length
