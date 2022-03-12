# -*- coding: utf-8 -*-
# @Time   : 2021/3/31 14:51
# @Author : Gang
# @File   : myCorrectationAnalysisModule.py
import sys, time

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QVBoxLayout, QFileDialog, QLineEdit
from correlationFigure import *
import numpy as np

from gangLogger.myLog import MyLog
from gangUtils.generalUtils import GeneralUtils
from correlationConst import *

from ui_QWCorrelationAnalysisModule import Ui_QWCorrelationAnalysisModule


class QmyCorrelationAnalysisModule(QMainWindow):
    logger = MyLog("QmyCorrelationAnalysisModule", BASEDIR)

    def __init__(self, parent=None):
        super(QmyCorrelationAnalysisModule, self).__init__(parent)
        self.ui = Ui_QWCorrelationAnalysisModule()
        self.ui.setupUi(self)
        self.init_set()
        self.init_widget()

    def init_set(self):
        self.keyPara = {}
        self.keyPara["SAVE_DATA_STATUE"] = False  # 数据保存标志位，初始化false，另外在点击run之后也应该设置false，绘图完成设置true

    def init_widget(self):
        self.ui.actRun.setEnabled(False)
        self.correlationLayout = QVBoxLayout(self)

        self.createFigure()

    # =============== 控件触发函数===============
    @pyqtSlot()
    def on_actQuit_triggered(self):
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
            time.sleep(0.1)
            self.logger.debug("Program exits")
            event.accept()
        else:
            event.ignore()

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
    def on_actRun_triggered(self):
        try:
            self.ui.actRun.setEnabled(False)
            self.keyPara["SAVE_DATA_STATUE"] = False

            keyPara = self.get_panel_para()
            if keyPara is None:
                return
            else:
                self.keyPara.update(keyPara)
                self.logger.debug(f"Parameters are updated before running. Parameter list:{self.keyPara}")

                self.draw_fig()
        except Exception as e:
            errMsg = f"RUN ERROR :{e}"
            self.addErrorMsgWithBox(errMsg)
        finally:
            self.ui.actRun.setEnabled(True)

    @pyqtSlot()
    def on_actSaveData_triggered(self):
        try:
            preCheck = self.savePreCheck()
            if preCheck:
                self.saveFig()

                # self.saveData()

                # TODO
                # 此处的数据保存先暂停，因为具体保存成什么格式？怎么保存？
                # 后面确定了在保存！！！
        except Exception as e:
            errMsg = f"DATA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    # =============== 控件触发函数===============
    def saveFig(self):
        saveFolderPath = self.keyPara["SAVE_FOLDER_PATH"]
        imgPath = os.path.join(saveFolderPath, "Correlation.png")

        if os.path.exists(imgPath):
            curTime = time.strftime("%Y-%m-%d_%H_%M", time.localtime())
            imgPath = os.path.join(saveFolderPath, f"Correlation{curTime}.png")
        self.fig.savefig(imgPath, dpi=300, bbox_inches='tight')

        logMsg = f"Images have been saved to {saveFolderPath}"
        self.addLogMsgWithBar(logMsg)
    def draw_fig(self):
        VMAX = self.keyPara["le_Vmax"]
        VMIN = self.keyPara["le_Vmin"]
        COLORMAP = self.keyPara["cmb_ColorMap"]
        BINS = int(self.keyPara["le_Bins"])
        COND_HIGH = self.keyPara["le_CondHigh"]
        COND_LOW = self.keyPara["le_CondLow"]
        DPI = int(self.keyPara["le_Fig_dpi"])
        FONTSIZE = 12

        filePath = self.keyPara["FILE_PATH"]

        dataset = np.load(filePath)
        conductance = dataset["conductance_array"]
        temp = np.array([np.histogram(data, range=[COND_LOW, COND_HIGH], bins=BINS)[0] for data in conductance])
        n_corr = np.corrcoef(temp.T)

        self.fig = self.figureCanvas.fig
        self.fig.clf()
        self.fig.set_dpi(DPI)
        self.ax = self.fig.add_subplot()
        mesh = self.ax.pcolormesh(n_corr, vmax=VMAX, vmin=VMIN, cmap=COLORMAP)
        # self.fig.colorbar(mesh, pad=0.02, aspect=50, ticks=None)
        xticks = np.linspace(0, BINS, 10)
        xticklabels = [str(round(idx, 2)) for idx in np.linspace(COND_LOW, COND_HIGH, 10)]
        yticks = np.linspace(0, BINS, 10)
        yticklabels = xticklabels
        self.ax.set_xticks(xticks)
        self.ax.set_xticklabels(xticklabels, rotation="horizontal")
        self.ax.set_yticks(yticks)
        self.ax.set_yticklabels(yticklabels, rotation="horizontal")
        self.ax.set_xlabel("log G/G0", fontsize=FONTSIZE)
        self.ax.set_ylabel("log G/G0", fontsize=FONTSIZE)

        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.keyPara["SAVE_DATA_STATUE"] = True  # 这个true放在这里的目的是只要绘图完成一遍，就说明产生了新数据，可以保存

    def get_panel_para(self):
        keyPara = {}
        le_obj_list = self.get_same_widget(self.ui.grp_Fig_Para, QLineEdit)
        for obj in le_obj_list:
            keyPara[obj.objectName()] = float(obj.text())
        keyPara["cmb_ColorMap"] = self.ui.cmb_ColorMap.currentText()
        return keyPara

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

    def get_same_widget(self, widget_name, activeX_name):
        return widget_name.findChildren(activeX_name)

    def createFigure(self):
        """
        在程序ui建立的初期，就创建Figure()，后面不断地刷新即可
        :return:
        """
        # self.key_para["le_Fig_dpi"]=int(self.ui.le_Fig_dpi.text())
        # DPI=self.key_para["le_Fig_dpi"]
        self.figureCanvas = MyFigureCanvas()
        self.correlationLayout.addWidget(self.figureCanvas)
        self.ui.grp_Correlation.setLayout(self.correlationLayout)

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
    correctationAnalysisModule = QmyCorrelationAnalysisModule()
    correctationAnalysisModule.show()
    sys.exit(app.exec_())
