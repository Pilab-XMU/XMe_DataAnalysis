from multiprocessing import freeze_support
import configparser
import sys
import time
import os
import csv

import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import pyqtSlot, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QVBoxLayout, QFileDialog, QLineEdit, QInputDialog
from scipy.optimize import curve_fit

from gangUtils.generalUtils import GeneralUtils as GeneralUtils
from gangLogger.myLog import MyLog
from ui_QWElectrochemModule import *
from dataProcessing import DataProcessor
from Figure import MyFigureCanvas, MyNavigationToolbar
from ElectrochemConst import BASEDIR



class QmyElectrochemModule(QMainWindow):
    logger = MyLog("QmyElectrochemModule", BASEDIR)
    
    def __init__(self, parent=None):
        super(QmyElectrochemModule, self).__init__(parent)
        self.ui = Ui_QWElectrochemModule()
        self.ui.setupUi(self)
        self.initSet()
        self.checkConfigFile()
        # 初始化控件
        self.initWidget()
        # welcome
        self.addLogMessage("*" * 18 + "Welcome" + "*" * 18, showtime=False)
        logMsg = "Please load the data file first."
        self.addLogMessage(logMsg)
        self.addStatusbarMessage(logMsg)

        self.getPanelPara()
        self.logger.debug("The initial configuration is complete.")
# =========================初始化函数=============================
    def initSet(self):
        self.keyPara = {}
        self.lastOpenPath = BASEDIR # 打开文件夹的初始地址
        self.keyPara["SAVE_DATA_STATUE"] = False
        self.data_p_selected = np.array([])
        self.data_c_selected = np.array([])
        self.current_index = 0
        self.trace_nums = 0
        self.show_ori_2d = True # 默认显示未经筛选的叠加二维图
        self.is_npz = False # 默认不是npz文件
    
    def initWidget(self):
        self.ui.actRun.setEnabled(False)
        self.ui.btn_redraw.setEnabled(False)
        self.ui.btn_select_update.setEnabled(False)
        self.ui.actSaveData.setEnabled(False)
        self.setSelectBtns(False)
        self.initHist2d()
        #TODO 设置文件保存地址
    
    def initHist2d(self):
        """初始化画图区域
        """
        self.fig_2d_layout = QVBoxLayout(self)
        self.fig_2d_canvas = MyFigureCanvas()
        self.fig_2d_toolbar = MyNavigationToolbar(self.fig_2d_canvas, self.fig_2d_canvas.mainFrame)
        self.fig_2d_layout.addWidget(self.fig_2d_canvas)
        self.fig_2d_layout.addWidget(self.fig_2d_toolbar)
        self.ui.grp_2d.setLayout(self.fig_2d_layout)

        # 单条区域
        self.fig_trace_layout = QVBoxLayout(self)
        self.fig_trace_canvas = MyFigureCanvas()
        self.fig_trace_layout.addWidget(self.fig_trace_canvas)
        self.ui.grp_trace.setLayout(self.fig_trace_layout)

# =========================UI: 界面控件触发函数=============================
    @pyqtSlot()
    def on_actOpenFiles_triggered(self):
        dialog_title = "Select tdms file(s)/ npz file"
        filt = "TDMS Files(*.tdms);;npz Files(*.npz)"
        loadStatus = False
        try:
            while not loadStatus:
                file_list, filt_used = QFileDialog.getOpenFileNames(self, dialog_title, self.lastOpenPath, filt)
                loadStatus = len(file_list) > 0
                
                if not loadStatus:
                    result = QMessageBox.warning(self, "Warning", "Please select at least one file!", 
                                                 QMessageBox.Ok | QMessageBox.Cancel,
                                                 QMessageBox.Ok) # 默认按Enter键为Ok
                    if result == QMessageBox.Cancel:
                        break
                    else:
                        continue
                if filt_used == "TDMS Files(*.tdms)":
                #已经获取到各文件路径
                    self.lastOpenPath = os.path.dirname(file_list[0])
                    self.keyPara['FILE_PATHS'] = file_list
                    self.addLogMessage(f"{len(file_list)} files have been loaded:")
                    self.addLogMsglist(file_list)
                    self.addLogMessage("*"*45, showtime=False)
                    self.logger.debug("File loading completed.")
                    self.ui.actRun.setEnabled(True)
                else:
                    file_num = len(file_list)
                    if file_num != 1:
                        result = QMessageBox.warning(self, "Warning", "Please select  one npz file!", 
                                                 QMessageBox.Ok | QMessageBox.Cancel,
                                                 QMessageBox.Ok) # 默认按Enter键为Ok
                        if result == QMessageBox.Cancel:
                            break
                        else:
                            continue
                    self.lastOpenPath = os.path.dirname(file_list[0])
                    self.keyPara['FILE_PATHS'] = file_list
                    self.addLogMessage(f"{len(file_list)} files have been loaded:")
                    self.addLogMsglist(file_list)
                    self.addLogMessage("*"*45, showtime=False)
                    self.logger.debug("File loading completed.")
                    self.ui.actRun.setEnabled(True)
        except Exception as e:
            err_msg = f"DATA FILE LOAD ERROR:{e}"
            self.ui.log.append(err_msg)

    @pyqtSlot()
    def on_actRun_triggered(self):
        try:
            self.ui.actRun.setEnabled(False)
            self.ui.btn_redraw.setEnabled(False)
            self.ui.btn_Last_Trace.setEnabled(False)
            self.ui.btn_Next_Trace.setEnabled(False)
            self.ui.btn_select_update.setEnabled(False)
            self.keyPara["SAVE_DATA_STATUE"] = False
            keyPara = self.getPanelPara()
            if keyPara is None:
                return
            self.keyPara.update(keyPara)
            self.logger.debug(f"Parameters are updated before running. Parameter list:{self.keyPara}")
            self.data_thread = QThread()
            self.data_processor = DataProcessor(self.keyPara)
            self.data_processor.runEnd.connect(lambda: self.stopDataThread(self.data_thread))
            self.data_processor.moveToThread(self.data_thread)
            self.data_thread.started.connect(self.data_processor.run)
            self.data_thread.finished.connect(self.merge)

            self.addLogMessage("Data calculation...")
            self.data_thread.start()
            self.logger.debug(
                    f"Start the data calculation thread--{self.data_thread.currentThread()},Now state:{self.data_thread.isRunning()}")
        except Exception as e:
            err_msg = f"RUN ERROR:{e}"
            self.ui.log.append(err_msg)
    @pyqtSlot()
    def on_btn_redraw_clicked(self):
        self.ui.btn_redraw.setEnabled(False)
        keyPara = self.getDrawSetting()
        if keyPara == None:
            self.ui.btn_redraw.setEnabled(True)
            return
        self.keyPara.update(keyPara)
        self.drawHist(self.data_p_selected, self.data_c_selected)
        self.ui.btn_redraw.setEnabled(True)
    @pyqtSlot()
    def on_btn_Last_Trace_clicked(self):
        self.ui.btn_Last_Trace.setEnabled(False)
        self.current_index = max(0, self.current_index-1)
        self.ui.le_Current_Index.setText(str(self.current_index))
        self.drawTrace()
        self.ui.btn_Next_Trace.setEnabled(True)
        if self.select_state[self.current_index]:
            self.ui.btn_Discard_Trace.setEnabled(True)
            self.ui.btn_Retain_Trace.setEnabled(False)
        else:
            self.ui.btn_Discard_Trace.setEnabled(False)
            self.ui.btn_Retain_Trace.setEnabled(True)
        if self.current_index != 0:
            self.ui.btn_Last_Trace.setEnabled(True)
    @pyqtSlot()
    def on_btn_Next_Trace_clicked(self):
        self.ui.btn_Next_Trace.setEnabled(False)
        self.current_index = min(self.current_index + 1, self.trace_nums- 1)
        self.ui.le_Current_Index.setText(str(self.current_index))
        self.drawTrace()
        self.ui.btn_Last_Trace.setEnabled(True)
        if self.select_state[self.current_index] == True:
            self.ui.btn_Discard_Trace.setEnabled(True)
            self.ui.btn_Retain_Trace.setEnabled(False)
        else:
            self.ui.btn_Discard_Trace.setEnabled(False)
            self.ui.btn_Retain_Trace.setEnabled(True)
        if self.current_index != self.trace_nums - 1:
            self.ui.btn_Next_Trace.setEnabled(True)
    @pyqtSlot()
    def on_actQuit_triggered(self):
        self.close()
    @pyqtSlot()
    def on_actSaveData_triggered(self):
        try:
            is_valid = self.savePreCheck()
            if is_valid:
                self.saveData(self.save_path)
                self.saveFig(self.save_path)
                msg = f"All data has been saved. Path:{self.save_path}"
                self.addLogMsgWithBar(msg)
                QMessageBox.information(self, 'info', msg)
        except Exception as e:
            self.addErrorMsgWithBox(f"SAVE ERROR: {e}")
            return 
    @pyqtSlot()
    def on_btn_Retain_Trace_clicked(self):
        self.select_state[self.current_index] = True
        self.ui.btn_Retain_Trace.setEnabled(False)
        self.ui.btn_Discard_Trace.setEnabled(True)
        self.select_nums = np.sum(self.select_state)
        self.ui.le_Selected_Nums.setText(str(self.select_nums))
        self.drawTrace()
    @pyqtSlot()
    def on_btn_Discard_Trace_clicked(self):
        self.select_state[self.current_index] = False
        self.ui.btn_Retain_Trace.setEnabled(True)
        self.ui.btn_Discard_Trace.setEnabled(False)
        self.select_nums = np.sum(self.select_state)
        self.ui.le_Selected_Nums.setText(str(self.select_nums))
        self.drawTrace()
    @pyqtSlot()
    def on_btn_select_update_clicked(self):
        self.ui.btn_redraw.setEnabled(False)
        self.ui.btn_select_update.setEnabled(False)
        self.setSelectBtns(False)
        keyPara = self.getPanelPara()
        if keyPara is None: # 参数更新失败，此时无需系统状态不变
            self.ui.btn_redraw.setEnabled(True)
            self.ui.btn_select_update.setEnabled(True)
            self.setSelectBtns(True)
            self.logger.debug("参数更新失败")
            return
        self.keyPara.update(keyPara)
        ok = self.dataSelect()
        if ok == False or self.data_p_selected.shape[0] == 0: # 筛选后没有满足条件的数据，为了与状态一致，应该清空绘图区
            self.clearFig()
            self.ui.btn_select_update.setEnabled(True)
            self.ui.actSaveData.setEnabled(True)
            self.addErrorMsgWithBox("There is no valid data. Please modify parameters in Data Select")
            return
        self.drawHist(self.data_p_selected, self.data_c_selected)
        self.trace_nums = self.data_p_selected.shape[0]# 更新单条区域
        self.ui.le_Trace_Nums.setText(str(self.trace_nums))
        self.ui.le_Selected_Nums.setText(str(self.trace_nums)) # 默认全选
        
        # 重置单条索引
        self.current_index = 0
        self.ui.le_Current_Index.setText('0')
        self.drawTrace()
        
        self.ui.btn_redraw.setEnabled(True)
        self.ui.btn_select_update.setEnabled(True)
        self.ui.actSaveData.setEnabled(True)
        
        self.setSelectBtns(True) # 全可用
        self.ui.btn_Last_Trace.setEnabled(False) # 当前在第一条，不能向上
        self.ui.btn_Retain_Trace.setEnabled(False) # 默认全部保存
        if self.current_index + 1 == self.trace_nums: # 只有一条时
            self.ui.btn_Next_Trace.setEnabled(False)
    @pyqtSlot()
    def on_btn_Update_2d_clicked(self):
        self.show_ori_2d = False
        p_data = self.data_p_selected[self.select_state]
        c_data = self.data_c_selected[self.select_state]
        self.drawHist(p_data, c_data)
    @pyqtSlot()
    def on_btn_Restore_2d_clicked(self):
        if self.show_ori_2d == True:
            self.addLogMessage("draw finished")
            return
        self.drawHist(self.data_p_selected, self.data_c_selected)
    @pyqtSlot()
    def on_btn_Select_All_clicked(self):
        self.select_state[:] = True
        self.select_nums = np.sum(self.select_state)
        self.ui.le_Selected_Nums.setText(str(self.select_nums))
        self.drawTrace()
    @pyqtSlot()
    def on_btn_Deselect_All_clicked(self):
        self.select_state[:] = False
        self.select_nums = 0
        self.ui.le_Selected_Nums.setText(str(self.select_nums))
        self.drawTrace()
    @pyqtSlot()
    def on_btn_Invert_Select_clicked(self):
        self.select_state = ~self.select_state
        self.select_nums = np.sum(self.select_state)
        self.ui.le_Selected_Nums.setText(str(self.select_nums))
        self.drawTrace()
    
# =========================事件=============================
    def closeEvent(self, event):
        """重写关闭事件

        Args:
            event (object): 事件对象
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
# =========================UI: Log 通知=============================
    def addLogMessage(self, text, showtime=True):
        """print text in log browser

        Args:
            text (string): content will be shown in log
            showtime (bool, optional): show time or not. Defaults to True.
        """
        try:
            if showtime:
                current = GeneralUtils.getCurrentTime()
                self.ui.log.append(f"[{current}] {text}")
            else:
                self.ui.log.append(text)
        except Exception as e:
            errMsg = f"TEXT BROWSER ERROR:{e}"
            self.logger.error(errMsg)
    def addLogMsglist(self, text_list, showtime=False):
        """print a list of string in log browser

        Args:
            text_list (list[str]): content list will be shown in log
            showtime (bool, optional): show time or not. Defaults to False.
        """
        try:
            if showtime:
                current = GeneralUtils.getCurrentTime()
                self.ui.log.append(current)
            for content in text_list:
                content = content.split('/')[-1]
                self.ui.log.append(f"-- {content}")
        except Exception as e:
            errMsg = f"TEXT LIST BROWSER ERROR:{e}"
            self.logger.error(errMsg)
    def addStatusbarMessage(self, msg):
        """更新状态栏信息

        Args:
            msg (str): 待显示信息
        """
        try:
            self.ui.statusbar.showMessage(":)" + msg)
        except Exception as e:
            errMsg = f"STATUSBAR ERROR{e}"
            self.logger.error(errMsg)
    def addErrorMsgWithBox(self, msg):
        """弹窗警告

        Args:
            msg (str): _description_
        """
        self.logger.error(msg)
        QMessageBox.warning(self, "Warning", msg)
        self.addStatusbarMessage(msg)
        self.addLogMessage(msg)
    def addErrorMsgNoBox(self, errMsg):
        self.logger.error(errMsg)
        self.addStatusbarMessage(errMsg)
        self.addLogMessage(errMsg)
    def addLogMsgWithBar(self, logMsg):
        self.logger.debug(logMsg)
        self.addStatusbarMessage(logMsg)
        self.addLogMessage(logMsg)
# =========================参数加载与保存=============================
    def checkConfigFile(self):
        """
        检查参数文件
        :return:
        """
        configPath = os.path.join(BASEDIR, "config.ini")
        if os.path.exists(configPath):
            dlgTitle = "Info"
            strInfo = "Config file detected. Load it?"
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
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_basic_setting, self.ui.grp_draw_setting, self.ui.grp_model_conductance]

            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in le_obj_list:
                obj.setText(config.get(section_name, obj.objectName()))
            # 加载电位模式
            potential_mode = int(config.get(section_name, 'potential_mode'))
            if potential_mode == 0:
                self.ui.rdo_potential_default.setChecked(True)
            elif potential_mode == 1:
                self.ui.rdo_potential_increase.setChecked(True)
            else:
                self.ui.rdo_potential_decrease.setChecked(True)
            # 加载电导模式
            conductance_mode = int(config.get(section_name, 'conductance_mode'))
            if conductance_mode == 0:
                self.ui.rdo_conductance_default.setChecked(True)
            elif conductance_mode == 1:
                self.ui.rdo_conductance_increase.setChecked(True)
            else:
                self.ui.rdo_conductance_decrease.setChecked(True)
            
            logMsg = "History parameters have been loaded"
            self.addLogMsgWithBar(logMsg)
        except Exception as e:
            errMsg = f"GTE OLD PARA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
    def getSameWidget(self, widget, targetWdt):
        """获取widget中的所有targetWdt

        Args:
            widget (obj): 父控件
            targetWdt (obj): 待搜索对象

        Returns:
            list(obj): 目标子控件数组
        """
        return widget.findChildren(targetWdt)
    def getPanelPara(self):
        keyPara = {}
        try:
            le_obj_list = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_basic_setting, self.ui.grp_draw_setting, self.ui.grp_model_conductance]
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in le_obj_list:
                keyPara[obj.objectName()] = float(obj.text())
            self.getPotentialMode()
            self.getConductanceMode()
        except Exception as e:
            errMsg = f"GTE PANEL PARA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            return None
        else:
            return keyPara
    def saveConfigPara(self):
        """保存参数文件
        """
        try:
            config = configparser.ConfigParser()
            config.optionxform = str
            section_name = "PANEL_PARA"
            config.add_section(section_name)
            le_obj_list = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_basic_setting, self.ui.grp_draw_setting, self.ui.grp_model_conductance]
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in le_obj_list:
                config.set(section_name, obj.objectName(), obj.text())
            config.set(section_name, 'potential_mode', str(self.potential_mode))
            config.set(section_name, 'conductance_mode', str(self.conductance_mode))
            config_path = os.path.join(BASEDIR, 'config.ini')
            with open(config_path, mode='w', encoding='utf-8') as f:
                config.write(f)
            self.logger.debug('Parameters have been saved.')
        except Exception as e:
            self.addErrorMsgWithBox(f'PARAMETERS SAVE ERROR:{e}')
            return
    def getDrawSetting(self):
        keyPara = {}
        try:
            le_obj_list = self.getSameWidget(self.ui.grp_draw_setting, QLineEdit)
            for obj in le_obj_list:
                keyPara[obj.objectName()] = float(obj.text())
        except Exception as e:
            errMsg = f"READ DRAW SETTING ERROR: {e}"
            self.addErrorMsgWithBox(errMsg)
            return None
        else:
            return keyPara
    def getPotentialMode(self):
        if self.ui.rdo_potential_default.isChecked():
            self.potential_mode = 0
        elif self.ui.rdo_potential_increase.isChecked():
            self.potential_mode = 1
        elif self.ui.rdo_potential_decrease.isChecked():
            self.potential_mode = 2
    def getConductanceMode(self):
        if self.ui.rdo_conductance_increase.isChecked():
            self.conductance_mode = 1
        elif self.ui.rdo_conductance_decrease.isChecked():
            self.conductance_mode = 2
        else:
            self.conductance_mode = 0

# =========================画图=============================
    def drawPre(self): # 重新运行后绘图
        ok = self.dataSelect() #数据筛选, 模人全选
        self.max_vol = np.max(np.concatenate(self.data_p_selected))
        self.min_vol = np.min(np.concatenate(self.data_p_selected))
        if ok == True and self.data_p_selected.shape[0] != 0:
            self.drawHist(self.data_p_selected, self.data_c_selected)
            self.trace_nums = len(self.data_p_selected)
            self.ui.le_Trace_Nums.setText(str(self.trace_nums))
            # 重置单条索引
            self.current_index = 0
            self.ui.le_Current_Index.setText('0')
            self.ui.le_Selected_Nums.setText(str(self.select_nums))
            self.drawTrace()
        else:
            self.addErrorMsgWithBox("There is no valid data. Please modify parameters in Data Select")
            self.clearFig()
            self.ui.actRun.setEnabled(True)
            self.ui.btn_select_update.setEnabled(True)
            return
        self.ui.btn_redraw.setEnabled(True)
        self.ui.actSaveData.setEnabled(True)
        self.ui.actRun.setEnabled(True)
        self.ui.btn_select_update.setEnabled(True)
        # 单条筛选区按钮
        self.setSelectBtns(True) # 全可用
        self.ui.btn_Last_Trace.setEnabled(False) # 当前在第一条，不能向上
        self.ui.btn_Retain_Trace.setEnabled(False) # 默认全部保存
        if self.current_index + 1 == self.trace_nums: # 只有一条时
            self.ui.btn_Next_Trace.setEnabled(False)
    def drawHist(self, p_list, c_list):
        if (p_list.shape[0] == 1):
            p_list = p_list.astype(np.float64)
            c_list = c_list.astype(np.float64)
        p_flat = np.concatenate(p_list, dtype=np.float64)
        c_flat = np.concatenate(c_list, dtype=np.float64)
        BINSX = int(self.keyPara["le_BinsX"])
        BINSY = int(self.keyPara["le_BinsY"])
        MINX = self.keyPara['le_MinX']
        MAXX = self.keyPara['le_MaxX']
        MINY = self.keyPara['le_MinY']
        MAXY = self.keyPara['le_MaxY']

        # 绘图
        self.fig_2d_canvas.fig.clear()
        ax = self.fig_2d_canvas.fig.add_subplot()
        self.h, xedges, yedges, colorbar = ax.hist2d(x = p_flat, y = c_flat, 
            bins=[BINSX, BINSY], 
            range=[[MINX, MAXX], [MINY, MAXY]],
            cmap = plt.cm.get_cmap('Purples'))
        ax.set_title("2d") #TODO 后续会改
        ax.set_xlabel('Potential vs Ag/AgCl / V')
        ax.set_ylabel('Conductacne / Log(G/G0)')
        ax.set_xlim(self.keyPara['le_Xlim0'], self.keyPara['le_Xlim1'])
        ax.set_ylim(self.keyPara['le_Ylim0'], self.keyPara['le_Ylim1'])
        self.fig_2d_canvas.fig.colorbar(colorbar, ax=ax)
        self.x_fit, self.y_fit = self.getGaussFit(self.h, xedges, yedges)
        ax.plot(self.x_fit, self.y_fit, 'red')
        
        self.fig_2d_canvas.fig.tight_layout()
        self.fig_2d_canvas.draw()
        self.fig_2d_canvas.flush_events()
        self.addLogMessage("draw finished")
        self.keyPara["SAVE_DATA_STATUE"] = True
    def drawTrace(self):
        self.fig_trace_canvas.fig.clear()
        idx = self.current_index
        x = self.data_p_selected[idx]
        y = self.data_c_selected[idx]
        ax = self.fig_trace_canvas.fig.add_subplot()
        
        increase_index = np.where(np.diff(x, prepend=x[0]) > 0)[0]
        if len(increase_index) > 0:
            ax.plot(x[increase_index], y[increase_index], color='red', lw=1.5, label='v-increase')
        decrease_index = np.where(np.diff(x, prepend=x[0]) < 0)[0]
        if len(decrease_index) > 0:
            ax.plot(x[decrease_index], y[decrease_index], color='blue', lw=1.5, label='v-decrease')
        if self.select_state[self.current_index] == True:
            ax.set_title('retain: true')
        else:
            ax.set_title('retain: false')
        ax.set_xlabel('Potential vs Ag/AgCl / V')
        ax.set_ylabel('Conductacne / Log(G/G0)')
        ax.set_xlim((self.min_vol-0.1, self.max_vol+0.1))
        ax.legend()
        self.fig_trace_canvas.fig.tight_layout()
        self.fig_trace_canvas.draw()
        self.fig_trace_canvas.flush_events()
    def getGaussFit(self, h, xedges, yedges):
        xTicks = (xedges[1:] + xedges[:-1]) / 2
        x = (yedges[1:] + yedges[:-1]) / 2
        yTicks = np.apply_along_axis(self.gaussFit, 1, h, x)
        return xTicks, yTicks
    def gaussFit(self, y_data, x):
        MING, MAXG = self.keyPara['le_MinY'], self.keyPara['le_MaxY']
        length = len(y_data)
        def gaussian(x, amp, cen, wid):
            return (amp / (np.sqrt(2 * np.pi) * wid)) * np.exp(-(x - cen) ** 2 / (2 * wid ** 2))
        if not np.any(y_data):
            mu = 0
            return MING + (MAXG-MING) * mu / length
        else:
            try:
                mu = curve_fit(gaussian, x, y_data)[0][1]
                if (mu > MAXG) or (mu < MING):
                    mu = np.mean(np.where(y_data == np.max(y_data))[0])
                    return MING + (MAXG-MING) * mu / length
                else:
                    return mu
            except Exception as e:
                mu = np.mean(np.where(y_data == np.max(y_data))[0])
                return MING + (MAXG-MING) * mu / length
            
# =========================数据过滤=============================
    def stopDataThread(self, thread):
        try:
            thread.quit()
            thread.wait()
            self.logger.debug(f"Exit {thread.currentThread()} thread，Now state:{thread.isRunning()}")
        except Exception as e:
            errMsg = f"THREAD EXIT ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
    def merge(self):
        # 数据处理线程已经退出, 开始合并多个数据
        is_valid = self.data_processor.postPorcessing() # 合并多个文件的数据
        if not is_valid:
            self.addErrorMsgWithBox("There is no valid data. Please modify parameters in BasicSetting.")
            self.ui.actRun.setEnabled(True)
            return
        self.logger.debug("The computing process exits safely and begins computing drawing data")
        self.addLogMessage("data read finished")
        
        # 合并后绘图
        self.drawPre()
        
        
    def dataSelect(self):
        try:
            p_list, c_list = self.data_processor.datasets['potential'], self.data_processor.datasets['conductance']
            p_list, c_list = self.dataSelectByPotential(p_list, c_list, self.potential_mode)
            if p_list is None:
                self.data_p_selected, self.data_c_selected = np.array([]), np.array([])
                return False
            p_list, c_list = self.dataSelectByCondValue(p_list, c_list)
            if p_list is None:
                self.data_p_selected, self.data_c_selected = np.array([]), np.array([])
                return False
            p_list, c_list = self.dataSelectByCondTrend(p_list, c_list, self.conductance_mode)
            if p_list is None:
                self.data_p_selected, self.data_c_selected = np.array([]), np.array([])
                return False
            self.data_p_selected, self.data_c_selected = p_list, c_list
            # 设置选择状态
            self.select_state = np.array([True] * len(self.data_p_selected))
            self.select_nums = self.select_state.shape[0]
            return True
        except Exception as e:
            self.logger.debug(f"data select error:{e}")
            return False
    def dataSelectByPotential(self, p_list, c_list, mode):
        try:
            p_res = [] #电位
            c_res = [] #电导
            if mode == 0: # 不筛选
                return p_list, c_list
            elif mode == 1: # 电位递增区间
                for p, c in zip(p_list, c_list):
                    increase_index = np.where(np.diff(p, prepend=p[0]) > 0)[0]
                    if len(increase_index) > 0:
                        p_res.append(p[increase_index])
                        c_res.append(c[increase_index])
            elif mode == 2: # 电位递减区间
                for p, c in zip(p_list, c_list):
                    decrease_index = np.where(np.diff(p, prepend=p[0]) < 0)[0]
                    if len(decrease_index) > 0:
                        p_res.append(p[decrease_index])
                        c_res.append(c[decrease_index])
            p_res, c_res = np.array(p_res, dtype='object'), np.array(c_res, dtype='object')
            if p_res.ndim == 2:
                p_res, c_res = p_res.astype(np.float64), c_res.astype(np.float64)
        except Exception as e:
            err_msg = f"POTENTIAL FILTER ERROR: {e}"
            self.addErrorMsgNoBox(err_msg)
            return None, None
        else:
            return p_res, c_res
    def dataSelectByCondValue(self, p_list, c_list):
        try:
            true_index = np.array([False] * len(c_list))
            start_max = self.keyPara['le_cond_start_up']
            start_min = self.keyPara['le_cond_start_low']
            end_max = self.keyPara['le_cond_end_up']
            end_min = self.keyPara['le_cond_end_low']
            for i, c in enumerate(c_list):
                c_start = np.mean(c[:10])
                c_end = np.mean(c[-10:])
                if (c_start <= start_max) and (c_start >= start_min) and (c_end <= end_max) and (c_end > end_min):
                    true_index[i] = True
            return p_list[true_index], c_list[true_index]
        except Exception as e:
            err_msg = f"data select by conductance value error : {e}"
            self.addErrorMsgNoBox(err_msg)
            return None, None   
    def dataSelectByCondTrend(self, p_list, c_list, mode):
        try:
            true_index = np.array([False] * len(c_list))
            if mode == 0:
                return p_list, c_list
            elif mode == 1: # 电导递增
                for i, c in enumerate(c_list):
                    c_begin = np.mean(c[:10]) 
                    c_end = np.mean(c[-10:]) # TODO 由于电位是上升在下降的，电导直接取末尾似乎不合适
                    if c_begin <= c_end:
                        true_index[i] = True
            elif mode == 2: # 电导递减
                for i, c in enumerate(c_list):
                    c_begin = np.mean(c[:10])
                    c_end = np.mean(c[-10:])
                    if c_begin >= c_end:
                        true_index[i] = True
            return p_list[true_index], c_list[true_index]
        except Exception as e:
            err_msg = f"Conductance trend filter error: {e}"
            self.addErrorMsgNoBox(err_msg)
            return None, None
# =========================保存数据与图片=============================   
    def savePreCheck(self):
        if not self.keyPara['SAVE_DATA_STATUE']:
            self.addErrorMsgWithBox("The data cannot be saved until the data processing is complete!")
            return False
        if self.data_p_selected.shape[0] == 0:
            self.addErrorMsgWithBox("There is no valid to save.")
            return False
        try:
            title = "选择目标文件夹, 将会在该文件夹下创建result目录"
            cur_path = BASEDIR
            dir_selected = QFileDialog.getExistingDirectory(self, title, cur_path, QFileDialog.ShowDirsOnly)
            if dir_selected == "":
                return False
            dlgTitle = "Folder name Settings"
            txtLabel = "Please enter the name of the folder to save"
            defaultName = "ElectroChemAnalysis"
            echoMode = QLineEdit.Normal
            flag = False
            while not flag:
                save_name, OK = QInputDialog.getText(self, dlgTitle, txtLabel, echoMode, defaultName)
                if OK:
                    save_path = dir_selected + '/' + save_name
                    IS_EXIST = os.path.exists(save_path)
                    if IS_EXIST:
                        errMsg = "The folder name already exists or is invalid,Please re-enter"
                        self.addErrorMsgWithBox(errMsg)
                        continue
                    else:
                        flag = not flag
                        self.save_path = save_path
                        os.mkdir(self.save_path)
                else:
                    logMsg = "Unsave data"
                    self.addLogMsgWithBar(logMsg)
                    return False
            return True
        except Exception as e:
            self.addErrorMsgWithBox(f"folder create fail: {e}")
            return False
    def saveData(self, path):
        hist_path = os.path.join(path, 'hist2d.txt')
        np.savetxt(hist_path, self.h, fmt='%d', delimiter='\t')
        fit_path = os.path.join(path, 'gaussianfit.txt')
        np.savetxt(fit_path, np.array([self.x_fit, self.y_fit]), fmt='%.5f', delimiter='\t')
        # 保存筛选后的数据
        npz_path = os.path.join(path, 'traces_select.npz')
        np.savez(npz_path, x=self.data_p_selected[self.select_state], y=self.data_c_selected[self.select_state])
        # 保存未筛选的数据
        np.savez(os.path.join(path, 'traces_origin.npz'), x = self.data_p_selected, y = self.data_c_selected, index = self.select_state)
        if np.sum(self.select_state == True) == 0:
            return
        trace_path = os.path.join(path, 'traces.csv')
        p_data = self.data_p_selected[self.select_state]
        c_data = self.data_c_selected[self.select_state]
        max_len = np.max([len(p) for p in p_data])
        X = np.array([np.pad(p, (0, max_len - len(p)), mode='constant', constant_values=np.nan) for p in p_data])
        Y = np.array([np.pad(p, (0, max_len - len(p)), mode='constant', constant_values=np.nan) for p in c_data])
        all = np.hstack([X, Y])
        all = all.reshape((-1, max_len))
        all = all.T
        np.savetxt(trace_path, all, delimiter=',', fmt='%.5f')
        # with open(trace_path, 'w', newline='', encoding='utf-8') as f:
        #     writer = csv.writer(f)
        #     for p, c in zip(p_data, c_data):
        #         writer.writerow(p)
        #         writer.writerow(c)
    def saveFig(self, path):
        fig_path = os.path.join(path, 'hist2d.png')
        self.fig_2d_canvas.fig.savefig(fig_path, dpi=100, bbox_inches='tight')
    def clearFig(self):
        self.keyPara["SAVE_DATA_STATUE"] = False
        self.fig_2d_canvas.fig.clear()
        self.fig_2d_canvas.draw()
        self.fig_2d_canvas.flush_events()
        self.fig_trace_canvas.fig.clear()
        self.fig_trace_canvas.draw()
        self.fig_trace_canvas.flush_events()
        self.ui.le_Trace_Nums.setText('0')
        self.ui.le_Current_Index.setText('0')
        self.current_index = 0
        self.trace_nums = 0
        self.ui.btn_Next_Trace.setEnabled(False)
        self.ui.btn_Last_Trace.setEnabled(False)
        self.ui.btn_Discard_Trace.setEnabled(False)
        self.ui.btn_Retain_Trace.setEnabled(False)
# ==============================辅助函数===============================
    def setSelectBtns(self, state):
        self.ui.btn_Last_Trace.setEnabled(state)
        self.ui.btn_Next_Trace.setEnabled(state)
        self.ui.btn_Retain_Trace.setEnabled(state)
        self.ui.btn_Discard_Trace.setEnabled(state)
        self.ui.btn_Update_2d.setEnabled(state)
        self.ui.btn_Restore_2d.setEnabled(state)
        self.ui.btn_Select_All.setEnabled(state)
        self.ui.btn_Deselect_All.setEnabled(state)
        self.ui.btn_Invert_Select.setEnabled(state)
        
if __name__ == '__main__':
    freeze_support()
    # 这行是为了解决多进程的问题
    app = QApplication(sys.argv)
    electrochemModule = QmyElectrochemModule()
    electrochemModule.show()
    sys.exit(app.exec_())