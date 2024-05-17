# -*- coding: utf-8 -*-
# @Time   : 2023/3/09 18:23
# @Author : shangchi
# @File   : myEGaInAnalysisModule.py
from multiprocessing import freeze_support
import configparser
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import pyqtSlot, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QVBoxLayout, QFileDialog, QLineEdit, QInputDialog


from gangUtils.generalUtils import GeneralUtils as GeneralUtils
from gangLogger.myLog import MyLog
from ui_QWEGaInAnalysisModule import *
from EGaInAnalysisConst import *
from myFigure import *
from EGaInAnalysis import EGaInAnalysis

class QmyEGaInAnalysisModule(QMainWindow):
    logger = MyLog("QmyEGaInAnalysisModule", BASEDIR)

    def __init__(self, parent=None):
        super(QmyEGaInAnalysisModule, self).__init__(parent)
        self.ui = Ui_QWEGaInAnalysisModule()
        self.ui.setupUi(self)
        self.init_set()
        self.checkConfig()
        self.init_widget()

    def init_set(self):
        """成员变量的初始化
        """
        self.keyPara = {}
        self.keyPara["SAVE_DATA_STATUE"] = False  # 数据保存标志位，初始化false，另外在点击run之后也应该设置false，绘图完成设置true
        self.lastOpenPath = BASEDIR # 打开文件夹的初始地址
        self.keyPara['PARA_ID'] = 0
    
    def init_widget(self):
        self.add_textBrowser_str("*" * 18 + "Welcome" + "*" * 18, showtime=False)
        logMsg = "Please load the data file first."
        self.add_textBrowser_str(logMsg)
        self.add_statusBar_str(logMsg)

        self.ui.actRun.setEnabled(False)
        self.ui.actSaveData.setEnabled(False)
        
        self.initSaveDir()
        self.initFigure()
        self.logger.debug("The initial configuration is complete.")

    def initFigure(self):
        self._errorbarLayout  = QVBoxLayout(self)
        self._jvLayout = QVBoxLayout(self)
        self._ivLayout = QVBoxLayout(self)
        self._countLayout = QVBoxLayout(self)

        self._errorbarCanvas = MyFigureCanvas()
        self._jvCanvas = MyFigureCanvas()
        self._ivCanvas = MyFigureCanvas()
        self._countCanvas = MyFigureCanvas()

        self._errorbarToolBar = MyNavigationToolbar(self._errorbarCanvas, self._errorbarCanvas.mainFrame)
        self._jvToolBar = MyNavigationToolbar(self._jvCanvas, self._jvCanvas.mainFrame)
        self._ivToolBar = MyNavigationToolbar(self._ivCanvas, self._ivCanvas.mainFrame)
        self._countToolBar = MyNavigationToolbar(self._countCanvas, self._countCanvas.mainFrame)

        self._errorbarLayout.addWidget(self._errorbarCanvas)
        self._errorbarLayout.addWidget(self._errorbarToolBar)
        self._jvLayout.addWidget(self._jvCanvas)
        self._jvLayout.addWidget(self._jvToolBar)
        self._ivLayout.addWidget(self._ivCanvas)
        self._ivLayout.addWidget(self._ivToolBar)
        self._countLayout.addWidget(self._countCanvas)
        self._countLayout.addWidget(self._countToolBar)

        self.ui.grp_stderr_fig.setLayout(self._errorbarLayout)
        self.ui.grp_jv_fig.setLayout(self._jvLayout)
        self.ui.grp_iv_fig.setLayout(self._ivLayout)
        self.ui.grp_cv_count.setLayout(self._countLayout)

    def initSaveDir(self):
        """
        初始化保存数据路径是桌面路径，后续加载完数据后应当修改为数据的文件路径！！
        :return:
        """
        deskPath = GeneralUtils.getDesktopPath()
        self.ui.le_Data_Save_Dir.setText(deskPath)
#===============控件触发函数=====================   
    @pyqtSlot()
    def on_actOpenFiles_triggered(self):
        """
        文件加载
        :return:
        """
        try:
            dlgTitle = "Select multiple files"  # 对话框标题
            filt = "TDMS Files(*.tdms)"  # 文件过滤器
            loadStatue = False
            while not loadStatue:
                fileList, filtUsed = QFileDialog.getOpenFileNames(self, dlgTitle, self.lastOpenPath, filt)

                loadStatue = len(fileList) > 0
                if not loadStatue:
                    result = QMessageBox.warning(self, "Warning", "Please select at least one file!",
                                                 QMessageBox.Ok | QMessageBox.Cancel,
                                                 QMessageBox.Ok)
                    if result == QMessageBox.Cancel:
                        break
                else:
                    # file load success!!!!
                    self.lastOpenPath = os.path.dirname(fileList[0])    
                    self.keyPara['FILE_PATHS'] = fileList
                    self.add_textBrowser_str(f"{len(fileList)} files have been loaded:")
                    self.add_textBrowser_list(fileList)
                    self.add_textBrowser_str("*" * 45, showtime=False)
                    self.ui.le_Data_Save_Dir.setText(self.lastOpenPath)
                    # 加载文件成功之后，应当对运行按钮进行释放
                    self.ui.actRun.setEnabled(True)
                    self.logger.debug("File loading completed.")
        except Exception as e:
            errMsg = f"DATA FILE LOAD ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
    
    @pyqtSlot()
    def on_actRun_triggered(self):
        """
        run~!!!!!!
        :return:
        """
        try:
            self.ui.actRun.setEnabled(False)  # 这里需要注意的是点击一次run 控件之后，应当设置未为不可选，
            self.ui.actSaveData.setEnabled(False)
            self.keyPara["SAVE_DATA_STATUE"] = False

            keyPara = self.getPanelPara()
            if keyPara is None:
                return
            else:
                self.keyPara.update(keyPara)
                self.logger.debug(f"Parameters are updated before running. Parameter list:{self.keyPara}")
                self.dataThread = QThread()
                self.dataAnalysis = EGaInAnalysis(self.keyPara)
                # 正常运行结束
                self.dataAnalysis.runEnd.connect(lambda: self.stopThread(self.dataThread))
                # 数据处理出错
                self.dataAnalysis.error.connect(self.threadError)
                #绘图信号
                #
                self.dataAnalysis.plotJVCurve.connect(self.drawJVCurve)
                self.dataAnalysis.plotIVCurve.connect(self.drawIVCurve)
                self.dataAnalysis.plotErrorbar.connect(self.drawErrorbar)
                #self.dataAnalysis.beginCVCount.connect(self.cvCountInit)
                #self.dataAnalysis.plotCVCount.connect(self.updateCVCount)


                self.dataAnalysis.moveToThread(self.dataThread)
                self.dataThread.started.connect(self.dataAnalysis.run)
                # self.dataThread.finished.connect(self.dataThread.deleteLater)
                self.dataThread.finished.connect(lambda: print("thread finish"))

                logMsg = "Data calculation..."
                self.addLogMsgWithBar(logMsg)

                self.dataThread.start()
                self.logger.debug(
                    f"Start the data calculation thread--{self.dataThread.currentThread()},Now state:{self.dataThread.isRunning()}")
        except Exception as e:
            errMsg = f"RUN ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_actQuit_triggered(self):
        """
        程序退出
        :return:
        """
        self.close()

    def closeEvent(self, event):
        """
        重写窗口关闭函数，关闭前保存面板参数
        :param event: 无
        :return: 无
        """
        dlg_title = "Warning"
        str_info = "Sure to quit??"
        reply = QMessageBox.question(self, dlg_title, str_info,
                                     QMessageBox.Yes | QMessageBox.Cancel,
                                     QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            self.saveConfigPara(os.path.join(BASEDIR, 'config.ini'))
            time.sleep(0.1)
            self.logger.debug("Program exits")
            event.accept()
        else:
            event.ignore()

    @pyqtSlot()
    def on_btn_Select_SaveDir_clicked(self):
        """
        设置处理结果的保存目录
        :return:
        """
        desktopPath = GeneralUtils.getDesktopPath()
        dlgTitle = "Select a Save Directory"
        selectDir = QFileDialog.getExistingDirectory(self, dlgTitle, desktopPath, QFileDialog.ShowDirsOnly)
        if selectDir != "":
            self.ui.le_Data_Save_Dir.setText(selectDir)
            self.keyPara[self.ui.le_Data_Save_Dir.objectName()] = selectDir
    @pyqtSlot()
    def on_actSaveData_triggered(self):
        try:
            preCheck = self.savePreCheck()
            if preCheck:
                # finished check
                dataSavePath = self.keyPara["Data_Save_Path"]

                # fig save
                self.saveFig()
                # end fig save

                # data save
                self.saveData()
                # end data save

                # config save
                config_path = os.path.join(dataSavePath, 'config.ini')
                self.saveConfigPara(config_path)

                logMsg = f"All data has been saved. Path:{dataSavePath}"
                self.addLogMsgWithBar(logMsg)
                QMessageBox.information(self, "Info", logMsg)
        except Exception as e:
            errMsg = f"DATA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
#================绘图========================
    def drawJVCurve(self):
        fig = self._jvCanvas.fig
        fig.clf()
        ax = fig.add_subplot()

        zeros_p, zeros_m = self.dataAnalysis.zeros_p, self.dataAnalysis.zeros_m
        bias = self.dataAnalysis.bias
        bias_lim = self.dataAnalysis.bias_lim
        J = np.abs(self.dataAnalysis.J)
        half_width = self.dataAnalysis.half_width

        for i in range(1, len(zeros_p)-1):
            start = zeros_p[i] - self.dataAnalysis.pos_hw
            end = zeros_p[i] + self.dataAnalysis.neg_hw
            ax.semilogy(bias[start:end], J[start:end], c='r', linewidth=.5)
        for i in range(1, len(zeros_m)-1):
            start = zeros_m[i] - self.dataAnalysis.neg_hw
            end = zeros_m[i] + self.dataAnalysis.pos_hw
            ax.semilogy(bias[start:end], J[start:end], c='b', linewidth=.5)
        ax.set_xlim(bias_lim[0]-0.1, bias_lim[1]+0.1)
        ax.set_xlabel("bias/V")
        ax.set_ylabel(r"J/(A/cm$^{2}$)")

        fig.tight_layout()
        fig.canvas.draw()
        fig.canvas.flush_events()
        
    def drawIVCurve(self):
        fig = self._ivCanvas.fig
        fig.clf()
        ax = fig.add_subplot()

        bias = self.dataAnalysis.bias
        curr = self.dataAnalysis.curr
        bias_lim = self.dataAnalysis.bias_lim
        ax.semilogy(bias, curr, linewidth=.5)
        ax.axis([bias_lim[0], bias_lim[1], 1e-15, 1e-2])
        ax.set_xlabel("Bias/V")
        ax.set_ylabel("Current/A")

        fig.tight_layout()
        fig.canvas.draw()
        fig.canvas.flush_events()

    def drawErrorbar(self):
        fig = self._errorbarCanvas.fig
        fig.clf()
        ax = fig.add_subplot()
        errX_p, errY_p, errStd_p = self.dataAnalysis.errX_p, self.dataAnalysis.errY_p, self.dataAnalysis.errStd_p
        errX_m, errY_m, errStd_m = self.dataAnalysis.errX_m, self.dataAnalysis.errY_m, self.dataAnalysis.errStd_m
        bias_lim = self.dataAnalysis.bias_lim

        ax.errorbar(errX_p, errY_p, yerr = errStd_p, fmt='rx', capsize=3)
        ax.errorbar(errX_m, errY_m, yerr = errStd_m, fmt='bx', capsize=3)
        ax.axis([bias_lim[0]-0.1, bias_lim[1]+0.1, errY_m[0]-7, errY_m[0]+2])
        ax.set_xlabel("Bias(V)")
        ax.set_ylabel(r'logJ|(A/cm$^{2}$)')

        fig.tight_layout()
        fig.canvas.draw()
        fig.canvas.flush_events()

        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.keyPara["SAVE_DATA_STATUE"] = True
        self.ui.actSaveData.setEnabled(True)
        self.ui.actRun.setEnabled(True)
    
    def cvCountInit(self):
        fig = self._countCanvas.fig
        fig.clf()
        ax = fig.add_subplot()
        ax.set_xticks(np.arange(-9, 3, 1))
        ax.set_xlabel("logJ")
        ax.set_ylabel("Counts")
        fig.tight_layout()
        fig.canvas.draw()
        fig.canvas.flush_events()
    
    def updateCVCount(self):
        print(f"update cvcount")
        clogJ = self.dataAnalysis.clogJ
        fig = self._countCanvas.fig
        ax =  fig.axes[0]
        bins = np.arange(-9, 2.1, 0.1)
        rows = clogJ.shape[0]
        if (rows % 2 == 1):
            zeros = rows - 1
        else:
            zeros = rows
        
        # ax.hist(np.concatenate([clogJ[:, id], np.zeros(zeros)]), bins=bins)
        # ax.plot(self.dataAnalysis.cvcount_x, self.dataAnalysis.cvcount_y, c='r')
        # fig.canvas.draw()
        # if id % 10 == 0:
        #     fig.canvas.flush_events()
        # if id == clogJ.shape[1]:
        #     fig.canvas.flush_events()
        count = 0
        for i, col in enumerate(self.dataAnalysis.cvcount_idx):
            ax.hist(np.concatenate([clogJ[:, col], np.zeros(zeros)]), bins=bins)
            ax.plot(self.dataAnalysis.cvcount_x, self.dataAnalysis.cvcount_y[i], c= 'r')
            count += 1
            if (count % 10 == 0):
                fig.canvas.draw()
                fig.canvas.flush_events()
        fig.canvas.draw()
        fig.canvas.flush_events()

        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.keyPara["SAVE_DATA_STATUE"] = True
        self.ui.actSaveData.setEnabled(True)
        self.ui.actRun.setEnabled(True)
#===============辅助函数=====================
    def savePreCheck(self):
        """
        数据保存之前的检查
        :return:
        """
        if not self.keyPara["SAVE_DATA_STATUE"]:
            errMsg = "The data cannot be saved until the data processing is complete!"
            self.addErrorMsgWithBox(errMsg)
            return False

        dlgTitle = "Folder name Settings"
        txtLabel = "Please enter the name of the folder to save"
        defaultName = "EGaIn"
        echoMode = QLineEdit.Normal
        saveDataDir = self.ui.le_Data_Save_Dir.text()
        flag = False
        while not flag:
            text, OK = QInputDialog.getText(self, dlgTitle, txtLabel, echoMode, defaultName)
            if OK:
                savePath = os.path.join(saveDataDir, text)
                IS_EXIST = os.path.exists(savePath)
                if IS_EXIST:
                    errMsg = "The file name already exists or is invalid,Please re-enter"
                    self.addErrorMsgWithBox(errMsg)
                    continue
                else:
                    flag = not flag
                    self.keyPara["Data_Save_Path"] = savePath
                    GeneralUtils.creatFolder(saveDataDir, text)  # 存储路径直接在这里创建
            else:
                logMsg = "Unsave data"
                self.addLogMsgWithBar(logMsg)
                return False
        return True
    
    def saveFig(self):
        """
        图片保存
        :return:
        """
        save_path = self.keyPara["Data_Save_Path"]
        img_dir = os.path.join(save_path, "Images")
        GeneralUtils.creatFolder(save_path, "Images")
        errorbar_path = os.path.join(img_dir, "errorbar_fig.png")
        jv_path = os.path.join(img_dir, "jv_fig.png")
        iv_path = os.path.join(img_dir, "iv_fig.png")
        hist = os.path.join(img_dir, "cv_counts.png")

        self._errorbarCanvas.fig.savefig(errorbar_path, dpi=300, bbox_inches='tight')
        self._jvCanvas.fig.savefig(jv_path, dpi=300, bbox_inches='tight')
        self._ivCanvas.fig.savefig(iv_path, dpi=300, bbox_inches='tight')
        #self._countCanvas.fig.savefig(hist, dpi=100, bbox_inches='tight')

    def saveData(self):
        """
        数据保存
        """
        save_path = self.keyPara["Data_Save_Path"]
        data_dir = os.path.join(save_path, "Data")
        GeneralUtils.creatFolder(save_path, "Data")
        errorbar_path = os.path.join(data_dir, "errorbar.csv")
        errX_p, errY_p, errStd_p = self.dataAnalysis.errX_p.reshape(-1, 1), self.dataAnalysis.errY_p.reshape(-1, 1), \
            self.dataAnalysis.errStd_p.reshape(-1, 1)
        errX_m, errY_m, errStd_m = self.dataAnalysis.errX_m.reshape(-1, 1), self.dataAnalysis.errY_m.reshape(-1, 1), \
            self.dataAnalysis.errStd_m.reshape(-1, 1)
        err_data = np.hstack((errX_p, errY_p, errStd_p, errX_m, errY_m, errStd_m))
        np.savetxt(errorbar_path, err_data, delimiter=',', header='errX_p(1 to -1),errY_p,std_p,errX_m(-1 to 1),errY_m,std_m',comments="")
        
        zeros_p, zeros_m = self.dataAnalysis.zeros_p, self.dataAnalysis.zeros_m
        bias = self.dataAnalysis.bias
        J = np.abs(self.dataAnalysis.J)
        bias_lim = self.dataAnalysis.bias_lim
        x_p, y_p = [], []
        x_m, y_m = [], []
        N = np.min((len(zeros_m), len(zeros_p))) - 1
        for i in range(N):
            start = zeros_p[i] - self.dataAnalysis.pos_hw
            end = zeros_p[i] + self.dataAnalysis.neg_hw
            x_p.append(bias[start:end])
            y_p.append(J[start:end])
            start = zeros_m[i] - self.dataAnalysis.neg_hw
            end = zeros_m[i] + self.dataAnalysis.pos_hw
            x_m.append(bias[start:end])
            y_m.append(J[start:end])
        np.savez(os.path.join(data_dir, 'single.npz'),xp=x_p, yp=y_p, xm=x_m, ym=y_m)
            
        # 保存单条？
        # bias = self.dataAnalysis.bias
        # J = np.abs(self.dataAnalysis.J)
        # zeros_p, zeros_m = self.dataAnalysis.zeros_p, self.dataAnalysis.zeros_m
        # bias_lim = self.dataAnalysis.bias_lim

        # for i in range(1, len(zeros_p)-1):
        #     start = zeros_p[i] - self.dataAnalysis.pos_hw
        #     end = zeros_p[i] + self.dataAnalysis.neg_hw
        #     np.savetxt('./')
        #     ax.plot(bias[start:end], J[start:end], c='r', linewidth=.5)
        # for i in range(1, len(zeros_m)-1):
        #     start = zeros_m[i] - self.dataAnalysis.neg_hw
        #     end = zeros_m[i] + self.dataAnalysis.pos_hw
        #     ax.semilogy(bias[start:end], J[start:end], c='b', linewidth=.5)


    def saveConfigPara(self, config_path):
        """
        结束保存参数
        :return:
        """
        try:
            config = configparser.ConfigParser()
            config.optionxform = str  # 这一句相当的关键，因为config这个模块会把option自动的变为全小写，这个设置可以保持原样！
            section_name = "PANEL_PARA"
            config.add_section(section_name)

            leObjList = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.wdt_Paras_9, self.ui.wdt_Paras_5, self.ui.wdt_Paras_10]
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                leObjList.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in leObjList:
                config.set(section_name, obj.objectName(), obj.text())
            # ========这一部分需要手动添加=====
            obj_list_manual = [self.ui.le_Data_Save_Dir]
            for obj in obj_list_manual:
                config.set(section_name, obj.objectName(), obj.text())
            config.set(section_name, "PARA_ID", str(self.keyPara["PARA_ID"]))
            with open(config_path, mode="w", encoding="utf-8") as f:
                config.write(f)
            self.logger.debug("Parameters have been saved")
        except Exception as e:
            errMsg = f"PARA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def getPanelPara(self):
        """
        run之后, 需要进行面板的参数采集
        :return:
        """
        keyPara = {}
        try:
            keyPara["PARA_ID"] = self.ui.cmb_Fit.currentIndex()
            leObjList = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara]
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                leObjList.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in leObjList:
                keyPara[obj.objectName()] = float(obj.text())
            keyPara["PARAS_9"] = self.getDevicePara(self.ui.wdt_Paras_9)
            keyPara["PARAS_5"] = self.getDevicePara(self.ui.wdt_Paras_5)
            keyPara["PARAS_10"] = self.getDevicePara(self.ui.wdt_Paras_10)
        except Exception as e:
            errMsg = f"GTE PANEL PARA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            return None
        else:
            return keyPara
    def getDevicePara(self, widgetName):
        temp = {}
        obj_list = self.getSameWidget(widgetName, QLineEdit)
        for obj in obj_list:
            temp[obj.objectName()] = float(obj.text())
        return temp
    def getSameWidget(self, widgetName, activeXName):
        """
        获取某个 widget 中同类型的控件
        :param widgetName: widget名, 传入的是ui中的某个widget名
        :param activeXName: 控件类型，传入的是对象
        :return: 寻找到的对象集合(List)
        """
        return widgetName.findChildren(activeXName)

    def getLastPara(self):
        """
        加载程序同路径下保存好的历史参数并设置，
        """
        try:
            config = configparser.ConfigParser()
            configPath = os.path.join(BASEDIR, "config.ini")
            config.read(configPath, encoding='utf-8')
            section_name = "PANEL_PARA"

            le_obj_list = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.wdt_Paras_5, self.ui.wdt_Paras_9, self.ui.wdt_Paras_10]
            self.ui.cmb_Fit.setCurrentIndex(int(config.get(section_name, "PARA_ID")))
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in le_obj_list:
                obj.setText(config.get(section_name, obj.objectName()))
            obj_list_manual = [self.ui.le_Data_Save_Dir]
            for obj in obj_list_manual:
                obj.setText(config.get(section_name, obj.objectName()))
            logMsg = "History parameters have been loaded"
            self.addLogMsgWithBar(logMsg)
        except Exception as e:
            errMsg = f"GTE OLD PARA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def checkConfig(self):
        """
        检查参数
        :return:
        """
        configPath = os.path.join(BASEDIR, "config.ini")
        if os.path.exists(configPath):
            dlgTitle = "Info"
            strInfo = "Config file detected. Load it??"
            reply = QMessageBox.question(self, dlgTitle, strInfo,
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.getLastPara()

    def stopThread(self, thread):
        """
        线程停止
        :param thread: 需传入对应的进程
        :return: 无返回值
        """
        try:
            print(thread.isFinished())
            thread.quit()
            thread.wait()
        except Exception as e:
            errMsg = f"PRECESS EXIT ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
        self.logger.debug(f"Exit {thread.currentThread()} thread，Now state:{thread.isRunning()}")

    def threadError(self, msg):
        if (self.dataThread.isRunning):
            self.dataThread.quit()
            self.dataThread.wait()
        self.addErrorMsgWithBox(msg)
        self.ui.actRun.setEnabled(True)
                
#=============日志辅助函数=============================
    def addErrorMsgWithBox(self, errMsg):
        self.logger.error(errMsg)
        QMessageBox.warning(self, "Warning", errMsg)
        self.add_statusBar_str(errMsg)
        self.add_textBrowser_str(errMsg)

    def addErrorMsgNoBox(self, errMsg):
        self.logger.error(errMsg)
        self.add_statusBar_str(errMsg)
        self.add_textBrowser_str(errMsg)

    def addLogMsgWithBar(self, logMsg):
        self.logger.debug(logMsg)
        self.add_statusBar_str(logMsg)
        self.add_textBrowser_str(logMsg)

    def add_textBrowser_str(self, content_str, showtime=True):
        """
        在textBrowser中添加字符串
        :param content_str: 字符串
        :param showtime: 是否添加时间，默认true
        :return: 无返回值
        """
        try:
            if showtime:
                current_time = GeneralUtils.getCurrentTime()
                self.ui.tbw_Log.append("[" + current_time + "]  " + content_str)
            else:
                self.ui.tbw_Log.append(content_str)
        except Exception as e:
            errMsg = f"TEXT BROWSER ERROR:{e}"
            self.logger.error(errMsg)

    def add_textBrowser_list(self, content_list, showtime=True):
        """
        在textBrowser中添加list
        :param content_list: 字符串列表
        :param showtime: 是否添加时间
        :return: 无返回值
        """
        try:
            if showtime:
                current_time = GeneralUtils.getCurrentTime()
                self.ui.tbw_Log.append(current_time)
                for content in content_list:
                    content = content.split("/")[-1]
                    self.ui.tbw_Log.append("-- " + content)
            else:
                for content in content_list:
                    content = content.split("/")[-1]
                    self.ui.tbw_Log.append("-- " + content)
        except Exception as e:
            errMsg = f"TEXT BROWSER LIST ERROR:{e}"
            self.logger.error(errMsg)

    def add_statusBar_str(self, content_str):
        """
        状态栏添加文字
        :param content_str:字符串
        :return:无
        """
        try:
            self.ui.statusbar.showMessage(":) " + content_str)
        except Exception as e:
            errMsg = f"STATUSBAR ERROR{e}"
            self.logger.error(errMsg)


if __name__ == '__main__':
    freeze_support()
    # 这行是为了解决多进程的问题
    app = QApplication(sys.argv)
    basicAnalysisModule = QmyEGaInAnalysisModule()
    basicAnalysisModule.show()
    sys.exit(app.exec_())
