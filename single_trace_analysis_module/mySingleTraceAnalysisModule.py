# -*- coding: utf-8 -*-
# @Time   : 2020/12/18 10:39
# @Author : Gang
# @File   : mySingleTraceAnalysisModule.py
import sys
import numpy as np
import os
import time

from gangLogger.myLog import MyLog

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QVBoxLayout

from ui_QWSingleTraceAnalysisModule import Ui_QWSingleTraceAnalysisModule
from gangUtils.generalUtils import GeneralUtils
from singleTraceFigure import MyFigureCanvas
from singleTraceConst import *


class QmySingleTraceAnalysisModule(QMainWindow):
    logger = MyLog("QmySingleTraceAnalysisModule", BASEDIR)

    def __init__(self, parent=None):
        super(QmySingleTraceAnalysisModule, self).__init__(parent)
        self.ui = Ui_QWSingleTraceAnalysisModule()
        self.ui.setupUi(self)
        self.init_widget_para()

    def init_widget_para(self):
        self.ui.actSaveData.setEnabled(False)
        self.ui.btn_Save_Current_Trace.setEnabled(False)
        self.ui.btn_Drop_Current_Trace.setEnabled(False)
        self.ui.btn_Last_Trace.setEnabled(False)
        self.ui.btn_Next_Trace.setEnabled(False)
        self.ui.horizontalSlider.setEnabled(False)
        self.tracePreviewLayout = QVBoxLayout(self)

        self.file_path = ""
        self.saveFolderName = ""
        self.saveFolderPath = ""
        self.conductance = None
        self.distance = None
        self.length = None
        self.additional_length = None
        self.IS_SELECT_ARRAR = None
        self.TRACE_NUM = None
        self.CURRENT_INDEX = None
        self.SELECT_COUNT = None
        self.save_format = "npz"

        self.create_figure()

    # =============== 控件触发函数===============
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
            time.sleep(0.1)
            self.logger.debug("Program exits")
            event.accept()
        else:
            event.ignore()

    @pyqtSlot()
    def on_actSaveData_triggered(self):
        """
        保存筛选之后的数据
        :return: 无返回值
        """
        dlg_title = "Info"
        str_info = f"{self.SELECT_COUNT} pieces of data have been selected. Are you sure to save them?"
        reply = QMessageBox.question(self, dlg_title, str_info,
                                     QMessageBox.Yes | QMessageBox.Cancel,
                                     QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.get_save_format()

            filePath = self.file_path
            folderName = self.ui.le_SaveFolder_Name.text()
            self.saveFolderName = folderName
            saveRootDir = os.path.dirname(os.path.dirname(filePath))
            saveFolderPath = os.path.join(saveRootDir, folderName)
            self.saveFolderPath = saveFolderPath

            try:
                GeneralUtils.creatFolder(saveRootDir, folderName)
            except Exception as e:
                errMsg = f"NEW FOLDER ERROR:{e}"
                self.addErrorMsgWithBox(errMsg)
                return
            else:
                try:
                    self.save_select_data()
                except Exception as e:
                    errMsg = f"SAVE DATA ERROR:{e}"
                    self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_actOpenFiles_triggered(self):
        """
        打开按钮，目前暂只支持单个goodtrace的查看
        :return: 无返回值
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
                    # 当程序执行到这里，说明成功加载，初始化数据，显示第一条单条
                    self.file_path = filePath
                    logMsg = f"File loading succeeded:{filePath}"
                    self.addLogMsgWithBar(logMsg)

                    self.init_dataset(filePath)
                    self.init_first_curve()
                    self.draw_fig()

                    if self.CURRENT_INDEX == self.TRACE_NUM - 1:
                        self.ui.btn_Next_Trace.setEnabled(False)
                    else:
                        self.ui.btn_Next_Trace.setEnabled(True)

                    self.ui.horizontalSlider.setEnabled(True)
                    self.ui.btn_Save_Current_Trace.setEnabled(True)
                    self.ui.btn_Drop_Current_Trace.setEnabled(True)
                    self.ui.actSaveData.setEnabled(True)
        except Exception as e:
            errMsg = f"DATA FILE LOAD ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_btn_Next_Trace_clicked(self):
        self.CURRENT_INDEX += 1
        if self.CURRENT_INDEX == self.TRACE_NUM - 1:
            self.ui.btn_Next_Trace.setEnabled(False)

        index = self.CURRENT_INDEX
        self.ui.btn_Last_Trace.setEnabled(True)
        self.ui.horizontalSlider.setValue(index)
        self.ui.progressBar.setValue(index)
        self.ui.le_Current_Index.setText(str(index + 1))
        self.draw_fig()

        if self.IS_SELECT_ARRAR[index] == 0:
            self.ui.btn_Save_Current_Trace.setEnabled(True)
            self.ui.btn_Drop_Current_Trace.setEnabled(False)
        else:
            self.ui.btn_Save_Current_Trace.setEnabled(False)
            self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_btn_Last_Trace_clicked(self):
        self.CURRENT_INDEX -= 1
        if self.CURRENT_INDEX == 0:
            self.ui.btn_Last_Trace.setEnabled(False)

        index = self.CURRENT_INDEX
        self.ui.btn_Next_Trace.setEnabled(True)
        self.ui.horizontalSlider.setValue(index)
        self.ui.progressBar.setValue(index)
        self.ui.le_Current_Index.setText(str(index + 1))
        self.draw_fig()

        if self.IS_SELECT_ARRAR[index] == 0:
            self.ui.btn_Save_Current_Trace.setEnabled(True)
            self.ui.btn_Drop_Current_Trace.setEnabled(False)
        else:
            self.ui.btn_Save_Current_Trace.setEnabled(False)
            self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_actOperateGuide_triggered(self):
        pass

    @pyqtSlot(int)
    def on_horizontalSlider_valueChanged(self, value):
        self.CURRENT_INDEX = value
        self.ui.le_Current_Index.setText(str(value + 1))
        self.ui.progressBar.setValue(value)
        self.draw_fig()

        if self.IS_SELECT_ARRAR[value] == 0:
            self.ui.btn_Save_Current_Trace.setEnabled(True)
            self.ui.btn_Drop_Current_Trace.setEnabled(False)
        else:
            self.ui.btn_Save_Current_Trace.setEnabled(False)
            self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_rdo_Format_csv_clicked(self):
        dlg_title = "Info"
        str_info = "You are advised to use the default data store format: npz \nConfirm the modification?？"
        reply = QMessageBox.warning(self, dlg_title, str_info,
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        if reply == QMessageBox.No:
            self.ui.rdo_Format_npz.setChecked(True)

    @pyqtSlot()
    def on_btn_Save_Current_Trace_clicked(self):
        index = self.CURRENT_INDEX
        self.IS_SELECT_ARRAR[index] = 1
        self.SELECT_COUNT += 1
        self.ui.le_Chosen_Nums.setText(str(self.SELECT_COUNT))
        self.ui.btn_Save_Current_Trace.setEnabled(False)
        self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_btn_Drop_Current_Trace_clicked(self):
        index = self.CURRENT_INDEX
        self.IS_SELECT_ARRAR[index] = 0
        self.SELECT_COUNT -= 1
        self.ui.le_Chosen_Nums.setText(str(self.SELECT_COUNT))
        self.ui.btn_Save_Current_Trace.setEnabled(True)
        self.ui.btn_Drop_Current_Trace.setEnabled(False)

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

    # =============== 控件触发函数===============

    def init_dataset(self, file_path):
        """
        初始化数据集，针对读取的数据将参数初始化
        :param file_path: goodtrace文件路径
        :return:
        """
        dataset = np.load(file_path)
        self.conductance, self.distance, self.length, self.additional_length = dataset['conductance_array'], dataset[
            'distance_array'], dataset["length_array"], dataset["additional_length"]
        self.IS_SELECT_ARRAR = np.zeros(self.conductance.shape[0], dtype=int)
        self.TRACE_NUM = self.conductance.shape[0]
        self.CURRENT_INDEX = 0
        self.SELECT_COUNT = 0

    def init_first_curve(self):
        """
        根据读取进来数据的信息设置面板上的初始化参数
        :return:
        """
        self.ui.horizontalSlider.setMaximum(self.TRACE_NUM - 1)
        self.ui.progressBar.setMaximum(self.TRACE_NUM - 1)
        self.ui.horizontalSlider.setValue(0)
        self.ui.progressBar.setValue(0)
        self.ui.le_Trace_Nums.setText(str(self.TRACE_NUM))
        self.ui.le_Current_Index.setText(str(self.CURRENT_INDEX + 1))
        self.ui.le_Chosen_Nums.setText(str(self.SELECT_COUNT))

    def create_figure(self):
        """
        在程序ui建立的初期，就创建Figure()，后面不断地刷新即可
        :return:
        """
        self.traceCanvas = MyFigureCanvas()
        self.tracePreviewLayout.addWidget(self.traceCanvas)
        self.ui.grp_TracePreview.setLayout(self.tracePreviewLayout)

    def draw_fig(self):
        """
        刷新式绘图
        :return:
        """
        self.fig = self.traceCanvas.fig
        self.fig.clf()
        conductance, distance = self.conductance[self.CURRENT_INDEX], self.distance[self.CURRENT_INDEX]
        ax = self.fig.add_subplot()
        ax.plot(distance, conductance)
        ax.set_xlabel('Length / nm')
        ax.set_ylabel('Conductance')
        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def save_select_data(self):
        """
        保存数据函数的实现
        :return:
        """
        saveFolderPath = self.saveFolderPath
        suffix = self.save_format

        saveFilePath = os.path.join(saveFolderPath, "single_trace_new." + suffix)

        if os.path.exists(saveFilePath):
            curTime = time.strftime("%Y-%m-%d_%H:%M", time.localtime())
            saveFilePath = os.path.join(saveFolderPath, f"single_trace_new{curTime}." + suffix)
        select_index = np.where(self.IS_SELECT_ARRAR == 1)[0]
        conductance_select, distance_select, length, additional_length = self.conductance[select_index], self.distance[
            select_index], self.length[select_index], self.additional_length
        if "npz" == self.save_format:
            np.savez(saveFilePath, distance_array=distance_select, conductance_array=conductance_select,
                     length_array=length, additional_length=additional_length)
        else:
            csv_data = self.get_csv_data(conductance_select, distance_select)
            np.savetxt(saveFilePath, csv_data, delimiter=",")

        logMsg = f"All data has been saved. Path:{self.saveFolderPath}"
        QMessageBox.information(self, "Info", logMsg)

    def get_csv_data(self, conductance_select, distance_select):
        """
        获取csv格式的数据并返回
        :param conductance_select:
        :param distance_select:
        :return:
        """
        rows = conductance_select.shape[0]
        cols = conductance_select.shape[1]
        dataset = np.zeros((rows * 2, cols))
        for i in range(rows):
            dataset[i * 2, :] = distance_select[i, :]
            dataset[i * 2 + 1, :] = conductance_select[i, :]
        return dataset.T

    def get_save_format(self):
        """
        无参数
        :return: 在存储数据前获取存储的格式
        """
        if self.ui.rdo_Format_npz.isChecked():
            self.save_format = "npz"
        else:
            self.save_format = "csv"

    def addErrorMsgWithBox(self, errMsg):
        self.logger.error(errMsg)
        QMessageBox.warning(self, "Warning", errMsg)
        self.add_statusBar_str(errMsg)

    def addErrorMsgNoBox(self, errMsg):
        self.logger.error(errMsg)
        self.add_statusBar_str(errMsg)

    def addLogMsgWithBar(self, logMsg):
        self.logger.debug(logMsg)
        self.add_statusBar_str(logMsg)

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
    basicAnalysisModule = QmySingleTraceAnalysisModule()
    basicAnalysisModule.show()
    sys.exit(app.exec_())
