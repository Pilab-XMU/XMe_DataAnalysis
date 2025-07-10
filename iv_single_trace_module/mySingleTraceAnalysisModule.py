
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
        self.have_data = False
        self.have_cond_for_rev = False
        self.have_cond = False

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
        self.view = 0
        self.show_cond = self.ui.ckBox_View_Cond.isChecked()
        self.show_curr = self.ui.ckBox_View_Current.isChecked()
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
            saveRootDir = os.path.dirname(filePath)
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
                    if self.TRACE_NUM != 0:
                        self.have_data = True
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
                    else:
                        self.addErrorMsgWithBox("File is empty.")
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
    def on_rdo_View_All_clicked(self):
        self.view = 0
        if self.have_data:
            self.draw_fig()
    @pyqtSlot()
    def on_rdo_View_Forward_clicked(self):
        self.view = 1
        if self.have_data:
            self.draw_fig()
    @pyqtSlot()
    def on_rdo_View_Reverse_clicked(self):
        self.view = 2
        if self.have_data:
            self.draw_fig()
    
    @pyqtSlot(int)
    def on_ckBox_View_Cond_stateChanged(self, state):
        if state == 0 and not self.ui.ckBox_View_Current.isChecked():
            QMessageBox.warning(self, "Warning", "Select at least one data channel!")
            self.ui.ckBox_View_Cond.setChecked(True)
            return
        self.show_cond = state == 2
        if self.have_data:
            self.draw_fig()
    @pyqtSlot(int)
    def on_ckBox_View_Current_stateChanged(self, state):
        if state == 0 and not self.ui.ckBox_View_Cond.isChecked():
            QMessageBox.warning(self, "Warning", "Select at least one data channel!")
            self.ui.ckBox_View_Current.setChecked(True)
            return
        print("Current checkbox")
        self.show_curr = state == 2
        if self.have_data:
            self.draw_fig()
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
        dataset = np.load(file_path, allow_pickle=True)
        self.v_for = dataset['v_for']
        self.v_rev =  dataset["v_rev"]
        # 为了填之前的坑
        if 'c_for' in dataset.files:
            self.c_for = dataset['c_for']
            self.c_rev = dataset['c_rev']
        elif 'i_for' in dataset.files:
            self.c_for = dataset['i_for']
            self.c_rev = dataset['i_rev']
            
        if 'cond_for' in dataset.files:
            self.cond_for = dataset['cond_for']
            self.cond_rev = dataset['cond_rev']
            self.have_cond_for_rev = True
        else:
            self.ui.ckBox_View_Cond.setDisabled(True)
            self.show_cond = False
            
        if 'cond' in dataset.files:
            self.condData = dataset['cond']
            self.have_cond = True
            
        self.TRACE_NUM = len(self.c_for)
        self.IS_SELECT_ARRAR = np.zeros(self.TRACE_NUM, dtype=int)
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
        c_for, v_for = self.c_for[self.CURRENT_INDEX], self.v_for[self.CURRENT_INDEX]
        c_rev, v_rev = self.c_rev[self.CURRENT_INDEX], self.v_rev[self.CURRENT_INDEX]
        ax1 = self.fig.add_subplot()
        if self.show_curr:
            if self.view == 0:
                ax1.plot(v_for, c_for, c='r',label='forward_v')
                ax1.plot(v_rev, c_rev, c='b',label='reverse_v')
            elif self.view == 1:
                ax1.plot(v_for, c_for, c='r',label='forward_v')
            else:
                ax1.plot(v_rev, c_rev, c='b',label='reverse_v')
            ax1.legend(loc='lower left')
        ax1.set_xlabel('Voltage/V')
        ax1.set_ylabel('Current/nA (logI)')
        
        ax2 = ax1.twinx()
        ax2.set_ylabel(r"log${G/G_0}$")
        if self.show_cond:
            cond_for = self.cond_for[self.CURRENT_INDEX]
            cond_rev = self.cond_rev[self.CURRENT_INDEX]
            alpha = 0.5 if self.show_curr else 1
            ax2.plot(v_for, cond_for, alpha=alpha, label='forward_g')
            ax2.plot(v_rev, cond_rev, alpha=alpha, label='reverse_g')
            ax2.legend(loc="lower right")
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

        select_index = np.where(self.IS_SELECT_ARRAR == 1)[0]
        
        if "npz" == self.save_format:
            saveFilePath = os.path.join(saveFolderPath, "single_trace_new." + suffix)
            if os.path.exists(saveFilePath):
                curTime = time.strftime("%Y-%m-%d_%H:%M", time.localtime())
                saveFilePath = os.path.join(saveFolderPath, f"single_trace_new{curTime}." + suffix)
            c_for, v_for = self.c_for[select_index], self.v_for[select_index]
            c_rev, v_rev = self.c_rev[select_index], self.v_rev[select_index]
            
            save_dict = {
                "v_for" : v_for,
                "v_rev" : v_rev,
                "c_for" : c_for,
                "c_rev" : c_rev,
            }
            if self.have_cond_for_rev:
                save_dict["cond_for"] = self.cond_for[select_index]
                save_dict["cond_rev"] = self.cond_rev[select_index]
            if self.have_cond:
                save_dict["cond"] = self.condData[select_index]
            
            np.savez(saveFilePath, **save_dict)
        else:
            header = "v_for, i_for,logG_for,v_rev,i_rev,logG_rev"
            for i, idx in enumerate(select_index):
                c_for, v_for = self.c_for[idx], self.v_for[idx]
                c_rev, v_rev = self.c_rev[idx], self.v_rev[idx]
                if self.have_cond_for_rev:
                    cond_for = self.cond_for[idx]
                    cond_rev = self.cond_rev[idx]
                else:
                    cond_for = np.full(len(c_for), np.nan)
                    cond_rev = np.full(len(c_rev), np.nan)
                
                if len(v_for) > len(v_rev):
                    delta = len(v_for) - len(v_rev)
                    v_rev = np.pad(v_rev, (0, delta), constant_values=np.nan)
                    c_rev = np.pad(c_rev, (0, delta), constant_values=np.nan)
                    cond_rev = np.pad(cond_rev, (0, delta), constant_values=np.nan)
                elif len(v_rev) > len(v_for):
                    delta = len(v_rev) - len(v_for)
                    v_for = np.pad(v_for, (0, delta), constant_values=np.nan)
                    c_for = np.pad(c_for, (0, delta), constant_values=np.nan)
                    cond_for = np.pad(cond_for, (0, delta), constant_values=np.nan)
                
                result = np.column_stack([v_for, c_for, cond_for, v_rev, c_rev, cond_rev])
                np.savetxt(os.path.join(saveFolderPath, f'{idx}.txt'), result, fmt='%.5f', 
                           delimiter=',', header=header, comments="")
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
