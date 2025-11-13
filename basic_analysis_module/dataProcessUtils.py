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

def cross_threshold(a, b, threshold):
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
        STEP = WIN_R
        JUMP_GAP = int(key_para["le_Jump_Gap"])
        ADDITIONAL_LENGTH = int(key_para["le_Additional_Length"])
        data_length = len(log_G)

        start, end, zero, len_high, len_low = {}, {}, {}, {}, {}

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
                    if cross_threshold(prev, post, HIGH_CUT):
                        start[n] = index
                        end[n] = index + ADDITIONAL_LENGTH # 确定截取片段的起点终点
                        index += STEP
                        continue
                    if cross_threshold(prev, post, ZERO_SET):
                        zero[n] = index
                    if cross_threshold(prev, post, HIGH_LENGTH):
                        len_high[n] = index
                        index += STEP
                        continue
                    if cross_threshold(prev, post, LOW_LENGTH):
                        len_low[n] = index
                    if n in start.keys() and n in zero.keys() and n in len_high.keys() and n in len_low.keys() and \
                    len_low.get(n) > len_high.get(n) >= zero.get(n) > start.get(n):
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
        
        
        TRUE_LENGTH = min(len(start), len(zero), len(end), len(len_low), len(len_high)) - 1

        start = np.array(list(start.values())[:TRUE_LENGTH])
        zero = np.array(list(zero.values())[:TRUE_LENGTH])
        end = np.array(list(end.values())[:TRUE_LENGTH])
        len_high = np.array(list(len_high.values())[:TRUE_LENGTH])
        len_low = np.array(list(len_low.values())[:TRUE_LENGTH])

        # TOTAL = len(start)
        # for i in range(TOTAL):
        #     if i < TOTAL - 1:
        #         min_idx = cls._argmin(log_G[start[i]: start[i+1]]) + start[i]
        #     else:
        #         min_idx = cls._argmin(log_G[start[i]:]) + start[i]
        #     h, l = cls._get_interval(log_G[start[i]: min_idx], [LOW_LENGTH, HIGH_LENGTH],STEP)
        #     if h is not None and l is not None:
        #         len_high[i] = h + start[i]
        #         len_low[i] = l + start[i]
        #np.savez('temp_v2.npz', cond = log_G, start = start, zero = zero, end = end, len_high = len_high, len_low = len_low)

        return start, zero, end, len_high, len_low

    @classmethod
    def _get_interval(cls, cond, cond_range, STEP):
        idx = STEP
        start = None
        end = None
        last = len(cond) - STEP
        cond_high = np.max(cond_range)
        cond_low = np.min(cond_range)
        while idx < last:
            prev = np.mean(cond[idx - STEP:idx])
            cur = np.mean(cond[idx:idx + STEP])
            if prev >= cond_high and cur <= cond_high and start is None and cond[idx] <= cond_high:
                start = idx
            elif prev >= cond_low and cur <= cond_low and end is None:
                end = idx
            if start is not None and end is not None:
                break
            idx += 1
        if start is None:
            temp = np.where(cond <= cond_high)[0]
            if len(temp) > 0:
                start = temp[0]
        if end is None:
            temp = np.where(cond <= cond_low)[0]
            if len(temp) > 0:
                end = temp[-1]
        if start is None or end is None:
            return None, None
        if start  > end:
            return None, None
        return start, end
    @classmethod
    def _argmin(cls, data):
        arr = np.ma.masked_invalid(data)
        if not arr.mask.all():
            return np.argmin(arr)
        return len(data) - 1

    @classmethod
    def cut_open_trace_with_select(cls, log_G, key_para):
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        WIN_R = max(cls.get_step_from_sampling(SAMPLING_RATE) , 1)
        START1 = key_para["le_Start1"]
        END1 = key_para["le_End1"]
        START2 = key_para["le_Start2"]
        END2 = key_para["le_End2"]

        start, end, zero, len_high, len_low = cls.cut_open_trace(log_G, key_para)
        start1 = np.ones_like(start)
        end1 = np.ones_like(start)
        start2 = np.ones_like(start)
        end2 = np.ones_like(start)
        VALID_MASK = np.ones_like(start, dtype=bool)

        COND_HIGH_1 = max(START1, END1)
        COND_LOW_1 = min(START1, END1)
        COND_HIGH_2 = max(START2, END2)
        COND_LOW_2 = min(START2, END2)
        
        TOTAL = len(start)
        for i in range(TOTAL):
            if i < TOTAL - 1:
                min_idx = cls._argmin(log_G[start[i]: start[i+1]]) + start[i]
            else:
                min_idx = cls._argmin(log_G[start[i]:]) + start[i]
            s1, e1 = cls._get_interval(log_G[start[i]:min_idx], [COND_LOW_1, COND_HIGH_1], WIN_R)
            s2, e2 = cls._get_interval(log_G[start[i]:min_idx], [COND_LOW_2, COND_HIGH_2], WIN_R)
            if s1 is None or e1 is None or s2 is None or e2 is None:
                VALID_MASK[i] = False
            else:
                start1[i] = s1 + start[i]
                end1[i] = e1 + start[i]
                start2[i] = s2 + start[i]
                end2[i] = e2 + start[i]
        start = start[VALID_MASK]
        end = end[VALID_MASK]
        zero = zero[VALID_MASK]
        len_high = len_high[VALID_MASK]
        len_low = len_low[VALID_MASK]
        start1 = start1[VALID_MASK]
        end1 = end1[VALID_MASK]
        start2 = start2[VALID_MASK]
        end2 = end2[VALID_MASK]
        return start, zero, end, len_high, len_low, start1, end1, start2, end2, TOTAL
                

    @classmethod
    def get_step_from_sampling(cls, SAMPLING_RATE):
        """
        根据采样频率自动计算步长
        :param SAMPLING_RATE:
        :return: 步长（int）
        """
        step = int(SAMPLING_RATE / 1000)
        step = max(step, 1)
        return step
