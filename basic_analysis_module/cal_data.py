# -*- coding: utf-8 -*-
# @Time   : 2020/11/30 14:38
# @Author : Gang
# @File   : cal_data.py

import numpy as np

def calculate_draw_data(data,key_para):
    SAMPLING_RATE=key_para["le_Sampling_Rate"]
    STRETCHING_RATE=key_para["le_Stretching_Rate"]
    PIEZO_RATE=key_para["le_Piezo_Rate"]
    # TODO
    #  piezo的使用还没有加进来，问题的关键就是这个换算关系取决于压电，就很蛋疼

    FACTOR=STRETCHING_RATE/SAMPLING_RATE
    log_G, start, zero, end, len_high, len_low, *_=data
    ALL_TRACE_NUM=len(start)
    SELECT_TRACE_NUM=ALL_TRACE_NUM
    distance = np.array([(np.arange(start[i],end[i])-zero[i])*FACTOR for i in range(ALL_TRACE_NUM)])
    condutance = np.array([log_G[np.arange(start[i],end[i])] for i in range(ALL_TRACE_NUM)])
    length = (len_low-len_high)*FACTOR

    distance_draw=distance.reshape(-1)
    condutance_draw=condutance.reshape(-1)

    return distance,condutance,length,distance_draw,condutance_draw,ALL_TRACE_NUM,SELECT_TRACE_NUM

def calculate_draw_data_with_select(data,key_para):
    SAMPLING_RATE = key_para["le_Sampling_Rate"]
    STRETCHING_RATE = key_para["le_Stretching_Rate"]
    PIEZO_RATE = key_para["le_Piezo_Rate"]
    UPPER_LIMIT1=key_para["le_Upper_Limit1"]
    UPPER_LIMIT2=key_para["le_Upper_Limit2"]
    LOW_LIMIT1=key_para["le_Low_Limit1"]
    LOW_LIMIT2=key_para["le_Low_Limit2"]

    FACTOR = STRETCHING_RATE / SAMPLING_RATE
    log_G, start, zero, end, len_high, len_low, start1, end1, start2, end2=data
    ALL_TRACE_NUM = len(start)


    temp1=(end1-start1)*FACTOR
    temp2=(end2-start2)*FACTOR
    VALID_TRACE_INDEX=np.where((temp1>=LOW_LIMIT1) & (temp1<=UPPER_LIMIT1) & (temp2>=LOW_LIMIT2) & (temp2<=UPPER_LIMIT2))[0]

    distance=np.array([(np.arange(start[i],end[i])-zero[i])*FACTOR for i in VALID_TRACE_INDEX])
    condutance = np.array([log_G[np.arange(start[i],end[i])] for i in VALID_TRACE_INDEX])
    length = np.array([(len_low[i] - len_high[i]) * FACTOR for i in VALID_TRACE_INDEX])
    distance_draw = distance.reshape(-1)
    condutance_draw = condutance.reshape(-1)

    SELECT_TRACE_NUM=len(VALID_TRACE_INDEX)

    return distance,condutance,length,distance_draw,condutance_draw,ALL_TRACE_NUM,SELECT_TRACE_NUM