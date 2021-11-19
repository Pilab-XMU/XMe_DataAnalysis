# -*- coding: utf-8 -*-
# @Time   : 2021/9/8 22:09
# @Author : Gang
# @File   : drawDataProcessUtils.py

import numpy as np
from basicAnalysisConst import *
from myLog.MyLog import *


class DrawDataProcessUtils:
    logger = MyLog("DrawDataProcessUtils", BASEDIR)

    @classmethod
    def calculate_draw_data(cls, data, key_para):
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        STRETCHING_RATE = key_para["le_Stretching_Rate"]
        PIEZO_RATE = key_para["le_Piezo_Rate"]
        # TODO
        # piezo的使用还没有加进来，问题的关键就是这个换算关系取决于压电，就很蛋疼

        FACTOR = STRETCHING_RATE / SAMPLING_RATE
        log_G, start, zero, end, len_high, len_low, *_ = data
        ALL_TRACE_NUM = len(start)
        SELECT_TRACE_NUM = ALL_TRACE_NUM
        # datacut_temp=[[[(j-zero[i])*FACTOR,log_G[j]] for j in range(start[i],end[i])]for i in range(TRUE_NUM)]
        #  上的这种写法先放放
        # 经过实验，可以知道的是上面这种写法被淘汰，另外，下面的双循环的方法可以被下面的矢量化的方法部分取代
        # distance=np.array([[(j-zero[i])*FACTOR for j in range(start[i],end[i])] for i in range(ALL_TRACE_NUM)])
        # conductance=np.array([[log_G[j] for j in range(start[i],end[i])] for i in range(ALL_TRACE_NUM)])
        # length=np.array([(len_low[i]-len_high[i])*FACTOR for i in range(ALL_TRACE_NUM)])
        distance = np.array([(np.arange(start[i], end[i]) - zero[i]) * FACTOR for i in range(ALL_TRACE_NUM)])
        conductance = np.array([log_G[np.arange(start[i], end[i])] for i in range(ALL_TRACE_NUM)])
        length = (len_low - len_high) * FACTOR

        distance_draw = distance.reshape(-1)
        conductance_draw = conductance.reshape(-1)

        return distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM

    @classmethod
    def calculate_draw_data_with_select(cls, data, key_para):
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        STRETCHING_RATE = key_para["le_Stretching_Rate"]
        PIEZO_RATE = key_para["le_Piezo_Rate"]
        UPPER_LIMIT1 = key_para["le_Upper_Limit1"]
        UPPER_LIMIT2 = key_para["le_Upper_Limit2"]
        LOW_LIMIT1 = key_para["le_Low_Limit1"]
        LOW_LIMIT2 = key_para["le_Low_Limit2"]

        FACTOR = STRETCHING_RATE / SAMPLING_RATE
        log_G, start, zero, end, len_high, len_low, start1, end1, start2, end2 = data
        ALL_TRACE_NUM = len(start)

        # VALID_TRACE_INDEX=[]
        # for i in range(TRUE_NUM):
        #     temp1=(end1[i]-start1[i])*FACTOR
        #     temp2=(end2[i]-start2[i])*FACTOR
        #     if temp1>UPPER_LIMIT1 or temp1>UPPER_LIMIT2 or temp1<LOW_LIMIT1 or temp2<LOW_LIMIT2:
        #         continue
        #     VALID_TRACE_INDEX.append(i)
        # 我认为下面的写法效率更高，可以等后面测试

        temp1 = (end1 - start1) * FACTOR
        temp2 = (end2 - start2) * FACTOR
        VALID_TRACE_INDEX = \
            np.where((temp1 >= LOW_LIMIT1) & (temp1 <= UPPER_LIMIT1) & (temp2 >= LOW_LIMIT2) & (temp2 <= UPPER_LIMIT2))[
                0]

        distance = np.array([(np.arange(start[i], end[i]) - zero[i]) * FACTOR for i in VALID_TRACE_INDEX])
        conductance = np.array([log_G[np.arange(start[i], end[i])] for i in VALID_TRACE_INDEX])
        length = np.array([(len_low[i] - len_high[i]) * FACTOR for i in VALID_TRACE_INDEX])
        distance_draw = distance.reshape(-1)
        conductance_draw = conductance.reshape(-1)

        SELECT_TRACE_NUM = len(VALID_TRACE_INDEX)

        return distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM

    @classmethod
    def calculate_draw_data_close(cls, data, key_para):
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        STRETCHING_RATE = key_para["le_Stretching_Rate"]
        PIEZO_RATE = key_para["le_Piezo_Rate"]
        # TODO
        # piezo的使用还没有加进来，问题的关键就是这个换算关系取决于压电，就很蛋疼

        FACTOR = STRETCHING_RATE / SAMPLING_RATE
        log_G, start, zero, end, len_high, len_low, *_ = data
        ALL_TRACE_NUM = len(start)
        SELECT_TRACE_NUM = ALL_TRACE_NUM

        distance = np.array([(zero[i] - np.arange(start[i], end[i])) * FACTOR for i in range(ALL_TRACE_NUM)])
        conductance = np.array([log_G[np.arange(start[i], end[i])] for i in range(ALL_TRACE_NUM)])
        length = (len_high - len_low) * FACTOR

        distance_draw = distance.reshape(-1)
        conductance_draw = conductance.reshape(-1)

        return distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM

    @classmethod
    def calculate_draw_data_close_with_select(cls, data, key_para):
        SAMPLING_RATE = key_para["le_Sampling_Rate"]
        STRETCHING_RATE = key_para["le_Stretching_Rate"]
        PIEZO_RATE = key_para["le_Piezo_Rate"]
        UPPER_LIMIT1 = key_para["le_Upper_Limit1"]
        UPPER_LIMIT2 = key_para["le_Upper_Limit2"]
        LOW_LIMIT1 = key_para["le_Low_Limit1"]
        LOW_LIMIT2 = key_para["le_Low_Limit2"]

        FACTOR = STRETCHING_RATE / SAMPLING_RATE
        log_G, start, zero, end, len_high, len_low, start1, end1, start2, end2 = data
        ALL_TRACE_NUM = len(start)

        temp1 = (start1 - end1) * FACTOR
        temp2 = (start2 - end2) * FACTOR
        VALID_TRACE_INDEX = np.where(
            (temp1 >= LOW_LIMIT1) & (temp1 <= UPPER_LIMIT1) & (temp2 >= LOW_LIMIT2) & (temp2 <= UPPER_LIMIT2)
        )[0]

        distance = np.array([(zero[i] - np.arange(start[i], end[i])) * FACTOR for i in VALID_TRACE_INDEX])
        conductance = np.array([log_G[np.arange(start[i], end[i])] for i in VALID_TRACE_INDEX])
        length = np.array([(len_high[i] - len_low[i]) * FACTOR for i in VALID_TRACE_INDEX])
        distance_draw = distance.reshape(-1)
        conductance_draw = conductance.reshape(-1)

        SELECT_TRACE_NUM = len(VALID_TRACE_INDEX)

        return distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM

