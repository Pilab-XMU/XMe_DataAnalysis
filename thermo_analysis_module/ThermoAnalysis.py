import time
from nptdms import TdmsFile
import numpy as np
import os
from ThermoConst import BASEDIR
from PyQt5.QtCore import QObject, pyqtSignal
from gangLogger.myLog import MyLog
from scipy.optimize import curve_fit
from scipy.fft import fft, ifft

#import debugpy

class ThermoAnalysis(QObject):
    logger = MyLog("ThermoAnalysis", BASEDIR)
    plotRightHist = pyqtSignal()
    plotCenterHist = pyqtSignal()
    plotLeftHist = pyqtSignal()
    runEnd = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, keyPara):
        super().__init__()
        self.keyPara = keyPara
        self.datasets = None

    def run(self):
        #debugpy.debug_this_thread()
        need_filter = self.keyPara['NEED_FILTER']
        fileList = self.keyPara["FILE_PATHS"]
        rightData, centerData, leftData = self.dataRead(fileList)
        
        if len(rightData) == 0 and len(centerData) == 0 and len(leftData) == 0:
            self.error.emit("No vaild data!")
            return
        
        # 开始傅里叶处理right
        
        for item in rightData:
            item['volt'] = self.analysis(item['volt'])
        
        
        # 根据斜率和绝对值过滤
        slope_limit = int(self.keyPara['le_SlopeLimit'])
        abs_mean_limit = int(self.keyPara['le_Abs_Mean_Limit'])
        
        bins = int(self.keyPara['le_BinsX'])
        
        if need_filter:
            centerDataSelect = volt_filter(centerData, slope_limit, abs_mean_limit)
            if len(centerDataSelect) == 0:
                self.error.emit("(Center) No vaild data after filter!")
            else:
                self.centerData = centerDataSelect
                self.centerFit = fit(self.centerData, bins)
                self.plotCenterHist.emit()
        else:
            self.centerData = centerData
            self.centerFit = fit(self.centerData, bins)
            self.plotCenterHist.emit()
        
        if need_filter:
            rightDataSelect = volt_filter(rightData, slope_limit, abs_mean_limit)
            if len(rightDataSelect) == 0:
                self.error.emit("(Right) No vaild data after filter!")
            else:
                self.rightData = rightDataSelect
                self.rightFit = fit(self.rightData, bins)
                self.plotRightHist.emit()
        else:
            self.rightData = rightData
            self.rightFit = fit(self.rightData, bins)
            self.plotRightHist.emit()
        
        if need_filter:
            leftDataSelect = volt_filter(leftData, slope_limit, abs_mean_limit)
            if len(leftDataSelect) == 0:
                self.error.emit("(Left) No vaild data after filter!")
            else:
                self.leftData = leftDataSelect
                self.leftFit = fit(self.leftData, bins)
                self.plotLeftHist.emit()
        else:
            self.leftData = leftData
            self.leftFit = fit(self.leftData, bins)
            self.plotLeftHist.emit()
        self.runEnd.emit()
    
    def dataRead(self, fileList):
        logG_lower = self.keyPara['le_LogG_Lower']
        logG_upper = self.keyPara['le_LogG_Upper']
        hover_lower = int(self.keyPara['le_Extends_For_2V'])
        hover_volt = self.keyPara['le_Hover_Voltage']
        
        # voltHistVector = []
        # currentHistVect = []
        # currentToVHistVect = []
        # rightcurrentToVHistVect = []
        # logGHistVector = []
        # leftVoltHistVector = []
        # rightVoltHistVector = []
        
        rightDataTotal = []
        centerDataTotal = []
        leftDataTotal = []

        for f in fileList:
            biasVolt, volt, current, logG = self.loadTDMSFile(f)
            if biasVolt is None or volt is None or current is None or logG is None:
                continue
            # 切分获得0电压区间
            bias_intervals = self.get_intervals(biasVolt)
            if (len(bias_intervals) == 0):
                continue
            total_len = len(biasVolt)
            # TOT = 4000 # tolerance points
            # POINTS_LIMIT = int(self.keyPara['le_Sample_Freq'] / 20 * (0.15 * 20000 * 2 + TOT))
            POINTS_LIMIT = int(self.keyPara['le_Min_Gap'])
            # # 过滤在0.1V 悬停时间短的
            bias_intervals = filter_by_len(bias_intervals, POINTS_LIMIT, total_len)
            bias_intervals = filter_by_zero(bias_intervals, logG, POINTS_LIMIT, int(self.keyPara['le_Num_Over_Zero']))
            if (len(bias_intervals) == 0):
                continue
            res_intevals, left_intervals, right_intervals, \
                left_means, right_means = filter_by_logG(bias_intervals, biasVolt, logG, (logG_lower, logG_upper), hover_lower, hover_volt)
            
            # 整理结果
            rigthData, centerData, leftData = self.cut(biasVolt, volt, logG, current, res_intevals, left_means, right_means)
            # for i in range(len(centerData)):
            #     voltHistVector += centerData[i]['bias_volt'].tolist()
            #     leftVoltHistVector += leftData[i]['bias_volt'].tolist()
            #     rightVoltHistVector += rightData[i]['bias_volt'].tolist()
            #     logGHistVector += centerData[i]['logG'].tolist()
            #     # ???
            #     currentHistVect += rightData[i]['current'].tolist()
            #     currentToVHistVect += centerData[i]['c2v'].tolist()
            #     rightcurrentToVHistVect += rightData[i]['c2v'].tolist()
            
            rightDataTotal += rigthData
            centerDataTotal += centerData
            leftDataTotal += leftData
            self.logger.debug(f"finish {os.path.basename(f)}")
            
        return rightDataTotal, centerDataTotal, leftDataTotal

    def cut(self, biasVolt, volt, logG, current, intervals, left_means, right_means):
        # TODO: 可能不是整数？？
        amp_factor = int(self.keyPara['le_Amp_Factor'])
        num_points_extends_from_center = int(self.keyPara['le_Extends_From_Centers'])
        num_points_extends_from_outside = int(self.keyPara['le_Extends_From_Outside'])
        centerData = []
        leftData = []
        rightData = []

        for i, interval in enumerate(intervals):
            mid = (interval[0] + interval[1]) // 2
            mid_logG = (left_means[i] + right_means[i]) / 2

            mid_left = mid + 400
            mid_right = mid + num_points_extends_from_center * 3+1
            centerData.append({
                'bias_volt': biasVolt[mid_left:mid_right],
                'volt': volt[mid_left:mid_right] / amp_factor * 1e6,
                'logG': logG[mid_left: mid_right],
                'current': current[mid_left: mid_right] * 0.001,
                'c2v': current[mid_left: mid_right] * 0.001 / (77.6e-6 * 10**mid_logG)
            })

            start_left = interval[0]
            start_right = interval[0] + num_points_extends_from_outside+1

            leftData.append({
                'bias_volt': biasVolt[start_left: start_right],
                'volt': volt[start_left: start_right] / amp_factor * 1e6,
                'logG': logG[start_left: start_right],
                'current': current[start_left: start_right] * 0.001,
                'c2v': current[start_left: start_right] * 0.001 / (77.6e-6 * 10**mid_logG)
            })

            end_left = interval[1]-num_points_extends_from_outside*7-330
            end_right = interval[1]-num_points_extends_from_outside*4+200+1
            rightData.append({
                'bias_volt': biasVolt[end_left: end_right],
                'volt': volt[end_left: end_right] / amp_factor * 1e6,
                'logG': logG[end_left: end_right],
                'current': current[end_left: end_right] * 0.001,
                'c2v': current[end_left: end_right] * 0.001 / (77.6e-6 * 10**mid_logG)
            })
        return rightData, centerData, leftData

    def loadTDMSFile(self, filePath):
        """
        加载tdms文件（单个）
        :param file_path:tdms文件路径
        :return: (偏压，电压，电流，电导)
        """
        biasVolt, volt, current, logG = None, None, None, None
        with TdmsFile.open(filePath) as tdmsFile:
            group = tdmsFile.groups()[0]
            channels = group.channels()
            for channel in channels:
                name = channel.name
                if ('Bias' in name):
                    biasVolt = channel[:]
                elif 'AI1' in name:
                    volt = channel[:]
                elif 'Current' in name:
                    current = channel[:]
                elif 'Log' in name:
                    logG = channel[:]
        return biasVolt, volt, current, logG
    
    def get_intervals(self, biasVolt):
        bias_lower = self.keyPara['le_Bias_Lower']
        bias_upper = self.keyPara['le_Bias_Upper']
        end_condition = ((biasVolt > bias_upper) | (biasVolt < bias_lower)) & (np.roll(biasVolt, 1) < bias_upper) & (np.roll(biasVolt, 1) > bias_lower)
        bias_end = np.where(end_condition)[0]
        start_condition = ((biasVolt > bias_lower) & (biasVolt < bias_upper) & ((np.roll(biasVolt, 1) > bias_upper) | (np.roll(biasVolt, 1) < bias_lower)))
        bias_start = np.where(start_condition)[0]
        bias_intervals = []
        for start_idx in bias_start:
            for end_idx in bias_end:
                if end_idx > start_idx:
                    bias_intervals.append((start_idx, end_idx))
                    break
        return bias_intervals

    def analysis(self, volt):
        fs = int(self.keyPara['le_Fs'])
        thres = self.keyPara['le_Thres']
        p_thres = self.keyPara['le_P_Thres']
        thres_1 = self.keyPara['le_Thres_1']
        prop = int(self.keyPara['le_Prop'])
        t = int(self.keyPara['le_T'])
        
        output = volt
        fyt = fft(volt, len(volt))
        f = np.arange(len(volt)) * (fs / len(volt))
        fyt_sq = fyt**2
    
        length = len(fyt_sq)
        kl = np.sum(fyt_sq[:int(length*thres)])
        kr = np.sum(fyt_sq[int(length*(1-thres))-1:])
        p = (kl + kr) / np.sum(fyt_sq)
        
        if p > p_thres:
            fyt[:int(length*thres_1)] = fyt[:int(length*thres_1)] / prop
            fyt[int(length*(1-thres_1))-1:] = fyt[int(length*(1-thres_1))-1:] / prop

            x = ifft(fyt)
            output = np.real(x)
            output = output[t-1:-t]
        return output

def filter_by_len(bias_intervals, POINTS_LIMIT, POINT_NUM):
    # 两个偏压为0的区间，是通过软接触测量电导，悬停的点数必须大于POINTS_LIMIT
    res = []
    length = len(bias_intervals)
    for i in range(length):
        if i == 0:
            if bias_intervals[0][0] - 1 >= POINTS_LIMIT:
                res.append(bias_intervals[0])
        elif i == length - 1:
            if bias_intervals[i][0] - bias_intervals[i-1][1] >= POINTS_LIMIT and POINT_NUM - bias_intervals[i][1] >= POINTS_LIMIT:
                res.append(bias_intervals[i])
        else:
            if bias_intervals[i][0] - bias_intervals[i - 1][1] >= POINTS_LIMIT and bias_intervals[i + 1][0] - bias_intervals[i][1] >= POINTS_LIMIT:
                res.append(bias_intervals[i])
    return res

def filter_by_zero(intervals, logG, POINTS_LIMIT, NUM_OVER_ZERO=10):
    # 是否出现电导大于0的情况
    res = []
    for interval in intervals:
        is_over_zero = logG[max(1, interval[0]-POINTS_LIMIT):interval[0]+1] > 0
        if sum(is_over_zero) <= NUM_OVER_ZERO:
            res.append(interval)
    return  res

def filter_by_logG(intervals, biasVolt,logG, range_logG=(-2.9, -1.9), hover_limit=200, HOVER_VOLTAGE=0.15):
    res_intevals = []
    left_intervals = []
    right_intervals = []
    left_means = []
    right_means = []
    m = len(logG)
    # 必须悬住
    for interval in intervals:
        start, end = interval[0], interval[1]
        hover_start = start - hover_limit
        hover_end = end + hover_limit
        if biasVolt[hover_start] > HOVER_VOLTAGE and biasVolt[hover_end-1] > HOVER_VOLTAGE: # 满足悬停条件
            logG_left = np.mean(logG[hover_start: start])
            logG_right = np.mean(logG[end: hover_end])
            # 必须在悬停范围内
            if (range_logG[0] <logG_left< range_logG[1]) and (range_logG[0] < logG_right < range_logG[1]):
                res_intevals.append(interval)
                left_intervals.append((hover_start, start))
                right_intervals.append((end, hover_end))
                left_means.append(logG_left)
                right_means.append(logG_right)
    return res_intevals, left_intervals, right_intervals, left_means, right_means

def volt_filter(data, slope_limit = 200, abs_mean_limit=100):
    n = len(data)
    pickedCell = []
    
    n_point_check = 100
    for item in data:
        v = item['volt']
        mean_volt = np.mean(v)

        while n_point_check >= len(v) / 2:
            n_point_check //= 2
        
        left_mean = np.mean(v[:n_point_check])
        right_mean = np.mean(v[-n_point_check-1:])
        center = len(v) // 2
        center_mean = np.mean(v[center-n_point_check//2: center+n_point_check//2])

        if np.abs(mean_volt) <= abs_mean_limit and \
            (np.abs(right_mean-left_mean) <= slope_limit \
                or np.abs(center_mean - left_mean) <= slope_limit):
            pickedCell.append(item)
        # else:
        #     dropedCell.append(item)
    return pickedCell

def gaussian(x, amp, cen, wid):
    return (amp / (np.sqrt(2 * np.pi) * wid)) * np.exp(-(x - cen)**2 / (2*wid**2))

# def gaussian(x, a, b, c):
#     return a * np.exp(-(x - b)**2 / (2 * c**2))

def fit(data, bins):
    # 高斯拟合
    vec = np.concatenate([item['volt'] for item in data])
    y, bin_edges = np.histogram(vec, bins=bins)
    x = (bin_edges[:-1] + bin_edges[1:]) / 2
    init_amp = y.max()
    init_mean = x[y.argmax()]
    init_wid = (bin_edges[1] - bin_edges[0]) * 2.35482
    paras, _ = curve_fit(gaussian, x, y, p0=[init_amp, init_mean, init_wid])
    return paras