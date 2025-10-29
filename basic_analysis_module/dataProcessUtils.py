# -*- coding: utf-8 -*-
# @Time   : 2020/11/17 19:52
# @Author : Gang
# @File   : dataProcessUtils.py

from nptdms import TdmsFile
import numpy as np
import numexpr as ne
from gangLogger.myLog import MyLog
from basicAnalysisConst import *


_9_DEVICE_PARAM_MAP = {
    0: ("DEVICE_0_PARA", "le_STM41"),
    1: ("DEVICE_1_PARA", "le_STM40"),
    2: ("DEVICE_2_PARA", "le_MCBJ41"),
    4: ("DEVICE_4_PARA", "le_STMTHERMO"),
}

def cross_threshold(a, b, threshold, direction='falling'):
    if direction == "rising":  # 上升沿
        return a <= threshold <= b
    else:  # 下降沿
        return a - threshold >= 0 and b - threshold <= 0
        
def get_new_start(log_G, cond_high, start_idx, high_old, STEP):
    STEP_NEW = STEP // 2
    idx = start_idx + STEP_NEW
    high_new = high_old
    while idx < high_old + STEP_NEW:
        pre = np.mean(log_G[idx - STEP_NEW:idx])
        post = np.mean(log_G[idx: idx + STEP_NEW])
        if cross_threshold(pre, post, cond_high):  # 满足条件
            high_new = idx
            break
        idx += STEP_NEW
    return high_new


class DataProcessUtils:
    logger = MyLog("DataProcessUtils", BASEDIR)

    @classmethod
    def creatFolder(cls, baseDir, folderName):
        folderPath = os.path.join(baseDir, folderName)
        if os.path.exists(folderPath):
            cls.logger.debug(f"目标路径已存在：{folderPath}")
        else:
            os.mkdir(folderPath)
            cls.logger.debug(f"已创建目标路径:{folderPath}")

    @classmethod
    def load_TMDS_file(cls, file_path):
        """
        加载tdms文件（单个）
        :param file_path:tdms文件路径
        :return:采样电压（numpy）
        """
        with TdmsFile.open(file_path) as tdms_file:
            samp_v = tdms_file.groups()[0].channels()[0][:]  # 此处读完数据就是numpy数组了
        return samp_v

    @classmethod
    def load_TMDS_file_multi(cls, file_path_list):
        """
        加载tdms文件（多个）
        :param file_path_list:tdms文件路径（list）
        :return:采样电压（numpy）
        """
        samp_v = []
        for file_path in file_path_list:
            try:
                temp = cls.load_TMDS_file(file_path)
            except Exception as e:
                errMsg = f"数据文件部分异常，文件名：{file_path},异常信息：{e}"
                cls.logger.error(errMsg)
            else:
                samp_v.extend(temp)
        return np.array(samp_v)
    
    @classmethod
    def get_logG(cls, file_path, key_para):
        """
        计算电导值
        :param file_path: 因为要使用多进程处理数据，这里传入的是单个tdms文件的路径
        :param key_para: 参数
        :return: 电导
        """
        samp_v = cls.load_TMDS_file(file_path)
        device_id = key_para["DEVICE_ID"]
        current = cls.get_current(samp_v, device_id, key_para)
        bias_V = key_para["le_BiasV"]
        log_G = np.log10(np.abs(current * 12886.6 / bias_V))
        return log_G

    @classmethod
    def get_current(cls, samp_v, device_id, key_para):
        currentPre = cls.get_currentPre(samp_v, device_id, key_para)
        background = cls.cal_background(currentPre)
        current = cls.remove_bg(currentPre, background)
        return current
    @classmethod
    def get_currentPre(cls, samp_v, device_id, key_para):
        if device_id == 3:
            currentPre = cls.get_currentPre_id_3(samp_v, key_para)
        else:
            currentPre = cls.get_currentPre_9_params(samp_v, device_id, key_para)
        return currentPre

    @classmethod
    def get_currentPre_9_params(cls, samp_v, device_id, key_para):
        """
        STMTHERMO的电流计算
        :param samp_v:采样电压
        :param key_para: 拟合参数
        :return: currentPre
        """
        para_key, para_prefix = _9_DEVICE_PARAM_MAP[device_id]
        p = key_para[para_key]
        offset = p.get(f'{para_prefix}_offset') if f'{para_prefix}_offset' in p else p.get(f'{para_prefix}_e1')
        a1 = p[f'{para_prefix}_a1']
        b1 = p[f'{para_prefix}_b1']
        c1 = p[f'{para_prefix}_c1']
        d1 = p[f'{para_prefix}_d1']
        a2 = p[f'{para_prefix}_a2']
        b2 = p[f'{para_prefix}_b2']
        c2 = p[f'{para_prefix}_c2']
        d2 = p[f'{para_prefix}_d2']
        samp_v = samp_v - offset
        currentPre = ne.evaluate("where(samp_v >= 0,exp(a2 * samp_v + b2)+ c2 * samp_v + d2, exp(a1 * samp_v + b1) + c1 * samp_v + d1)")
        return currentPre


    @classmethod
    def get_currentPre_id_3(cls, samp_v, key_para):
        """
        STMNEW的电流计算
        :param samp_v:采样电压
        :param key_para: 拟合参数
        :return: currentPre
        """
        p = key_para["DEVICE_3_PARA"]
        offset = p["le_STMNEW_offset"]
        a2 = p['le_STMNEW_a2']
        b2 = p['le_STMNEW_b2']
        a1 = p['le_STMNEW_a1']
        b1 = p['le_STMNEW_b1']
        samp_v = samp_v - offset
        currentPre = np.where(samp_v >= 0, np.power(10., a2 * samp_v + b2), np.power(10., a1 * samp_v + b1))
        return currentPre
    

    @classmethod
    def cal_background(cls, cp):
        """
        计算背景电流
        :param cp: currentPre
        :return: 背景电流值
        """
        """
        这套算法是自己设计的！！！！
        """
        length = len(cp)
        index = length // 3
        hist, bin_edges = np.histogram(cp[index:2 * index], bins=30, range=(0, 7.76e-11))
        if max(hist) == 0:
            background = 1e-12
        else:
            max_index = np.argmax(hist)
            background = (bin_edges[max_index] + bin_edges[max_index + 1]) / 2
        return background

    @classmethod
    def remove_bg(cls, cp, bg):
        """
        去掉背景电流
        :param cp: currentPre
        :param bg: 背景电流
        :return: 电流
        """
        current = ne.evaluate("cp - bg")
        return current

    @classmethod
    def cut_trace(cls, log_G, key_para):
        """
        暂时没用呵呵呵呵
        :param log_G:
        :param key_para:
        :return:
        """
        SELECT_OPTION = key_para["SELECT_OPTION"]
        if key_para["PROCESS"] == 0:
            if not SELECT_OPTION:
                cls.cut_open_trace(log_G, key_para)
        else:
            cls.cut_close_trace(log_G, key_para)

    @classmethod
    def cut_close_trace(cls, log_G, key_para):
        """
        处理close过程的数据
        :param log_G:
        :param key_para:
        :return:
        """

        HIGH_CUT = key_para["le_High_Cut"]
        HIGH_LENGTH = key_para["le_High_Length"]
        LOW_LENGTH = key_para["le_Low_Length"]
        ZERO_SET = key_para["le_Zero_Set"]
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        STEP = cls.get_step_from_sampling(SAMPLING_RATE)
        JUMP_GAP = int(key_para["le_Jump_Gap"])
        ADDITIONAL_LENGTH = int(key_para["le_Additional_Length"])
        data_length = len(log_G)

        start, end, zero, len_high, len_low = {}, {}, {}, {}, {}
        start1, end1, start2, end2 = {}, {}, {}, {}

        n = 0  # n表示条数序列索引
        IS_RISE_STEP = STEP * 5  # 表示判断是否处于上升过程的step长度，用处：避免重复计算
        ENDINDEX = data_length - STEP * 10
        index = STEP * 10  # index表示点的序列索引

        while index < ENDINDEX:
            try:
                if np.mean(log_G[index - IS_RISE_STEP:index]) < np.mean(log_G[index:index + IS_RISE_STEP]):
                    temp1 = np.mean(log_G[index - STEP:index])
                    temp2 = np.mean(log_G[index:index + STEP])
                    if temp1 <= LOW_LENGTH <= temp2:
                        len_low[n] = index
                    if temp1 <= HIGH_LENGTH <= temp2:
                        len_high[n] = index
                    if temp1 <= ZERO_SET <= temp2:
                        zero[n] = index
                    if temp1 <= HIGH_CUT <= temp2:
                        end[n] = index
                        start[n] = index - ADDITIONAL_LENGTH
                    if n in len_low.keys() and n in len_high.keys() and n in zero.keys() and n in end.keys() and len_low.get(
                            n) < len_high.get(n) <= zero.get(n) < end.get(n):
                        n += 1
                        index += JUMP_GAP
                        continue
                    index += STEP
                else:
                    index += STEP

            except Exception as e:
                errMsg = f"CUT SINGLE TRACE ERROR:{e}"
                cls.logger.error(errMsg)
                break

        TRUE_LENGTH = min(len(len_low), len(len_high), len(zero), len(end), len(start))
        len_low, len_high, zero, end, start = np.array(list(len_low.values()))[1:TRUE_LENGTH], np.array(
            list(len_high.values()))[1:TRUE_LENGTH], np.array(list(zero.values()))[1:TRUE_LENGTH], np.array(
            list(end.values()))[1:TRUE_LENGTH], np.array(list(start.values()))[1:TRUE_LENGTH]

        return start, zero, end, len_high, len_low, start1, end1, start2, end2

    @classmethod
    def cut_close_trace_with_select(cls, log_G, key_para):
        HIGH_CUT = key_para["le_High_Cut"]
        HIGH_LENGTH = key_para["le_High_Length"]
        LOW_LENGTH = key_para["le_Low_Length"]
        ZERO_SET = key_para["le_Zero_Set"]
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        STEP = cls.get_step_from_sampling(SAMPLING_RATE)
        JUMP_GAP = int(key_para["le_Jump_Gap"])
        ADDITIONAL_LENGTH = int(key_para["le_Additional_Length"])
        START1 = key_para["le_Start1"]
        END1 = key_para["le_End1"]
        START2 = key_para["le_Start2"]
        END2 = key_para["le_End2"]
        data_length = len(log_G)

        start, end, zero, len_high, len_low = {}, {}, {}, {}, {}
        start1, end1, start2, end2 = {}, {}, {}, {}

        n = 0  # n表示条数序列索引
        IS_RISE_STEP = STEP * 5  # 表示判断是否处于上升过程的step长度，用处：避免重复计算
        ENDINDEX = data_length - STEP * 10
        index = STEP * 10  # index表示点的序列索引

        while index < ENDINDEX:
            try:
                if np.mean(log_G[index - IS_RISE_STEP:index]) < np.mean(log_G[index:index + IS_RISE_STEP]):
                    temp1 = np.mean(log_G[index - STEP:index])
                    temp2 = np.mean(log_G[index:index + STEP])
                    if temp1 - LOW_LENGTH >= 0 and temp2 - LOW_LENGTH <= 0:
                        len_low[n] = index
                    if temp1 - HIGH_LENGTH >= 0 and temp2 - HIGH_LENGTH <= 0:
                        len_high[n] = index
                    if temp1 - ZERO_SET >= 0 and temp2 - ZERO_SET <= 0:
                        zero[n] = index
                    if temp1 - HIGH_CUT >= 0 and temp2 - HIGH_CUT <= 0:
                        end[n] = index
                        start[n] = index - ADDITIONAL_LENGTH
                    if temp1 - START1 >= 0 and temp2 - START1 <= 0:
                        start1[n] = index
                    if temp1 - END1 >= 0 and temp2 - END1 <= 0:
                        end1[n] = index
                    if temp1 - START2 >= 0 and temp2 - START2 <= 0:
                        start2[n] = index
                    if temp1 - END2 >= 0 and temp2 - END2 <= 0:
                        end2[n] = index

                    if n in len_low.keys() and n in len_high.keys() and n in zero.keys() and n in end.keys() and n in start1.keys() and n in start2.keys() and n in end1.keys() and n in end2.keys() \
                            and len_low.get(n) < len_high.get(n) <= zero.get(n) < end.get(n) \
                            and start1.get(n) > end1.get(n) and start2.get(n) > end2.get(n):
                        n += 1
                        index += JUMP_GAP
                        continue
                    index += STEP
                else:
                    index += STEP

            except Exception as e:
                errMsg = f"CUT SINGLE TRACE ERROR:{e}"
                cls.logger.error(errMsg)
                break
        TRUE_LENGTH = min(len(len_low), len(len_high), len(zero), len(end), len(start), len(start1), len(start2),
                          len(end1), len(end2))
        len_low, len_high, zero, end, start, start1, start2, end1, end2 = np.array(list(len_low.values()))[1:TRUE_LENGTH], np.array(
            list(len_high.values()))[1:TRUE_LENGTH], np.array(list(zero.values()))[1:TRUE_LENGTH], np.array(
            list(end.values()))[1:TRUE_LENGTH], np.array(list(start.values()))[1:TRUE_LENGTH], np.array(
            list(start1.values()))[1:TRUE_LENGTH], np.array(list(start2.values()))[1:TRUE_LENGTH], np.array(
            list(end1.values()))[1:TRUE_LENGTH], np.array(list(end2.values()))[1:TRUE_LENGTH]

        return start, zero, end, len_high, len_low, start1, end1, start2, end2

    @classmethod
    def cut_open_trace(cls, log_G, key_para):
        """
        处理open过程的数据
        :param log_G:
        :param key_para:
        :return:
        """

        HIGH_CUT = key_para["le_High_Cut"]
        HIGH_LENGTH = key_para["le_High_Length"]
        LOW_LENGTH = key_para["le_Low_Length"]
        ZERO_SET = key_para["le_Zero_Set"]
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        WIN_R = max(cls.get_step_from_sampling(SAMPLING_RATE) , 1) #SAMPLING_RATE / 500
        # STEP = max(int(WIN_R // 2), 1)
        STEP = WIN_R
        JUMP_GAP = int(key_para["le_Jump_Gap"])
        ADDITIONAL_LENGTH = int(key_para["le_Additional_Length"])
        data_length = len(log_G)

        start, end, zero, len_high, len_low = {}, {}, {}, {}, {}
        start1, end1, start2, end2 = {}, {}, {}, {}

        n = 0  # n表示条数序列索引
        IS_DECLINE_STEP = WIN_R * 5  # 表示判断是否处于下降过程的step长度，用处：避免重复计算
        ENDINDEX = data_length - WIN_R * 10
        index = WIN_R * 10  # index表示点的序列索引

        while index < ENDINDEX:
            try:
                if np.mean(log_G[index - IS_DECLINE_STEP:index]) > np.mean(log_G[index:index + IS_DECLINE_STEP]):
                    prev = np.mean(log_G[index - WIN_R:index])
                    post = np.mean(log_G[index:index + WIN_R])
                    if post - HIGH_CUT > 0:
                        index += STEP
                        continue  # 这里提前continue的原因是：处于下降状态的曲线，比高点还高的话，就不用判断下面的了，直接跳过
                    if cross_threshold(prev, post, HIGH_CUT, 'falling'):
                        start[n] = index
                        end[n] = index + ADDITIONAL_LENGTH # 确定截取片段的起点终点
                        index += STEP
                        continue
                    if cross_threshold(prev, post, ZERO_SET, 'falling'):
                        zero[n] = index
                    if cross_threshold(prev, post, HIGH_LENGTH, 'falling'):
                        len_high[n] = index
                        index += STEP
                        continue
                    if cross_threshold(prev, post, LOW_LENGTH, 'falling'):
                        len_low[n] = index
                    if n in start.keys() and n in zero.keys() and n in len_high.keys() and n in len_low.keys() and \
                    len_low.get(n) > len_high.get(n) >= zero.get(n) > start.get(n):
                        # high_new = get_new_start(log_G, HIGH_LENGTH, start[n], len_high[n], STEP)
                        # len_high[n] = high_new
                        n += 1
                        index += JUMP_GAP
                        # STEP = np.random.randint(10, 20)
                        continue
                    index += STEP
                else:
                    index += STEP
            except Exception as e:
                errMsg = f"CUT SINGLE TRACE ERROR:{e}"
                cls.logger.error(errMsg)
                break
        TRUE_LENGTH = min(len(start), len(zero), len(end), len(len_low), len(len_high)) - 1
        # 这个-1 至关重要！！！！！！！！！！

        start = np.array(list(start.values())[:TRUE_LENGTH])
        zero = np.array(list(zero.values())[:TRUE_LENGTH])
        end = np.array(list(end.values())[:TRUE_LENGTH])
        len_high = np.array(list(len_high.values())[:TRUE_LENGTH])
        len_low = np.array(list(len_low.values())[:TRUE_LENGTH])
        np.savez('temp.npz', cond=log_G, start=start, zero=zero, end=end, len_high=len_high, len_low=len_low)
        return start, zero, end, len_high, len_low, start1, end1, start2, end2

    @classmethod
    def cut_open_trace_with_select(cls, log_G, key_para):
        HIGH_CUT = key_para["le_High_Cut"]
        HIGH_LENGTH = key_para["le_High_Length"]
        LOW_LENGTH = key_para["le_Low_Length"]
        ZERO_SET = key_para["le_Zero_Set"]
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        STEP = cls.get_step_from_sampling(SAMPLING_RATE)
        JUMP_GAP = int(key_para["le_Jump_Gap"])
        ADDITIONAL_LENGTH = int(key_para["le_Additional_Length"])
        START1 = key_para["le_Start1"]
        END1 = key_para["le_End1"]
        START2 = key_para["le_Start2"]
        END2 = key_para["le_End2"]
        data_length = len(log_G)

        start, end, zero, len_high, len_low = {}, {}, {}, {}, {}
        start1, end1, start2, end2 = {}, {}, {}, {}

        n = 0  # n表示条数序列索引
        IS_DECLINE_STEP = STEP * 5  # 表示判断是否处于下降过程的step长度，用处：避免重复计算
        ENDINDEX = data_length - STEP * 10
        index = STEP * 10  # index表示点的序列索引

        while index < ENDINDEX:
            try:
                if np.mean(log_G[index - IS_DECLINE_STEP:index]) > np.mean(log_G[index:index + IS_DECLINE_STEP]):
                    temp_1 = np.mean(log_G[index - STEP:index])
                    temp_2 = np.mean(log_G[index:index + STEP])
                    if temp_2 - HIGH_CUT > 0:
                        index += STEP
                        continue  # 这里提前continue的原因是：处于下降状态的曲线，比高点还高的话，就不用判断下面的了，直接跳过
                    if temp_1 - HIGH_CUT >= 0 and temp_2 - HIGH_CUT <= 0:
                        start[n] = index
                        end[n] = index + ADDITIONAL_LENGTH
                        index += STEP
                        continue
                    if temp_1 - ZERO_SET >= 0 and temp_2 - ZERO_SET <= 0:
                        zero[n] = index
                    if temp_1 - HIGH_LENGTH >= 0 and temp_2 - HIGH_LENGTH <= 0:
                        len_high[n] = index
                    if temp_1 - LOW_LENGTH >= 0 and temp_2 - LOW_LENGTH <= 0:
                        len_low[n] = index
                    if temp_1 - START1 >= 0 and temp_2 - START1 <= 0:
                        start1[n] = index
                    if temp_1 - END1 >= 0 and temp_2 - END1 <= 0:
                        end1[n] = index
                    if temp_1 - START2 >= 0 and temp_2 - START2 <= 0:
                        start2[n] = index
                    if temp_1 - END2 >= 0 and temp_2 - END2 <= 0:
                        end2[n] = index

                    if n in start.keys() and n in zero.keys() and n in len_high.keys() and n in start1.keys() and n in end1.keys() and n in start2.keys() and n in end2.keys() and n in len_low.keys() \
                            and len_low.get(n) > len_high.get(n) >= zero.get(n) > start.get(n) \
                            and start1.get(n) < end1.get(n) and start2.get(n) < end2.get(n):
                        n += 1
                        index += JUMP_GAP
                        continue
                    index += STEP
                else:
                    index += STEP
            except Exception as e:
                errMsg = f"CUT SINGLE TRACE ERROR:{e}"
                cls.logger.error(errMsg)
                break
        TRUE_LENGTH = min(len(start), len(zero), len(end), len(len_low), len(len_high), len(start1), len(end1),
                          len(start2),
                          len(end2)) - 1
        start, zero, end, len_high, len_low, start1, end1, start2, end2 = np.array(
            list(start.values()))[:TRUE_LENGTH],  np.array(list(zero.values()))[:TRUE_LENGTH], np.array(
            list(end.values()))[:TRUE_LENGTH], np.array(list(len_high.values()))[:TRUE_LENGTH], np.array(
            list(len_low.values()))[:TRUE_LENGTH], np.array(list(start1.values()))[:TRUE_LENGTH], np.array(
            list(end1.values()))[:TRUE_LENGTH], np.array(list(start2.values()))[:TRUE_LENGTH], np.array(
            list(end2.values()))[:TRUE_LENGTH]
        return start, zero, end, len_high, len_low, start1, end1, start2, end2

    @classmethod
    def get_step_from_sampling(cls, SAMPLING_RATE):
        """
        根据采样频率自动计算步长
        :param SAMPLING_RATE:
        :return: 步长（int）
        """
        return int(SAMPLING_RATE / 500)
