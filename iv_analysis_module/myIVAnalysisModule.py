# -*- coding: utf-8 -*-
# @Time   : 2021/9/17 19:38
# @Author : Gang
# @File   : myIVAnalysisModule.py
from multiprocessing import freeze_support
import configparser
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import pyqtSlot, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QVBoxLayout, QFileDialog, QLineEdit, QInputDialog
from scipy.optimize import curve_fit

from IVFigure import *
from gangUtils.generalUtils import GeneralUtils as GeneralUtils
from gangLogger.myLog import MyLog
from ivAnalysisConst import *
from ivDataAnalysis import IVDataAnalysis as DataAnalysis
from ui_QWIVAnalysisModule import *


class QmyIVAnalysisModule(QMainWindow):
    logger = MyLog("QmyIVAnalysisModule", BASEDIR)

    def __init__(self, parent=None):
        super(QmyIVAnalysisModule, self).__init__(parent)
        self.ui = Ui_QWIVAnalysisModule()
        self.ui.setupUi(self)
        self.init_set()
        self.init_widget()

        self.getPanelPara()

    def init_set(self):
        self.keyPara = {}
        self.keyPara["SAVE_DATA_STATUE"] = False  # 数据保存标志位，初始化false，另外在点击run之后也应该设置false，绘图完成设置true

    def init_widget(self):
        self.checkConfig()
        self.add_textBrowser_str("*" * 18 + "Welcome" + "*" * 18, showtime=False)
        logMsg = "Please load the data file first."
        self.add_textBrowser_str(logMsg)
        self.add_statusBar_str(logMsg)

        self.ui.actRun.setEnabled(False)
        self.ui.btn_Redraw.setEnabled(False)

        self.forwardLavout = QVBoxLayout(self)
        self.reverseLayout = QVBoxLayout(self)
        self.superPositionLayout = QVBoxLayout(self)
        self.condLayout = QVBoxLayout(self)
        self.condForwardLayout = QVBoxLayout(self)
        self.condReverseLayout = QVBoxLayout(self)

        self.initSaveDir()
        self.createFigure()
        self.logger.debug("The initial configuration is complete.")

    # ============控件触发函数===============
    @pyqtSlot()
    def on_actOpenFiles_triggered(self):
        """
        文件加载
        :return:
        """
        try:
            dlgTitle = "Select multiple files"  # 对话框标题
            filt = "TDMS Files(*.tdms)"  # 文件过滤器
            desktopPath = GeneralUtils.getDesktopPath()
            loadStatue = False
            while not loadStatue:
                fileList, filtUsed = QFileDialog.getOpenFileNames(self, dlgTitle, desktopPath, filt)

                loadStatue = len(fileList) > 0
                if not loadStatue:
                    result = QMessageBox.warning(self, "Warning", "Please select at least one file!",
                                                 QMessageBox.Ok | QMessageBox.Cancel,
                                                 QMessageBox.Ok)
                    if result == QMessageBox.Cancel:
                        break
                else:
                    # file load success!!!!
                    self.keyPara['FILE_PATHS'] = fileList
                    self.add_textBrowser_str(f"{len(fileList)} files have been loaded:")
                    self.add_textBrowser_list(fileList)
                    self.add_textBrowser_str("*" * 45, showtime=False)
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
            self.ui.btn_Redraw.setEnabled(False)
            self.keyPara["SAVE_DATA_STATUE"] = False

            keyPara = self.getPanelPara()
            if keyPara is None:
                return
            else:
                self.keyPara.update(keyPara)
                self.logger.debug(f"Parameters are updated before running. Parameter list:{self.keyPara}")
                self.dataThread = QThread()
                self.dataAnalysis = DataAnalysis(self.keyPara)
                self.dataAnalysis.runEnd.connect(lambda: self.stopThread(self.dataThread))

                self.dataAnalysis.moveToThread(self.dataThread)
                self.dataThread.started.connect(self.dataAnalysis.run)
                self.dataThread.finished.connect(self.drawPre)

                logMsg = "Data calculation..."
                self.addLogMsgWithBar(logMsg)

                self.dataThread.start()
                self.logger.debug(
                    f"Start the data calculation thread--{self.dataThread.currentThread()},Now state:{self.dataThread.isRunning()}")
        except Exception as e:
            errMsg = f"RUN ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_btn_Redraw_clicked(self):
        try:
            keyPara = self.getPanelPara()
            if keyPara is None:
                return
            else:
                self.keyPara.update(keyPara)
                self.logger.debug(f"Parameters are updated before running. Parameter list:{self.keyPara}")
                self.draw()
        except Exception as e:
            errMsg = f"REDRAW ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            self.ui.actRun.setEnabled(True)

    @pyqtSlot()
    def on_actSaveData_triggered(self):
        try:
            preCheck = self.savePreCheck()
            if preCheck:
                # finished check
                dataSavePath = self.keyPara["Data_Save_Path"]

                # fig save
                self.saveFig(dataSavePath)
                # end fig save

                # data save
                self.saveData(dataSavePath)
                # end data save

                logMsg = f"All data has been saved. Path:{dataSavePath}"
                self.addLogMsgWithBar(logMsg)
                QMessageBox.information(self, "Info", logMsg)
        except Exception as e:
            errMsg = f"DATA SAVE ERROR:{e}"
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
            self.saveConfigPara()
            time.sleep(0.1)
            self.logger.debug("Program exits")
            event.accept()
        else:
            event.ignore()

    @pyqtSlot()
    def on_actOperateGuide_triggered(self):
        """
        暂未开发
        :return:
        """
        pass

    @pyqtSlot()
    def on_btn_SaveDir_clicked(self):
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

    # ============控件触发函数===============
    def saveFig(self, dataSavePath):
        """
        图片保存
        :param dataSavePath:
        :return:
        """
        imgPath = os.path.join(dataSavePath, "Images")
        GeneralUtils.creatFolder(dataSavePath, "Images")
        forwardPath = os.path.join(imgPath, "forwardScan.png")
        reversePath = os.path.join(imgPath, "reverseScan.png")
        superPositionPath = os.path.join(imgPath, "superPositionScan.png")
        condPath = os.path.join(imgPath, "conductanceScan.png")
        self.forwardFig.savefig(forwardPath, dpi=100, bbox_inches='tight')
        self.reverseFig.savefig(reversePath, dpi=100, bbox_inches='tight')
        self.superPositionFig.savefig(superPositionPath, dpi=100, bbox_inches='tight')
        self.condFig.savefig(condPath, dpi=100, bbox_inches='tight')

    def saveData(self, dataSavePath):
        """
        数据保存
        :param dataSavePath:
        :return:
        """
        dataPath = os.path.join(dataSavePath, "IVData")
        GeneralUtils.creatFolder(dataSavePath, "IVData")
        forwardPath = os.path.join(dataPath, "forwardScan.txt")
        reversePath = os.path.join(dataPath, "reverseScan.txt")
        superPositionPath = os.path.join(dataPath, "superPositionScan.txt")
        condPath = os.path.join(dataPath, "conductanceScan.txt")

        np.savetxt(forwardPath, self.forH, fmt='%d', delimiter='\t')
        np.savetxt(reversePath, self.revH, fmt='%d', delimiter='\t')
        np.savetxt(superPositionPath, self.supH, fmt='%d', delimiter='\t')
        np.savetxt(condPath, self.condH, fmt='%d', delimiter='\t')

    def savePreCheck(self):
        """
        数据保存之前的检查
        :return:
        """
        if not self.keyPara["SAVE_DATA_STATUE"]:
            errMsg = "The data cannot be saved until the data processing is complete!"
            self.addErrorMsgWithBox(errMsg)
            return False

        dlgTitle = "File name Settings"
        txtLabel = "Please enter the name of the folder to save"
        defaultName = "IVAnalysis"
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

    def checkDataset(self, dataset):
        """
        检查每个进程计算的数据
        :param dataset:
        :return:
        """
        if not dataset:
            return False
        else:
            biasVDataFor, biasVDataReve = dataset[0], dataset[3]
            if biasVDataFor.shape[0] == 0 or biasVDataReve.shape[0] == 0:
                return False
            return True

    def getAggregateData(self, datasets):
        """
        获取多进程计算结果的聚合
        :param datasets: 多线程的结果
        :return:
        """
        if len(datasets) == 1:
            if self.checkDataset(datasets[0]):
                return datasets[0][0], datasets[0][1], datasets[0][2], datasets[0][3], datasets[0][4], datasets[0][
                    5], datasets[0][6], datasets[0][7], datasets[0][8], True
            else:
                errMsg = "No valid drawing data, please adjust data"
                self.addErrorMsgWithBox(errMsg)
                return None, False
        else:
            effectCount = 0

            biasVDataFor, currentDataFor, condDataFor, \
            biasVDataReve, currentDataReve, condDataReve, \
            biasVDataFlat, currentDataFlat, condDataFlat = None, None, None, None, None, None, None, None, None

            for dataset in datasets:
                if self.checkDataset(dataset):
                    if effectCount == 0:
                        effectCount += 1
                        biasVDataFor, currentDataFor, condDataFor, biasVDataReve, currentDataReve, condDataReve, \
                        biasVDataFlat, currentDataFlat, condDataFlat = \
                            dataset[0], dataset[1], dataset[2], dataset[3], dataset[4], dataset[
                                5], \
                            dataset[6], dataset[7], dataset[8]
                    else:
                        biasVDataFor = np.concatenate((biasVDataFor, dataset[0]))
                        currentDataFor = np.concatenate((currentDataFor, dataset[1]))
                        condDataFor = np.concatenate((condDataFor, dataset[2]))
                        biasVDataReve = np.concatenate((biasVDataReve, dataset[3]))
                        currentDataReve = np.concatenate((currentDataReve, dataset[4]))
                        condDataReve = np.concatenate((condDataReve, dataset[5]))
                        biasVDataFlat = np.concatenate((biasVDataFlat, dataset[6]))
                        currentDataFlat = np.concatenate((currentDataFlat, dataset[7]))
                        condDataFlat = np.concatenate((condDataFlat, dataset[8]))
            if effectCount == 0:
                errMsg = "No valid drawing data, please adjust data"
                self.addErrorMsgWithBox(errMsg)
                return None, False
            else:
                return biasVDataFor, currentDataFor, condDataFor, biasVDataReve, currentDataReve, condDataReve, biasVDataFlat, currentDataFlat, condDataFlat, True

    def drawPre(self):
        """
        绘图前置
        :return:
        """
        self.logger.debug("The computing process exits safely and begins computing drawing data")
        datasets = self.dataAnalysis.datasets
        # 这里的这个返回值是多进程的返回数据的集合！
        # 不管是单个文件，还是多个文件，都是List

        try:
            *dataTemp, statue = self.getAggregateData(datasets)
        except Exception as e:
            errMsg = f"The parallel computing draw data aggregation error:{e}"
            self.addErrorMsgWithBox(errMsg)
            self.ui.actRun.setEnabled(True)
        else:
            if not statue:
                return
            else:
                self.biasVDataFor, self.currentDataFor, self.condDataFor, \
                self.biasVDataReve, self.currentDataReve, self.condDataReve, \
                self.biasVDataFlat, self.currentDataFlat, self.condDataFlat = dataTemp

                logMsg = "Start drawing..."
                self.addLogMsgWithBar(logMsg)

                try:
                    self.draw()
                except Exception as e:
                    errMsg = f"DRAW ERROR:{e}"
                    self.addErrorMsgWithBox(errMsg)
                else:
                    self.ui.btn_Redraw.setEnabled(True)
        finally:
            self.ui.actRun.setEnabled(True)

    def draw(self):
        """
        进行绘图工作！！
        :return:
        """
        # 参数读取！！
        SCANRANGE = self.keyPara["le_ScanRange"]
        BINSX = int(self.keyPara["le_BinsX"])
        BINSY = int(self.keyPara["le_BinsY"])
        IMAX = self.keyPara["le_I_Max"]
        IMIN = self.keyPara["le_I_Min"]
        GMAX = self.keyPara["le_G_Max"]
        GMIN = self.keyPara["le_G_Min"]
        VMAX = self.keyPara["le_V_Max"]
        VMIN = self.keyPara["le_V_Min"]
        COLORMAP = self.keyPara["cmb_ColorMap"]

        CMAP = plt.cm.get_cmap(COLORMAP).copy()
        CMAP.set_under("white")
        FONTSIZE = 10

        biasVDataFor = self.biasVDataFor
        currentDataFor = self.currentDataFor
        condDataFor = self.condDataFor
        biasVDataReve = self.biasVDataReve
        currentDataReve = self.currentDataReve
        condDataReve = self.condDataReve
        biasVDataFlat = self.biasVDataFlat
        currentDataFlat = self.currentDataFlat
        condDataFlat = self.condDataFlat

        self.forwardFig = self.forwardCanvas.fig
        self.reverseFig = self.reverseCanvas.fig
        self.superPositionFig = self.superPositionCanvas.fig
        self.condFig = self.condCanvas.fig
        self.condForwardFig = self.condForwardCanvas.fig
        self.condReverseFig = self.condReverseCanvas.fig
        self.forwardFig.clf()
        self.reverseFig.clf()
        self.superPositionFig.clf()
        self.condFig.clf()
        self.condForwardFig.clf()
        self.condReverseFig.clf()

        self.forwardAxes = self.forwardFig.add_subplot()
        self.reverseAxes = self.reverseFig.add_subplot()
        self.superPositionAxes = self.superPositionFig.add_subplot()
        self.condAxes = self.condFig.add_subplot()
        self.condForwardAxes = self.condForwardFig.add_subplot()
        self.condReverseAxes = self.condReverseFig.add_subplot()

        # 绘图部分！！
        # 正扫
        self.forH, forXedges, forYedges, _ = self.forwardAxes.hist2d(x=biasVDataFor, y=currentDataFor,
                                                                     bins=[BINSX, BINSY],
                                                                     range=[[-SCANRANGE, SCANRANGE], [IMIN, IMAX]],
                                                                     vmin=VMIN, vmax=VMAX, cmap=CMAP)
        self.forwardAxes.set_title("Forward Scan")
        self.forwardAxes.set_xlabel("Voltage/V", fontsize=FONTSIZE)
        self.forwardAxes.set_ylabel("Current/nA (logI)", fontsize=FONTSIZE)

        self.forwardFig.tight_layout()
        self.forwardFig.canvas.draw()
        self.forwardFig.canvas.flush_events()
        # 此处还需要进行高斯拟合，做出hist2d之后的拟合曲线！！！
        # forXFit, forYFit = self.getGaussFit(forH, forXedges)
        # self.forwardAxes.plot(forXFit, forYFit, "y-", lw=4)

        # 反扫
        self.revH, revXedges, revYedges, _ = self.reverseAxes.hist2d(x=biasVDataReve, y=currentDataReve,
                                                                     bins=[BINSX, BINSY],
                                                                     range=[[-SCANRANGE, SCANRANGE], [IMIN, IMAX]],
                                                                     vmin=VMIN, vmax=VMAX, cmap=CMAP)
        self.reverseAxes.set_title("Reverse Scan")
        self.reverseAxes.set_xlabel("Voltage/V", fontsize=FONTSIZE)
        self.reverseAxes.set_ylabel("Current/nA (logI)", fontsize=FONTSIZE)

        self.reverseFig.tight_layout()
        self.reverseFig.canvas.draw()
        self.reverseFig.canvas.flush_events()
        # revXFit, revYFit = self.getGaussFit(revH, revXedges)
        # self.reverseAxes.plot(revXFit, revYFit, "y-", lw=4)

        # 叠加
        self.supH, supXedges, supYedges, _ = self.superPositionAxes.hist2d(x=biasVDataFlat, y=currentDataFlat,
                                                                           bins=[BINSX, BINSY],
                                                                           range=[[-SCANRANGE, SCANRANGE],
                                                                                  [IMIN, IMAX]],
                                                                           vmin=VMIN, vmax=VMAX, cmap=CMAP)
        self.superPositionAxes.set_title("SuperPosition Scan")
        self.superPositionAxes.set_xlabel("Voltage/V", fontsize=FONTSIZE)
        self.superPositionAxes.set_ylabel("Current/nA (logI)", fontsize=FONTSIZE)

        self.superPositionFig.tight_layout()
        self.superPositionFig.canvas.draw()
        self.superPositionFig.canvas.flush_events()
        # supXFit, supYFit = self.getGaussFit(supH, supXedges)
        # self.superPositionAxes.plot(supXFit, supYFit, "y-", lw=4)

        # 电导
        self.condH, condXedges, condYedges, _ = self.condAxes.hist2d(x=biasVDataFlat, y=condDataFlat,
                                                                     bins=[BINSX, BINSY],
                                                                     range=[[-SCANRANGE, SCANRANGE], [GMIN, GMAX]],
                                                                     vmin=VMIN, vmax=VMAX, cmap=CMAP)
        self.condAxes.set_title("Conductance Scan")
        self.condAxes.set_xlabel("Voltage/V", fontsize=FONTSIZE)
        self.condAxes.set_ylabel("Conductance/ (logG$_{0}$)", fontsize=FONTSIZE)

        self.condFig.tight_layout()
        self.condFig.canvas.draw()
        self.condFig.canvas.flush_events()
        # condXFit, condYFit = self.getGaussFit(condH, condXedges)
        # self.condAxes.plot(condXFit, condYFit, "y-", lw=4)

        # 电导正扫
        self.condForH, condForXedges, condForYedges, _ = self.condForwardAxes.hist2d(x=biasVDataFor, y=condDataFor,
                                                                     bins=[BINSX, BINSY],
                                                                     range=[[-SCANRANGE, SCANRANGE], [GMIN, GMAX]],
                                                                     vmin=VMIN, vmax=VMAX, cmap=CMAP)
        self.condForwardAxes.set_title("Conductance Forward Scan")
        self.condForwardAxes.set_xlabel("Voltage/V", fontsize=FONTSIZE)
        self.condForwardAxes.set_ylabel("Conductance/ (logG$_{0}$)", fontsize=FONTSIZE)

        self.condForwardFig.tight_layout()
        self.condForwardFig.canvas.draw()
        self.condForwardFig.canvas.flush_events()

        # 电导反扫
        self.condReveH, condReveXedges, condReveYedges, _ = self.condReverseAxes.hist2d(x=biasVDataReve, y=condDataReve,
                                                                              bins=[BINSX, BINSY],
                                                                              range=[[-SCANRANGE, SCANRANGE],
                                                                                     [GMIN, GMAX]],
                                                                              vmin=VMIN, vmax=VMAX, cmap=CMAP)
        self.condReverseAxes.set_title("Conductance Reverse Scan")
        self.condReverseAxes.set_xlabel("Voltage/V", fontsize=FONTSIZE)
        self.condReverseAxes.set_ylabel("Conductance/ (logG$_{0}$)", fontsize=FONTSIZE)

        self.condReverseFig.tight_layout()
        self.condReverseFig.canvas.draw()
        self.condReverseFig.canvas.flush_events()

        # 绘图结束！！
        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.keyPara["SAVE_DATA_STATUE"] = True  # 这个true放在这里的目的是只要绘图完成一遍，就说明产生了新数据，可以保存

    def getGaussFit(self, h, xedges):
        """
        对矩阵进行高斯拟合（列方向！！！）
        :param h:
        :param xedges:
        :param yedges:
        :return:
        """

        xTicks = (xedges[1:] + xedges[:-1]) / 2
        yTicks = np.apply_along_axis(self.gaussFit, 0, h)
        return xTicks, yTicks

    def gaussFit(self, xData):
        IMAX = self.keyPara["le_I_Max"]
        IMIN = self.keyPara["le_I_Min"]
        length = xData.shape[0]

        def gaussFun(x, a, u, sig):
            return a * np.exp(-(x - u) ** 2 / (2 * sig ** 2)) / (sig * np.sqrt(2 * np.pi))

        if not np.any(xData):
            mu = 0
        else:
            try:
                mu = curve_fit(gaussFun, np.arange(length), xData)[0][1]
            except Exception:
                mu = np.mean(np.where(xData == np.max(xData))[0])
        return IMIN + (IMAX - IMIN) * mu / length

    def stopThread(self, thread):
        """
        多进程中进程的停止
        :param thread: 需传入对应的进程
        :return: 无返回值
        """
        try:
            thread.quit()
            thread.wait()
            self.logger.debug(f"Exit {thread.currentThread()} thread，Now state:{thread.isRunning()}")
        except Exception as e:
            errMsg = f"PRECESS EXIT ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def getPanelPara(self):
        """
        run之后，需要进行面板的参数采集
        :return:
        """
        keyPara = {}
        try:
            keyPara["cmb_ColorMap"] = self.ui.cmb_ColorMap.currentText()

            leObjList = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.grp_DrawPara]
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                leObjList.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in leObjList:
                keyPara[obj.objectName()] = float(obj.text())
        except Exception as e:
            errMsg = f"GTE PANEL PARA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            return None
        else:
            return keyPara

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

    def getLastPara(self):
        """
        加载程序同路径下保存好的历史参数并设置，
        :return:
        """
        try:
            config = configparser.ConfigParser()
            configPath = os.path.join(BASEDIR, "config.ini")
            config.read(configPath, encoding='utf-8')
            section_name = "PANEL_PARA"

            le_obj_list = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.grp_DrawPara]

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

    def saveConfigPara(self):
        """
        结束保存参数
        :return:
        """
        try:
            config = configparser.ConfigParser()
            config.optionxform = str  # 这一句相当的关键，因为config这个模块会把option自动的变为全小写，这个设置可以保持原样！
            section_name = "PANEL_PARA"
            config.add_section(section_name)
            le_obj_list = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.grp_DrawPara]

            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in le_obj_list:
                config.set(section_name, obj.objectName(), obj.text())
            # ========这一部分需要手动添加=====
            obj_list_manual = [self.ui.le_Data_Save_Dir]
            for obj in obj_list_manual:
                config.set(section_name, obj.objectName(), obj.text())
            configPath = os.path.join(BASEDIR, "config.ini")
            with open(configPath, mode="w", encoding="utf-8") as f:
                config.write(f)
            self.logger.debug("Parameters have been saved")
        except Exception as e:
            errMsg = f"PARA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def getSameWidget(self, widgetName, activeXName):
        """
        获取某个 widget 中同类型的控件
        :param widgetName: widget名，传入的是ui中的某个widget名
        :param activeXName: 控件类型，传入的是对象
        :return: 寻找到的对象集合(List)
        """
        return widgetName.findChildren(activeXName)

    def createFigure(self):
        self.forwardCanvas = MyFigureCanvas()
        self.reverseCanvas = MyFigureCanvas()
        self.superPositionCanvas = MyFigureCanvas()
        self.condCanvas = MyFigureCanvas()
        self.condForwardCanvas = MyFigureCanvas()
        self.condReverseCanvas = MyFigureCanvas()

        self.forwardToolBar = MyNavigationToolbar(self.forwardCanvas, self.forwardCanvas.mainFrame)
        self.reverseToolBar = MyNavigationToolbar(self.reverseCanvas, self.reverseCanvas.mainFrame)
        self.superPositionToolBar = MyNavigationToolbar(self.superPositionCanvas, self.superPositionCanvas.mainFrame)
        self.condToolBar = MyNavigationToolbar(self.condCanvas, self.condCanvas.mainFrame)
        self.condForwardToolBar = MyNavigationToolbar(self.condForwardCanvas, self.condForwardCanvas.mainFrame)
        self.condReverseToolBar = MyNavigationToolbar(self.condReverseCanvas, self.condReverseCanvas.mainFrame)

        self.forwardLavout.addWidget(self.forwardCanvas)
        self.forwardLavout.addWidget(self.forwardToolBar)
        self.reverseLayout.addWidget(self.reverseCanvas)
        self.reverseLayout.addWidget(self.reverseToolBar)
        self.superPositionLayout.addWidget(self.superPositionCanvas)
        self.superPositionLayout.addWidget(self.superPositionToolBar)
        self.condLayout.addWidget(self.condCanvas)
        self.condLayout.addWidget(self.condToolBar)
        self.condForwardLayout.addWidget(self.condForwardCanvas)
        self.condForwardLayout.addWidget(self.condForwardToolBar)
        self.condReverseLayout.addWidget(self.condReverseCanvas)
        self.condReverseLayout.addWidget(self.condReverseToolBar)

        self.ui.grp_forward.setLayout(self.forwardLavout)
        self.ui.grp_reverse.setLayout(self.reverseLayout)
        self.ui.grp_superPosition.setLayout(self.superPositionLayout)
        self.ui.grp_cond.setLayout(self.condLayout)
        self.ui.grp_cond_for.setLayout(self.condForwardLayout)
        self.ui.grp_cond_rev.setLayout(self.condReverseLayout)

    def initSaveDir(self):
        """
        初始化保存数据路径是桌面路径，后续加载完数据后应当修改为数据的文件路径！！
        :return:
        """
        deskPath = GeneralUtils.getDesktopPath()
        self.ui.le_Data_Save_Dir.setText(deskPath)

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
    ivAnalysisModule = QmyIVAnalysisModule()
    ivAnalysisModule.show()
    sys.exit(app.exec_())
