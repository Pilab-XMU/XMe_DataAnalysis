import time
from math import pi
from nptdms import TdmsFile
import numpy as np

from EGaInAnalysisConst import BASEDIR
from PyQt5.QtCore import QObject, pyqtSignal
from gangLogger.myLog import MyLog
from scipy.optimize import curve_fit

class EGaInAnalysis(QObject):
    logger = MyLog("EGaInAnalysis", BASEDIR)
    runEnd = pyqtSignal()
    error = pyqtSignal(str)
    plotJVCurve = pyqtSignal()
    plotIVCurve = pyqtSignal()
    plotErrorbar = pyqtSignal()
    beginCVCount = pyqtSignal()
    plotCVCount = pyqtSignal()
    haveError = False
    def __init__(self, keyPara):
        super().__init__()
        self.keyPara = keyPara
        self.datasets = None
        
    
    def run(self):
        fileList = self.keyPara["FILE_PATHS"]
        bias, current, J, bias_lim = self.dataRead(fileList)
        self.bias_lim = bias_lim
        bias = np.concatenate(bias)
        current = np.concatenate(current)
        J = np.concatenate(J)
        if (self.keyPara["le_VolLim"] > np.max(np.abs(bias_lim))- 0.001):
            self.haveError = True
            self.error.emit("Voltage Limit is too large.")
            return
        anchor_p, anchor_m, current_width, half_width = self.zeroSeek(bias)
        if ((len(anchor_p) == 0) and len(anchor_m) == 0):
            self.haveError = True
            self.error.emit("There is no valid data, please change another data file.")
            return
        # 绘制J-V图
        self.half_width = half_width
        self.zeros_p = anchor_p
        self.zeros_m = anchor_m
        self.J = J
        self.bias = bias
        self.plotJVCurve.emit()
        # 绘制I-V图
        self.curr = current
        self.plotIVCurve.emit()
        try:
            J_p, J_m, avg_p, avg_m = self.cut(bias, J, bias_lim, self.keyPara["le_Interval"])
            logJp_mean = np.mean(np.log10(np.abs(J_p)), axis=0)
            logJm_mean = np.mean(np.log10(np.abs(J_m)), axis=0)
            # Jp_std = np.std(J_p, axis=0)
            logJp_std = np.std(np.log10(np.abs(J_p)), axis=0, ddof=1)
            # Jm_std = np.std(J_m, axis=0)
            logJn_std = np.std(np.log10(np.abs(J_m)), axis=0, ddof=1)
            div_num = (bias_lim[1] - bias_lim[0])/ self.keyPara["le_Interval"] + 1
            divp = np.ceil(len(avg_p)/div_num).astype(int)
            divm = np.ceil(len(avg_m)/div_num).astype(int)

            self.errX_p = avg_p[::divp]
            self.errY_p = logJp_mean[::divp]
            self.errStd_p = logJp_std[::divp]

            self.errX_m = avg_m[::divm]
            self.errY_m = logJm_mean[::divm]
            self.errStd_m = logJn_std[::divm]
            self.plotErrorbar.emit()
        except Exception as e:
            self.haveError = True
            self.logger.error(f"[THREAD ERROR]CUT ERROR:{e}\n")
            self.error.emit("CVcount Error!")
            return
        time.sleep(2)
        # 绘制高斯拟合cvcount ???
        clogJ = self.calculateClogJ(anchor_p, anchor_m, div_num, J)
        if len(clogJ) == 0:
            self.haveError = True
            self.error.emit("Error!")
            return
        self.clogJ = clogJ
        self.beginCVCount.emit()
        def gaussian(x, amp, cen, wid):
            return (amp / (np.sqrt(2 * np.pi) * wid)) * np.exp(-(x - cen) ** 2 / (2 * wid ** 2))
        rows = clogJ.shape[0]
        if (rows % 2 == 1):
            zeros = rows - 1
        else:
            zeros = rows
        bins = np.arange(-9, 2.1, 0.1)

        yy_list = []
        self.y_list = []
        x = (bins[1:] + bins[:-1]) / 2
        self.cvcount_idx = []
        for col in range(clogJ.shape[1]):# 每个箱子
            # 对每一列做直方图，
            y, edges = np.histogram(np.concatenate([clogJ[:, col], np.zeros(zeros)]), bins=bins)
            try:
                para = curve_fit(gaussian, x, y, p0=[2, -6, 15])
                # count += 1
            except Exception as e:
                self.logger.error(f"[THREAD ERROR]gaussian fit error:{col},{e}\n")
                continue
            self.cvcount_idx.append(col)
            self.y_list.append(y)
            yy = gaussian(x, para[0][0], para[0][1], para[0][2])
            yy_list.append(yy)
        self.cvcount_x = x
        self.cvcount_y = yy_list
        self.plotCVCount.emit()
        self.runEnd.emit()
        return

    
    def dataRead(self, fileList):
        bias, curr, J = [], [], []
        d = self.keyPara['le_Diameter'] * self.keyPara['le_Scale'] # 真实直径(mm)
        area = pi * (d / 2)**2*1e-2 # 面积(cm^2)
        for f in fileList:
            vol_bias, vol_sample = self.loadTDMSFile(f)
            vol_bias, current = self.voltage2current(vol_bias, vol_sample)
            # 电流密度
            j = current / area
            bias.append(vol_bias)
            curr.append(current)
            J.append(j)
        # 扫描电压上下限
        bias_upper = round(np.max(bias[0]), 2)
        bias_lower = round(np.min(bias[0]), 2)
        return bias, curr, J, (bias_lower, bias_upper)

    def loadTDMSFile(self, path):
        """读取TDMS文件，返回偏压和采样电压
        Args:
            path (str): tdms文件路径
        Returns:
            tuple(bias voltage, sample voltage): 
        """
        with TdmsFile.open(path) as tdms_file:
            group = tdms_file.groups()[0]
            vol_bias = group.channels()[0][:]
            vol_sample = group.channels()[1][:]
        return vol_bias, vol_sample
        
    def voltage2current(self, voltage_bias, voltage_sample):
        """计算电流

        Args:
            voltage_bias (numpy.array): 偏压
            voltage_sample (numpy.array): 采样电压
        Returns:
            tuple(bias, current)
        """
        par = self.keyPara
        # 根据偏压去掉重复值
        diff = np.diff(voltage_bias)
        idx = np.concatenate(([0], np.where(diff != 0)[0] + 1))
        bias = voltage_bias[idx]
        samp = voltage_sample[idx]

        # 截取完整序列，即从第一个极大值点到最后一个极大值点之间的部分
        diff = np.diff(bias)
        idx = np.where((diff[:-1] > 0) & (diff[1:] < 0))[0] + 1 # 局部极大值索引
        start_idx, end_idx = idx[0], idx[-1]
        

        bia = np.zeros(end_idx - start_idx + 3)
        sam = np.zeros(end_idx - start_idx + 3)
        bia[0] = bias[start_idx] - (bias[start_idx + 1] - bias[start_idx])
        sam[0] = samp[start_idx] - (samp[start_idx + 1] - samp[start_idx])
        bia[1:-1] = bias[start_idx: end_idx + 1]
        sam[1:-1] = samp[start_idx: end_idx + 1]
        bia[-1] = bias[end_idx] + (bias[end_idx] - bias[end_idx-1])
        sam[-1] = samp[end_idx] + (samp[end_idx] - samp[end_idx-1])
        
        if self.keyPara["PARA_ID"] == 0:
            current = self.v2c_Para9(sam)
        elif self.keyPara["PARA_ID"] == 1:
            current = self.v2c_Para5(sam)
        return bia, current
    def v2c_Para9(self, samp_v):
        para = self.keyPara["PARAS_9"]
        v = samp_v - para["le_Fit9_Offset"]
        current = np.where(samp_v < 0.003, 
                           v*para["le_Fit9_cP"]+np.exp(v*para["le_Fit9_aP"]+para["le_Fit9_bP"])+para["le_Fit9_dP"], \
                           v*para["le_Fit9_cM"]+np.exp(v*para["le_Fit9_aM"]+para["le_Fit9_bM"])+para["le_Fit9_dM"])
        return current
    def v2c_Para5(self, samp_v):
        para = self.keyPara["PARAS_5"]
        v = samp_v - para["le_Fit5_Offset"]
        aP = para["le_Fit5_aP"]
        bP = para["le_Fit5_bP"]
        aM = para["le_Fit5_aM"]
        bM = para["le_Fit5_bM"]
        current = np.where(v < 0, np.power(10., aP * v + bP), np.power(10., aM * v + bM))
        return current
    def zeroSeek(self, bias):
        """寻找扫描电压中的零点
        Args:
            bia (1D numpy array): 扫描电压
        Returns:
            anchor_p (1D numpy array): 正向(1 -> -1)扫描电压零点
            anchor_n (1D numpy array): 负向(-1 -> 1)扫描电压零点
            current_data_witdh(int): 数据宽度
            half_width(int): 半宽
        """
        # 这里假设了一定会有偏压为0的时刻
        diff = np.diff(np.sign(bias))
        # 从正变为负时，正数的索引
        pos_zero_list = np.where(diff < 0)[0]
        # 从负变为正时，负数的索引
        neg_zero_list = np.where(diff > 0)[0]
        
        if len(neg_zero_list) == 0 or len(pos_zero_list) == 0:
            self.haveError = True
            self.error.emit("There is no valid data, please change another data file.")
            return [], [], 0, 0
        
        current_data_width = abs(neg_zero_list[0] - pos_zero_list[0])
        half_width = current_data_width // 2

        # print(f"half_width= {half_width}")

        pos_zero_list = pos_zero_list[(pos_zero_list >= half_width) & (pos_zero_list < len(bias)-half_width)]
        neg_zero_list = neg_zero_list[(neg_zero_list >= half_width) & (neg_zero_list < len(bias)-half_width)]

        pos_zero_list = pos_zero_list[np.diff(pos_zero_list, prepend=-1) != 1]

        # 修正一下
        neg_zero_list_1 = []
        for i in range(len(neg_zero_list)-1):
            if neg_zero_list[i+1]-neg_zero_list[i] == 1:
                continue
            else:
                neg_zero_list_1.append(neg_zero_list[i])
        if neg_zero_list[-1] - neg_zero_list_1[-1] != 1:
            neg_zero_list_1.append(neg_zero_list[-1])
        neg_zero_list = np.array(neg_zero_list_1)

        # 修正一下half_width
        if (pos_zero_list[0] < neg_zero_list[0]):
            neg_hw = abs(pos_zero_list[0] - neg_zero_list[0])// 2
            pos_hw = abs(pos_zero_list[1] - neg_zero_list[0]) // 2
        else:
            neg_hw = abs(pos_zero_list[0] - neg_zero_list[1]) // 2
            pos_hw = abs(pos_zero_list[0] - neg_zero_list[0]) // 2

        self.pos_hw = pos_hw
        self.neg_hw = neg_hw

        # 找到零点前后更靠近零点的索引
        # 从正到负
        anchor_p = []
        for i in pos_zero_list:
            if abs(bias[i]) < abs(bias[i+1]):
                anchor_p.append(i)
            else:
                anchor_p.append(i+1)
        # 从负到正
        anchor_n = []
        for i in neg_zero_list:
            if abs(bias[i]) < abs(bias[i+1]):
                anchor_n.append(i)
            else:
                anchor_n.append(i+1)
        anchor_n = np.array(anchor_n)
        anchor_p = np.array(anchor_p)
        return anchor_p, anchor_n, current_data_width, half_width
    
    def cut(self, bias,J, bias_lim, interval):
        bias_diff = np.diff(bias)
        tip = np.where(((bias_diff[:-1] > 0) & (bias_diff[1:] < 0)) |  ((bias_diff[:-1] < 0) & (bias_diff[1:] > 0)))[0] + 1

        #提取正向扫描(1到-1)和反向扫描(-1到1)起始点
        scan_pos = []
        scan_neg = []
        for i in range(len(tip)-1):
            start = tip[i]
            end = tip[i+1]
            if (bias[start] < bias[end]):
                scan_neg.append((start, end))
            elif (bias[start] > bias[end]):
                scan_pos.append((start, end))
        # 平均电压(可以理解为将电压划分为若干bins后，每个bins的中点)
        assert(bias_lim[0] < bias_lim[1])
        avg_p = np.arange(bias_lim[1], bias_lim[0] - interval, -interval)
        avg_n = np.arange(bias_lim[0], bias_lim[1] + interval,  interval)

        Jp = np.zeros((len(scan_pos), len(avg_p)))
        Jm = np.zeros((len(scan_neg), len(avg_n)))

        # 根据平均电压，找对应的电流密度J
        for i , (start, end) in enumerate(scan_pos):
            Jp[i][0] = J[start-1]
            k = 1
            for j in range(start+1, end+1):
                if (bias[j] >= avg_p[k] and bias[j+1] <= avg_p[k]):
                    Jp[i][k] = J[j]
                    k += 1
                if k >= len(avg_p):
                    break;
            Jp[i][-1] = J[end]
        for i , (start, end) in enumerate(scan_neg):
            Jm[i][0] = J[start-1]
            k = 1
            for j in range(start+1, end+1):
                if (bias[j] <= avg_n[k] and bias[j+1] >= avg_n[k]):
                    Jm[i][k] = J[j]
                    k += 1
                if k >= len(avg_n):
                    break;
            Jm[i][-1] = J[end]
        # 删除含有0的行
        Jp = Jp[np.where(np.all(Jp != 0, axis=1))]
        Jm = Jm[np.where(np.all(Jm != 0, axis=1))]
        return Jp, Jm, avg_p, avg_n
    
    def calculateClogJ(self, anchor_p, anchor_m, div_num, J):
        try:
            clogJ = []
            delta = np.abs(anchor_p[0] - anchor_m[0]) # 周期长度
            half_delta = round(delta / 2) # 半个周期
            step = round(delta / div_num) # 步长 与interval一样
            l = min(len(anchor_m), len(anchor_p))
            logJ = np.log10(np.abs(J))
            for i in range(l):
                startPoint = anchor_p[i] - half_delta
                idx = np.arange(startPoint, startPoint + step * div_num, step, dtype=np.int32)
                clogJ.append(logJ[idx])
            clogJ = np.array(clogJ)
            return clogJ
        except Exception as e:
            self.logger.error(f"[THREAD ERROR]CALCULATE CLOGJ ERROR:{e}")
            return []
