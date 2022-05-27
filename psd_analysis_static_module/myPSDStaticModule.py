# -*- coding: utf-8 -*-
# @Time   : 2021/9/26 9:23
# @Author : Gang
# @File   : myPSDStaticModule.py
import sys, time
import configparser

import numpy as np
from PyQt5.QtCore import pyqtSlot, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QVBoxLayout, QLineEdit

from psdStaticDataAnalysis import PSDStaticDataAnalysis as DataAnalysis
from gangUtils.generalUtils import GeneralUtils as GeneralUtils
from gangLogger.myLog import MyLog
from psdStaticConst import *
from psdStaticFigure import *
from ui_QWPSDAnalysisStaticModule import *
import matplotlib.pyplot as plt
from scipy import linalg
from sklearn import mixture
import matplotlib as mpl


class QmyPSDStaticModule(QMainWindow):
    logger = MyLog("QmyPSDStaticModule", BASEDIR)

    def __init__(self, parent=None):
        super(QmyPSDStaticModule, self).__init__(parent)
        self.ui = Ui_QWPSDAnalysisStaticModule()
        self.ui.setupUi(self)
        self.init_set()
        self.init_widget()

    def init_set(self):
        self.keyPara = {}
        self.keyPara["SAVE_DATA_STATUE"] = False  # 数据保存标志位，初始化false，另外在点击run之后也应该设置false，绘图完成设置true

    def init_widget(self):
        self.checkConfig()
        self.ui.actRun.setEnabled(False)

        self.psdLayout = QVBoxLayout(self)
        self.originalLayout = QVBoxLayout(self)
        self.createFigure()

    # ============控件触发函数===============

    @pyqtSlot()
    def on_le_CondHigh_editingFinished(self):
        self.ui.le_XlimitRight.setText(self.ui.le_CondHigh.text())
        self.ui.le_XlimitRightOri.setText(self.ui.le_CondHigh.text())

    @pyqtSlot()
    def on_le_CondLow_editingFinished(self):
        self.ui.le_XLimitLeft.setText(self.ui.le_CondLow.text())
        self.ui.le_XLimitLeftOri.setText(self.ui.le_CondLow.text())

    @pyqtSlot()
    def on_actSaveData_triggered(self):
        try:
            preCheck = self.savePreCheck()
            if preCheck:
                self.saveFig()

                self.saveData()

                # TODO
                # 此处的数据保存先暂停，因为具体保存成什么格式？怎么保存？
                # 后面确定了在保存！！！
        except Exception as e:
            errMsg = f"DATA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_actRun_triggered(self):
        try:
            self.ui.actRun.setEnabled(False)
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
            errMsg = f"RUN ERROR :{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_actOpenFiles_triggered(self):
        """
        文件加载，注意这里加载的是经过处理之后的已经切分好的单条曲线！！
        :return:
        """
        try:
            dlgTitle = "Select a single_trace data file"  # 对话框标题
            filt = "npz Files(*.npz)"  # 文件过滤器
            desktopPath = GeneralUtils.getDesktopPath()
            loadStatue = False
            while not loadStatue:
                filePath, _ = QFileDialog.getOpenFileName(self, dlgTitle, desktopPath, filt)
                loadStatue = False if filePath == "" else True
                if not loadStatue:
                    result = QMessageBox.warning(self, "Warning", "Please select a file!",
                                                 QMessageBox.Ok | QMessageBox.Cancel,
                                                 QMessageBox.Ok)
                    if result == QMessageBox.Cancel:
                        break
                else:
                    # file load success!!!!
                    self.keyPara["FILE_PATH"] = filePath
                    logMsg = f"File loading succeeded:{filePath}"
                    self.addLogMsgWithBar(logMsg)
                    self.ui.actRun.setEnabled(True)
        except Exception as e:
            errMsg = f"DATA FILE LOAD ERROR:{e}"
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
        str_info = "Sure to quit?"
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

    # ============控件触发函数===============
    def saveFig(self):
        saveFolderPath = self.keyPara["SAVE_FOLDER_PATH"]
        imgPathOri = os.path.join(saveFolderPath, "StaticPSDOri.png")
        imgPath = os.path.join(saveFolderPath, "StaticPSD.png")

        if os.path.exists(imgPath):
            curTime = time.strftime("%Y-%m-%d_%H_%M", time.localtime())
            imgPath = os.path.join(saveFolderPath, f"StaticPSD{curTime}.png")
        self.fig.savefig(imgPath, dpi=300, bbox_inches='tight')

        if os.path.exists(imgPathOri):
            curTime = time.strftime("%Y-%m-%d_%H_%M", time.localtime())
            imgPathOri = os.path.join(saveFolderPath, f"StaticPSDOri{curTime}.png")
        self.figOri.savefig(imgPathOri, dpi=300, bbox_inches='tight')

        logMsg = f"Images have been saved to {saveFolderPath}"
        self.addLogMsgWithBar(logMsg)

    def saveData(self):
        saveFolderPath = self.keyPara["SAVE_FOLDER_PATH"]
        dataPathOri = os.path.join(saveFolderPath, "psdStaticOriAnalysis.txt")
        dataPath = os.path.join(saveFolderPath, "psdStaticAnalysis.txt")

        if os.path.exists(dataPathOri):
            curTime = time.strftime("%Y-%m-%d_%H_%M", time.localtime())
            dataPathOri = os.path.join(saveFolderPath, f"psdStaticOriAnalysis{curTime}.txt")
        if os.path.exists(dataPath):
            curTime = time.strftime("%Y-%m-%d_%H_%M", time.localtime())
            dataPath = os.path.join(saveFolderPath, f"psdStaticAnalysis{curTime}.txt")

        np.savetxt(dataPathOri, self.hOri, fmt='%d', delimiter='\t')
        np.savetxt(dataPath, self.h, fmt='%d', delimiter='\t')

        logMsg = f"Data have been saved to {saveFolderPath}"
        self.addLogMsgWithBar(logMsg)

    def draw(self):
        CMAPNAME = self.keyPara["cmb_ColorMap"]
        CMAPNAMEORI = self.keyPara["cmb_ColorMapOri"]

        MAPUNDER = self.keyPara["cmb_MapUnder"]
        MAPUNDERORI = self.keyPara["cmb_MapUnderOri"]

        MAPOVER = self.keyPara["cmb_MapOver"]
        MAPOVERORI = self.keyPara["cmb_MapOverOri"]

        BINS = int(self.keyPara["le_Bins"])
        BINSORI = int(self.keyPara["le_BinsOri"])

        VMIN = self.keyPara["le_Vmin"]
        VMINORI = self.keyPara["le_VminOri"]

        VMAX = self.keyPara["le_Vmax"]
        VMAXORI = self.keyPara["le_VmaxOri"]

        XLEFT = self.keyPara["le_XLimitLeft"]
        XLEFTORI = self.keyPara["le_XLimitLeftOri"]

        XRIGHT = self.keyPara["le_XlimitRight"]
        XRIGHTORI = self.keyPara["le_XlimitRightOri"]

        YLEFT = self.keyPara["le_YLimitLeft"]
        YLEFTORI = self.keyPara["le_YLimitLeftOri"]

        YRIGHT = self.keyPara["le_YLimitRight"]
        YRIGHTORI = self.keyPara["le_YLimitRightOri"]

        FITLOW = self.keyPara["le_FitLow"]
        FITLOWOri = self.keyPara["le_FitLowOri"]

        FITHIGH = self.keyPara["le_FitHigh"]
        FITHIGHOri = self.keyPara["le_FitHighOri"]

        cmap = plt.cm.get_cmap(CMAPNAME).copy()
        if "Null" != MAPUNDER:
            cmap.set_under(MAPUNDER)
        if "Null" != MAPOVER:
            cmap.set_over(MAPOVER)

        cmapOri = plt.cm.get_cmap(CMAPNAMEORI).copy()
        if "Null" != MAPUNDERORI:
            cmapOri.set_under(MAPUNDERORI)
        if "Null" != MAPOVERORI:
            cmapOri.set_over(MAPOVERORI)

        # 高斯拟合
        a = np.log10(self.gMean).reshape(-1, 1)
        b = np.log10(self.scaledPSDOri).reshape(-1, 1)
        c = np.log10(self.scaledPSD).reshape(-1, 1)
        XOri = np.concatenate((a, b), axis=1)
        X = np.concatenate((a, c), axis=1)

        gmmOri = mixture.GaussianMixture(n_components=1, covariance_type="full").fit(XOri)
        gmmOriMean, gmmOriCov = gmmOri.means_[0], gmmOri.covariances_[0]
        vOri, wOri = linalg.eigh(gmmOriCov)
        vOri = 2. * np.sqrt(2.) * np.sqrt(vOri)
        uOri = wOri[0] / linalg.norm(wOri[0])
        angleOri = np.arctan(uOri[1] / uOri[0])
        angleOri = 180. * angleOri / np.pi  # convert to degrees

        gmm = mixture.GaussianMixture(n_components=1, covariance_type="full").fit(X)
        gmmMean, gmmCov = gmm.means_[0], gmm.covariances_[0]
        v, w = linalg.eigh(gmmCov)
        v = 2. * np.sqrt(2.) * np.sqrt(v)
        u = w[0] / linalg.norm(w[0])
        angle = np.arctan(u[1] / u[0])
        angle = 180. * angle / np.pi  # convert to degrees

        # 原始图

        self.figOri = self.originalCanvas.fig
        self.figOri.clf()
        self.axOri = self.figOri.add_subplot()
        self.hOri, xedgesOri, yedgesOri, imageOri = self.axOri.hist2d(np.log10(self.gMean), np.log10(self.scaledPSDOri),
                                                                      bins=BINSORI,
                                                                      range=[[XLEFTORI, XRIGHTORI],
                                                                             [YLEFTORI, YRIGHTORI]],
                                                                      vmin=VMINORI, vmax=VMAXORI, cmap=cmapOri)
        self.figOri.colorbar(imageOri, pad=0.02, aspect=50)
        for ratio in np.linspace(FITLOWOri, FITHIGHOri, 5):
            ellOri = mpl.patches.Ellipse(gmmOriMean, vOri[0] * ratio, vOri[1] * ratio, 180. + angleOri, edgecolor='k',
                                         lw=2, fill=False)
            self.axOri.add_artist(ellOri)
        self.axOri.set_xlabel('G$_{AVG}$ (G$_0)$')
        self.axOri.set_ylabel("Noise Power/G (G$_0)$")

        x_nums_ori = np.arange(int(np.ceil(XLEFTORI)), int(np.ceil(XRIGHTORI)), 1)
        self.axOri.set_xticks(x_nums_ori)
        self.axOri.set_xticklabels(["$10^" + "{" + f"{i}" + "}$" for i in x_nums_ori])
        y_nums_ori = np.arange(int(np.ceil(YLEFTORI)), int(np.ceil(YRIGHTORI)), 1)
        self.axOri.set_yticks(y_nums_ori)
        self.axOri.set_yticklabels(["$10^" + "{" + f"{i}" + "}$" for i in y_nums_ori])
        # axOri.set_xlim(XLEFTORI, XRIGHTORI)
        # axOri.set_ylim(YLEFTORI, YRIGHTORI)

        self.figOri.tight_layout()
        self.figOri.canvas.draw()
        self.figOri.canvas.flush_events()

        # 拟合图

        self.fig = self.psdCanvas.fig
        self.fig.clf()
        self.ax = self.fig.add_subplot()
        self.h, xedges, yedges, image = self.ax.hist2d(np.log10(self.gMean), np.log10(self.scaledPSD),
                                                       bins=BINS,
                                                       range=[[XLEFT, XRIGHT], [YLEFT, YRIGHT]],
                                                       vmin=VMIN, vmax=VMAX, cmap=cmap)
        self.fig.colorbar(image, pad=0.02, aspect=50)
        for ratio in np.linspace(FITLOW, FITHIGH, 5):
            ell = mpl.patches.Ellipse(gmmMean, v[0] * ratio, v[1] * ratio, 180. + angle, edgecolor='k', lw=2,
                                      fill=False)
            self.ax.add_artist(ell)
        self.ax.text(XRIGHT - 0.5, YRIGHT - 0.3, f"N={self.minN:.2f}")
        self.ax.set_xlabel('G$_{AVG}$ (G$_0)$')
        yLabel = "Noise Power/G$^{" + f"{self.minN:.2f}" + "}$"
        self.ax.set_ylabel(yLabel)

        x_nums = np.arange(int(np.ceil(XLEFT)), int(np.ceil(XRIGHT)), 1)
        self.ax.set_xticks(x_nums)
        self.ax.set_xticklabels(["$10^" + "{" + f"{i}" + "}$" for i in x_nums])
        y_nums = np.arange(int(np.ceil(YLEFT)), int(np.ceil(YRIGHT)), 1)
        self.ax.set_yticks(y_nums)
        self.ax.set_yticklabels(["$10^" + "{" + f"{i}" + "}$" for i in y_nums])
        # ax.set_xlim(XLEFT, XRIGHT)
        # ax.set_ylim(YLEFT, YRIGHT)

        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.keyPara["SAVE_DATA_STATUE"] = True  # 这个true放在这里的目的是只要绘图完成一遍，就说明产生了新数据，可以保存

    def savePreCheck(self):
        """
        数据保存之前的检查
        :return:
        """
        if not self.keyPara["SAVE_DATA_STATUE"]:
            errMsg = "The data cannot be saved until the data processing is complete!"
            self.addErrorMsgWithBox(errMsg)
            return False

        logMsg = "Data saving, please wait..."
        self.addLogMsgWithBar(logMsg)

        filePath = self.keyPara["FILE_PATH"]
        folderName = self.ui.le_SaveFolder_Name.text()
        self.keyPara["le_SaveFolder_Name"] = folderName
        saveRootDir = os.path.dirname(os.path.dirname(filePath))
        saveFolderPath = os.path.join(saveRootDir, folderName)
        self.keyPara["SAVE_FOLDER_PATH"] = saveFolderPath

        try:
            GeneralUtils.creatFolder(saveRootDir, folderName)
        except Exception as e:
            errMsg = f"NEW FOLDER ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            return False
        else:
            return True

    def drawPre(self):
        """
        绘图前的准备
        :return:
        """
        try:
            self.logger.debug("The computing process exits safely and begins computing drawing data")
            dataset = self.dataAnalysis.dataset
            if dataset is None:
                errMsg = "DATASET ERROR"
                self.addErrorMsgWithBox(errMsg)
            else:
                self.gMean, self.integPSD, self.minN = dataset
                signTemp = np.sign(self.gMean)
                self.gMeanAF = signTemp * np.power(np.abs(self.gMean), self.minN)
                self.scaledPSD = self.integPSD / self.gMeanAF
                self.scaledPSDOri = self.integPSD / self.gMean
                try:
                    self.draw()
                except Exception as e:
                    errMsg = f"DRAW ERROR:{e}"
                    self.addErrorMsgWithBox(errMsg)
        except Exception as e:
            errMsg = f"DRAWPRE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
        finally:
            self.ui.actRun.setEnabled(True)

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
            keyPara["cmb_MapUnder"] = self.ui.cmb_MapUnder.currentText()
            keyPara["cmb_MapOver"] = self.ui.cmb_MapOver.currentText()
            keyPara["cmb_MapUnderOri"] = self.ui.cmb_MapUnderOri.currentText()
            keyPara["cmb_MapOverOri"] = self.ui.cmb_MapOverOri.currentText()
            keyPara["cmb_ColorMapOri"] = self.ui.cmb_ColorMapOri.currentText()

            leObjList = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_Params, self.ui.tw_FigureParams]
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
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_Params, self.ui.tw_FigureParams]

            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in le_obj_list:
                obj.setText(config.get(section_name, obj.objectName()))
            obj_list_manual = [self.ui.le_SaveFolder_Name]
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
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_Params, self.ui.tw_FigureParams]

            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in le_obj_list:
                config.set(section_name, obj.objectName(), obj.text())
            # ========这一部分需要手动添加=====
            obj_list_manual = [self.ui.le_SaveFolder_Name]
            for obj in obj_list_manual:
                config.set(section_name, obj.objectName(), obj.text())
            configPath = os.path.join(BASEDIR, "config.ini")
            with open(configPath, mode="w", encoding="utf-8") as f:
                config.write(f)
            self.logger.debug("Parameters have been saved")
        except Exception as e:
            errMsg = f"PARA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def createFigure(self):
        self.psdCanvas = MyFigureCanvas()
        self.psdToolBar = MyNavigationToolbar(self.psdCanvas, self.psdCanvas.mainFrame)
        self.psdLayout.addWidget(self.psdCanvas)
        self.psdLayout.addWidget(self.psdToolBar)
        self.ui.grp_PSD.setLayout(self.psdLayout)

        self.originalCanvas = MyFigureCanvas()
        self.originalToolBar = MyNavigationToolbar(self.originalCanvas, self.originalCanvas.mainFrame)
        self.originalLayout.addWidget(self.originalCanvas)
        self.originalLayout.addWidget(self.originalToolBar)
        self.ui.grp_original.setLayout(self.originalLayout)

    def getSameWidget(self, widgetName, activeXName):
        """
        获取某个 widget 中同类型的控件
        :param widgetName: widget名，传入的是ui中的某个widget名
        :param activeXName: 控件类型，传入的是对象
        :return: 寻找到的对象集合(List)
        """
        return widgetName.findChildren(activeXName)

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
    app = QApplication(sys.argv)
    psdStaticModule = QmyPSDStaticModule()
    psdStaticModule.show()
    sys.exit(app.exec_())
