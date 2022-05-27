# -*- coding: utf-8 -*-
# @Time   : 2020/11/11 15:33
# @Author : Gang
# @File   : myBasicAnalysisModule.py
from multiprocessing import freeze_support
import sys
# import os
# if hasattr(sys, 'frozen'):
#     os.environ['PATH'] = sys._MEIPASS + ";" + os.environ['PATH']
# 这两行是为了解决拷贝到别人电脑不能用的bug
import configparser
import matplotlib.pyplot as plt
from scipy.stats import norm
import copy

from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QLineEdit, QVBoxLayout, QInputDialog
from PyQt5.QtCore import pyqtSlot, QThread
from dataAnalysis import DataAnalysis
from calDrawData import CalDrawData
from saveAllData import SaveAllData
from myFigure import *
from dataProcessUtils import *

from ui_QWBasicAnalysisModule import Ui_QWBasicAnalysisModule
from myAboutWidget import QmyAbout
from gangLogger.myLog import MyLog
from gangUtils.generalUtils import GeneralUtils
from basicAnalysisConst import *


# TODO 下一步开发计划：
# 2. 绘图的时候每次都要创建一个对象，我认为很麻烦，可参考教程的方法，初始化-》循环绘图 这里需要参照其他功能模块的方法，循环绘图，不要每次都创建对象  done!!!!!
# 3. 另外一维长度的高斯拟合可以参照禄椿师兄的高斯拟合方法
# 4. 把selectdir 改成save dir!!!!  done
# 5. redraw功能再逻辑上还是有点问题的，在运行程序的过程中，应该是不能点击这个button
#    的，所以在此处应该对其权限进行修改！！！   done!!!
# 6. 致命错误：conductance拼写错误，应该是conductance


class QmyBasicAnalysisModule(QMainWindow):
    logger = MyLog("BasicAnalysis", BASEDIR)

    # 为什么这里设计成类变量？？避免静态方法出现的时候，用不了了！

    def __init__(self):
        super().__init__()
        self.ui = Ui_QWBasicAnalysisModule()
        self.ui.setupUi(self)
        self.key_para = {}  # 页面关键参数dict
        self.init_set()  # 初始化设置

    def init_set(self):
        self.key_para["SaveData_Statue"] = False  # 此参数标志是否可以进行数据保存的工作，应当在得到绘图数据之后设置为True，并且在每点击一次run之后设置为False
        self.key_para["Data_Save_Path"] = ""
        self.init_widget()
        self.createFigure()

    def init_widget(self):
        self.add_textBrowser_str("*" * 26 + "Welcome" + "*" * 26, showtime=False)
        logMsg = "Please load the data file first."
        self.add_textBrowser_str(logMsg)
        self.add_statusBar_str(logMsg)

        self._2DCondLayout = QVBoxLayout(self)
        self._1DCondLayout = QVBoxLayout(self)
        self._1DLengthLayout = QVBoxLayout(self)

        self.init_save_dir()
        self.check_config()

        self.ui.actRun.setEnabled(False)
        self.ui.actStop.setEnabled(False)
        self.ui.btn_Redraw.setEnabled(False)  # 重画按钮，应当在绘图成功后设置为可触发
        self.ui.btn_Update.setEnabled(False)  # 更新additional-length按钮，应当在绘图成功后设置为可触发
        # self.ui.btn_SaveResult.setEnabled(
        #     self.check_savedir_statue())  # 保存图片及对应作图文件按钮，初次使用应该是false，后面继续使用，应该会用config中自动设置上次的路径，所以应该加一个判断函数

        self.logger.debug("The initial configuration is complete.")

    # =============== 控件触发函数===============
    @pyqtSlot()
    def on_actAbout_triggered(self):
        self.aboutUi = QmyAbout()
        self.aboutUi.show()

    @pyqtSlot()
    def on_actOpenFiles_triggered(self):
        """
        选择文件act
        :return:
        """
        try:
            dlg_title = "Select multiple files"  # 对话框标题
            filt = "TDMS Files(*.tdms)"  # 文件过滤器
            desktop_path = GeneralUtils.getDesktopPath()
            load_statue = False
            while not load_statue:
                file_list, filt_used = QFileDialog.getOpenFileNames(self, dlg_title, desktop_path, filt)

                load_statue = self.set_load_state(file_list)
                if not load_statue:
                    result = QMessageBox.warning(self, "Warning", "Please select at least one file!",
                                                 QMessageBox.Ok | QMessageBox.Cancel,
                                                 QMessageBox.Ok)
                    if result == QMessageBox.Cancel:
                        break
                else:
                    self.key_para['FILE_PATHS'] = file_list
                    self.add_textBrowser_str(f"{len(file_list)} files have been loaded:")
                    self.add_textBrowser_list(file_list)
                    self.add_textBrowser_str("*" * 60, showtime=False)
                    # 加载文件成功之后，应当对运行按钮进行释放
                    self.ui.actRun.setEnabled(True)
                    self.logger.debug("File loading completed.")
        except Exception as e:
            errMsg = f"DATA FILE LOAD ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_actQuit_triggered(self):
        """
        这个就离谱，我只是调用了close函数，为什么又调用了我重写的closeevent？？？？
        :return:
        """
        # todo 需要想明白！！！这里虽然功能没问题，但是这是为什么呢？？？
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
            self.save_config_para()
            self.add_statusBar_str("Parameter saving...")
            time.sleep(0.1)
            self.logger.debug("Program exits")
            event.accept()
        else:
            event.ignore()

    @pyqtSlot()
    def on_actRun_triggered(self):
        """
        运行按钮
        :return: 无返回值
        """
        try:
            self.ui.actRun.setEnabled(False)  # 这里需要注意的是点击一次run 控件之后，应当设置未为不可选，
            self.ui.btn_Redraw.setEnabled(False)
            self.key_para["SaveData_Statue"] = False

            keyPara = self.get_panel_para()
            if keyPara is None:
                return
            else:
                self.key_para.update(keyPara)  # 运行前应该得到面板参数，返回dict，并更新self.key_para
                self.logger.debug(f"Parameters are updated before running. Parameter list:{self.key_para}")

                self._data_thread = QThread()
                self.data_analysis = DataAnalysis(self.key_para)
                self.data_analysis.pbar.connect(self.set_progressBar_int)
                self.data_analysis.tbw.connect(self.add_textBrowser_str)
                self.data_analysis.sbar.connect(self.add_statusBar_str)
                self.data_analysis.run_end.connect(lambda: self.stop_thread(self._data_thread))

                self.data_analysis.moveToThread(self._data_thread)
                self._data_thread.started.connect(self.data_analysis.run)
                self._data_thread.finished.connect(self.draw_prepare)

                logMsg = "Data calculation..."
                self.addLogMsgWithBar(logMsg)

                self._data_thread.start()

                self.logger.debug(
                    f"Start the data calculation thread--{self._data_thread.currentThread()},Now state:{self._data_thread.isRunning()}")
        except Exception as e:
            errMsg = f"RUN ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_actGuideSet_triggered(self):
        # TODO
        #  参数设置指南QAction，这里应当弹出一个Dialog给出提示，此处不重要，最后再添加
        pass

    @pyqtSlot(int)
    def on_cmb_Device_currentIndexChanged(self, index):
        """
        仪器设备combox，此处响应参数为int，我想int应该比string快一点哈哈
        :param index: 对应的combox改变时的选项序号
        :return: 无返回值
        """
        self.key_para["DEVICE_ID"] = index
        """
        设备id号对应的设备名
        DEVICE_ID    DEVICE_NAME
            0           stm41
            1           stm40
            2           mcbj41
            3           stm_new
        """

    @pyqtSlot(int)
    def on_cmb_Process_currentIndexChanged(self, index):
        """
        分析过程combox，对应的过程发生改变
        :param index: 对应的combox改变时的选项序号
        :return: 无
        """
        self.key_para["PROCESS"] = index
        """
        0   open
        1   close
        """

    @pyqtSlot()
    def on_btn_Update_clicked(self):
        # TODO 点击两次会有bug
        self.key_para["SaveData_Statue"] = False
        self.key_para["le_Additional_Length"] = int(self.ui.le_Additional_Length.text())  # 更新additional length
        ADDITIONAL_LENGTH = self.key_para["le_Additional_Length"]
        # 这里需要注意的是，dataset是一个list，因为使用了多进程！！！
        if self.key_para["PROCESS"] == 0:
            for data in self.dataset:
                data[3] = data[1] + ADDITIONAL_LENGTH
        else:
            for data in self.dataset:
                data[1] = data[3] - ADDITIONAL_LENGTH
        self.cal_draw()

    @pyqtSlot()
    def on_btn_Redraw_clicked(self):
        try:
            self.key_para["SaveData_Statue"] = False
            # 此处应该只更新绘图部分的关键参数就可以了吧
            key_para = {}
            obj_draw_para_list = self.get_same_widget(self.ui.toolBox, QLineEdit)
            for obj in obj_draw_para_list:
                key_para[obj.objectName()] = float(obj.text())
            self.key_para.update(key_para)
            self.draw(self.distance_draw, self.conductance_draw, self.length)
        except Exception as e:
            errMsg = f"REDRAW ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            self.set_progressBar_int(0)
            self.ui.actRun.setEnabled(True)
            del self.dataset
            del self.draw_dataset

    @pyqtSlot()
    def on_btn_Reset_clicked(self):
        self.ui.le_Sampling_Rate.setText("20000")
        self.ui.le_Piezo_Rate.setText("1")
        self.ui.le_Stretching_Rate.setText("10")
        self.ui.le_BiasV.setText("0.1")
        self.ui.le_High_Cut.setText("1.2")
        self.ui.le_High_Length.setText("-0.3")
        self.ui.le_Low_Length.setText("-6")
        self.ui.le_Zero_Set.setText("-0.3")
        self.ui.le_Jump_Gap.setText("10000")
        # ===============================================================================================
        self.ui.le_2D_BinsX.setText("500")
        self.ui.le_2D_BinsY.setText("800")
        self.ui.le_2D_Xleft.setText("-0.2")
        self.ui.le_2D_Xright.setText("1.5")
        self.ui.le_2D_Yleft.setText("-7")
        self.ui.le_2D_Yright.setText("1.5")
        self.ui.le_1D_Cond_Xleft.setText("-7")
        self.ui.le_1D_Cond_Xright.setText("1.5")
        self.ui.le_1D_Cond_Bins.setText("800")
        self.ui.le_1D_Leng_Xleft.setText("0")
        self.ui.le_1D_Leng_Xright.setText("1.5")
        self.ui.le_1D_Leng_Bins.setText("100")
        # ===============================================================================================
        self.ui.le_Additional_Length.setText("3000")
        desktop_path = GeneralUtils.getDesktopPath()
        self.ui.le_Data_Save_Dir.setText(desktop_path)
        # ===============================================================================================
        self.ui.le_Start1.setText("-2")
        self.ui.le_Start2.setText("-4")
        self.ui.le_End1.setText("-3")
        self.ui.le_End2.setText("-6")
        self.ui.le_Low_Limit1.setText("-55")
        self.ui.le_Low_Limit2.setText("-55")
        self.ui.le_Upper_Limit1.setText("55")
        self.ui.le_Upper_Limit2.setText("55")
        # ===============================================================================================
        self.ui.le_STM41_a1.setText("-9.2694")
        self.ui.le_STM41_b1.setText("-26.0147")
        self.ui.le_STM41_c1.setText("-6.7339e-12")
        self.ui.le_STM41_d1.setText("5.45977e-14")
        self.ui.le_STM41_a2.setText("9.2575")
        self.ui.le_STM41_b2.setText("-25.7897")
        self.ui.le_STM41_c2.setText("3.1833e-12")
        self.ui.le_STM41_d2.setText("6.34969e-15")
        self.ui.le_STM41_offset.setText("0.013")
        # ===============================================================================================
        self.ui.le_STM40_a1.setText("-9.1137")
        self.ui.le_STM40_b1.setText("-27.646")
        self.ui.le_STM40_c1.setText("-1.1614e-11")
        self.ui.le_STM40_d1.setText("-1.06185e-13")
        self.ui.le_STM40_a2.setText("9.2183")
        self.ui.le_STM40_b2.setText("-27.8018")
        self.ui.le_STM40_c2.setText("1.1899e-11")
        self.ui.le_STM40_d2.setText("8.05335e-13")
        self.ui.le_STM40_offset.setText("0")
        # ===============================================================================================
        self.ui.le_MCBJ41_a1.setText("-9.1316")
        self.ui.le_MCBJ41_b1.setText("-26.9744")
        self.ui.le_MCBJ41_c1.setText("1.8756e-13")
        self.ui.le_MCBJ41_d1.setText("9.8081e-14")
        self.ui.le_MCBJ41_a2.setText("9.1121")
        self.ui.le_MCBJ41_b2.setText("-27.3949")
        self.ui.le_MCBJ41_c2.setText("-7.8635e-13")
        self.ui.le_MCBJ41_d2.setText("2.4551e-13")
        self.ui.le_MCBJ41_offset.setText("-0.025")
        # ===============================================================================================
        self.ui.le_STMNEW_a1.setText("-3.9747")
        self.ui.le_STMNEW_b1.setText("-13.265")
        self.ui.le_STMNEW_a2.setText("4.0114")
        self.ui.le_STMNEW_b2.setText("-13.614")
        self.ui.le_STMNEW_offset.setText("0")

        dlg_title = "info"
        str_info = "All parameters have been reset！"
        QMessageBox.information(self, dlg_title, str_info)
        self.add_textBrowser_str(str_info)
        # END

    @pyqtSlot()
    def on_actSaveData_triggered(self):
        self.on_btn_SaveResult_clicked()

    @pyqtSlot()
    def on_btn_SaveResult_clicked(self):
        try:
            pre_check = self.save_data_precheck()
            # 通过检查的，相应的存储目录都已经建立！！
            if pre_check:
                data_save_path = self.key_para["Data_Save_Path"]
                # ====================完成危险排查，开始数据保存！！！！============
                self.save_fig(data_save_path)

                # 因为图片的保存不耗时，而且里面的对象传参有点麻烦，就在这里直接解决了

                distance, conductance, length, distance_draw, conductance_draw = self.distance, self.conductance, self.length, self.distance_draw, self.conductance_draw
                self._save_all_data_thread = QThread()
                self.save_data = SaveAllData(distance, conductance, length, distance_draw, conductance_draw,
                                             self.key_para)
                self.save_data.tbw.connect(self.add_textBrowser_str)
                self.save_data.run_end.connect(lambda: self.stop_thread(self._save_all_data_thread))

                self.save_data.moveToThread(self._save_all_data_thread)
                self._save_all_data_thread.started.connect(self.save_data.run)
                self._save_all_data_thread.finished.connect(self.show_finished_save)

                logMsg = "Save data..."
                self.addLogMsgWithBar(logMsg)

                self._save_all_data_thread.start()

                self.logger.debug(
                    f"Start the data save thread--{self._save_all_data_thread.currentThread()},Now state:{self._save_all_data_thread.isRunning()}")
        except Exception as e:
            errMsg = f"DATA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    @pyqtSlot()
    def on_btn_Select_SaveDir_clicked(self):
        """
        设置处理结果的保存目录
        :return:
        """
        desktop_path = GeneralUtils.getDesktopPath()
        dlg_title = "Select a Save Directory"
        select_dir = QFileDialog.getExistingDirectory(self, dlg_title, desktop_path, QFileDialog.ShowDirsOnly)
        if select_dir != "":
            self.ui.le_Data_Save_Dir.setText(select_dir)
            self.key_para[self.ui.le_Data_Save_Dir.objectName()] = select_dir

    @pyqtSlot()
    def on_le_Jump_Gap_editingFinished(self):
        """
        因为gap这个值很重要，所以用户在修改的时候需要加上提示
        :return:
        """
        result = QMessageBox.warning(self, "Warning", "This parameter is extremely important. Modify it with caution",
                                     QMessageBox.Ok | QMessageBox.Cancel,
                                     QMessageBox.Cancel)
        if result == QMessageBox.Cancel:
            self.ui.le_Jump_Gap.setText("10000")

    # =============== 控件触发函数===============
    def createFigure(self):
        self._1DCondCanvas = MyFigureCanvas()
        self._1DLengthCanvas = MyFigureCanvas()
        self._2DCondCanvas = MyFigureCanvas()

        self._1DCondNaviBar = MyNavigationToolbar(self._1DCondCanvas, self._1DCondCanvas.main_frame)
        self._1DLengthNaviBar = MyNavigationToolbar(self._1DLengthCanvas, self._1DLengthCanvas.main_frame)
        self._2DCondNaviBar = MyNavigationToolbar(self._2DCondCanvas, self._2DCondCanvas.main_frame)

        self._2DCondLayout.addWidget(self._2DCondCanvas)
        self._2DCondLayout.addWidget(self._2DCondNaviBar)
        self._1DCondLayout.addWidget(self._1DCondCanvas)
        self._1DCondLayout.addWidget(self._1DCondNaviBar)
        self._1DLengthLayout.addWidget(self._1DLengthCanvas)
        self._1DLengthLayout.addWidget(self._1DLengthNaviBar)

        self.ui.grp_2D_Cloud.setLayout(self._2DCondLayout)
        self.ui.grp_1D_Conductance.setLayout(self._1DCondLayout)
        self.ui.grp_1D_Length.setLayout(self._1DLengthLayout)

    def init_save_dir(self):
        desktop_path = GeneralUtils.getDesktopPath()
        self.ui.le_Data_Save_Dir.setText(desktop_path)

    def save_fig(self, data_save_path):
        img_path = os.path.join(data_save_path, "Images")
        GeneralUtils.creatFolder(data_save_path, "Images")
        self._2DCondFig.savefig(img_path + '/2D_Conductance.png', dpi=100, bbox_inches='tight')
        self._1DCondFig.savefig(img_path + '/Conductance_count.png', dpi=100, bbox_inches='tight')
        self._1DLengthFig.savefig(img_path + '/Length_count.png', dpi=100, bbox_inches='tight')

    def save_data_precheck(self):
        """
        点击保存按钮之前的检查工作，包括数据是否存在和校验存储路径是否存在
        :return: bool值
        """
        if not self.key_para["SaveData_Statue"]:
            errMsg = "The data cannot be saved until the data processing is complete!"
            self.addErrorMsgWithBox(errMsg)
            return False

        dlg_title = "File name Settings"
        txt_label = "Please enter the name of the folder to save"
        default_name = "New Folder"
        echo_mode = QLineEdit.Normal
        saveDataDir = self.ui.le_Data_Save_Dir.text()
        flag = False
        while not flag:
            text, OK = QInputDialog.getText(self, dlg_title, txt_label, echo_mode, default_name)
            if OK:
                save_path = os.path.join(saveDataDir, text)
                IS_EXIST = os.path.exists(save_path)
                if IS_EXIST:
                    errMsg = "The file name already exists or is invalid,Please re-enter"
                    self.addErrorMsgWithBox(errMsg)
                    continue
                else:
                    flag = not flag
                    self.key_para["Data_Save_Path"] = save_path
                    GeneralUtils.creatFolder(saveDataDir, text)  # 存储路径直接在这里创建
            else:
                logMsg = "Unsave data"
                self.addLogMsgWithBar(logMsg)
                return False

        return True

    def check_savedir_statue(self):
        """
        在程序初始化的时候检查存储路径的存在与否及其合法性
        :return: bool值
        """
        dir = self.ui.le_Data_Save_Dir.text()
        if dir == "":
            return False
        else:
            # 程序执行到这里，虽然路径不是""，但是应该检查路径的有效性
            return os.path.exists(dir)

    def set_load_state(self, file_list):
        """
        设置文件加载状态
        :param file_list: 调用FileDialog得到的文件列表
        :return: Boolean
        """
        if (len(file_list) > 0):
            return True
        return False

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

    def set_progressBar_int(self, content_int):
        """
        设置进度条数值
        :param content_int: 进度条数值，整数
        :return:无
        """
        self.ui.progressBar.setValue(int(content_int))

    def check_config(self):
        configPath = os.path.join(BASEDIR, "config.ini")
        if os.path.exists(configPath):
            dlg_title = "Info"
            str_info = "Config file detected. Load it??"
            reply = QMessageBox.question(self, dlg_title, str_info,
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.get_last_para()

    def get_panel_para(self):
        """
        点击run按钮之后，获取到面板上的设置参数，将其返回 key_para
        :return: dict，用来更新self.key_para
        """
        """
        点击run按钮之后，获取到面板上的设置参数，将其保存在 key_para 中
        :return: 无
        """
        key_para = {}
        try:
            key_para["DEVICE_ID"] = self.ui.cmb_Device.currentIndex()
            key_para["PROCESS"] = self.ui.cmb_Process.currentIndex()
            key_para["SELECT_OPTION"] = self.ui.rdo_select_open.isChecked()
            # 上面三个参数获取到对应的设备型号以及处理过程，筛选开关

            le_obj_list = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.wdt_Basic_Set, self.ui.wdt_Select_Para]
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.get_same_widget(wdt, QLineEdit))
            for obj in le_obj_list:
                key_para[obj.objectName()] = float(obj.text())
            # ===========================这两个位置比较尴=====手动添加
            obj_list_manual = [self.ui.le_Additional_Length, self.ui.le_Data_Save_Dir]
            key_para[obj_list_manual[0].objectName()] = int(obj_list_manual[0].text())
            key_para[obj_list_manual[1].objectName()] = obj_list_manual[1].text()
            # ==================下面的代码在后续添加了设备后需要手动添加！
            key_para["DEVICE_0_PARA"] = self.get_device_para(self.ui.wdt_Device_0)
            key_para["DEVICE_1_PARA"] = self.get_device_para(self.ui.wdt_Device_1)
            key_para["DEVICE_2_PARA"] = self.get_device_para(self.ui.wdt_Device_2)
            key_para["DEVICE_3_PARA"] = self.get_device_para(self.ui.wdt_Device_3)
        except Exception as e:
            errMsg = f"GTE PANEL PARA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            return None
        else:
            return key_para

    def get_last_para(self):
        """
        加载程序同路径下保存好的历史参数并设置，
        :return:
        """
        try:
            config = configparser.ConfigParser()
            configPath = os.path.join(BASEDIR, "config.ini")
            config.read(configPath, encoding='utf-8')
            section_name = "PANEL_PARA"
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.wdt_Basic_Set, self.ui.wdt_Select_Para, self.ui.wdt_Device_0,
                                         self.ui.wdt_Device_1, self.ui.wdt_Device_2, self.ui.wdt_Device_3]
            le_obj_list = []
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.get_same_widget(wdt, QLineEdit))
            for obj in le_obj_list:
                obj.setText(config.get(section_name, obj.objectName()))
            obj_list_manual = [self.ui.le_Additional_Length, self.ui.le_Data_Save_Dir]
            for obj in obj_list_manual:
                obj.setText(config.get(section_name, obj.objectName()))
            logMsg = "History parameters have been loaded"
            self.addLogMsgWithBar(logMsg)
        except Exception as e:
            errMsg = f"GTE OLD PARA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def save_config_para(self):
        """
        完成关闭软件时面板参数的保存
        :return: 无
        """
        try:
            config = configparser.ConfigParser()
            config.optionxform = str  # 这一句相当的关键，因为config这个模块会把option自动的变为全小写，这个设置可以保持原样！
            section_name = "PANEL_PARA"
            config.add_section(section_name)
            le_obj_list = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.wdt_Basic_Set, self.ui.wdt_Select_Para, self.ui.wdt_Device_0,
                                         self.ui.wdt_Device_1, self.ui.wdt_Device_2, self.ui.wdt_Device_3]

            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                le_obj_list.extend(self.get_same_widget(wdt, QLineEdit))
            for obj in le_obj_list:
                config.set(section_name, obj.objectName(), obj.text())
            # ========这一部分需要手动添加=====
            obj_list_manual = [self.ui.le_Additional_Length, self.ui.le_Data_Save_Dir]
            for obj in obj_list_manual:
                config.set(section_name, obj.objectName(), obj.text())
            configPath = os.path.join(BASEDIR, "config.ini")
            with open(configPath, mode="w", encoding="utf-8") as f:
                config.write(f)
            self.logger.debug("Parameters have been saved")
        except Exception as e:
            errMsg = f"PARA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def get_same_widget(self, widget_name, activeX_name):
        """
        获取某个 widget 中同类型的控件
        :param widget_name: widget名，传入的是ui中的某个widget名
        :param activeX_name: 控件类型，传入的是对象
        :return: 寻找到的对象集合(List)
        """
        return widget_name.findChildren(activeX_name)

    def get_device_para(self, widget_name):
        """
        获取不同设备对应的参数，注意只需要传入widget_name
        :param widget_name:
        :return: dict
        """
        temp = {}
        obj_list = self.get_same_widget(widget_name, QLineEdit)
        for obj in obj_list:
            temp[obj.objectName()] = float(obj.text())
        return temp

    def split_filelist(self, file_list):
        """
        遗憾的是，还是单个文件比较快，此功能dead
        开发此功能的目的是加载多个文件之后，因为采用多进程的进程池去处理，每次处理一个文件总是感觉会有点浪费开销
        所以，可以吧filelist做一个变化，几个文件为一组，变成二维数组
        :param file_list:
        :return: 修改好的filelist
        """
        file_list_new = []
        GROUP_SIZE = 3  # 一次处理两个文件----------经过测试，同时处理三个文件效率较高！！
        len_file_list = len(file_list)
        if (len(file_list) <= GROUP_SIZE):
            return file_list_new.append(file_list)
        len_new_list = len_file_list // GROUP_SIZE if len_file_list % GROUP_SIZE == 0 else len_file_list // GROUP_SIZE + 1
        for i in range(len_new_list):
            file_list_new.append(file_list[i * GROUP_SIZE:GROUP_SIZE * (i + 1)])
        return file_list_new

    def draw_prepare(self):
        """
        绘图前的准备
        :return: 无
        """
        self.logger.debug("The computing process exits safely and begins computing drawing data")
        original_dataset = self.data_analysis.dataset
        # 这里的这个返回值不管是单个文件，还是多个文件，都是List
        try:
            self.dataset, statue = self.get_NOTNULL_dataset(original_dataset)
        except Exception as e:
            errMsg = f"The parallel computing data aggregation error:{e}"
            self.addErrorMsgWithBox(errMsg)
            self.set_progressBar_int(0)
            self.ui.actRun.setEnabled(True)

        else:
            if not statue:
                self.set_progressBar_int(0)
                self.ui.actRun.setEnabled(True)
                # TODO
                # 程序运行到此处，说明一条都没切出来，需要修改切分范围，所以可以删掉一些东西
                # 已经在 get_NOTNULL_dataset 函数中进行了异常提示！！！

            else:
                self.cal_draw()  # 检查通过之后，开始计算绘图所需数据

    def stop_thread(self, thread):
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

    def check_dataset(self, dataset):
        """
        检查切分数据是否成功
        :param dataset: 单个的dataset
        :return: bool
        """
        if not dataset:
            return False
        else:
            if dataset[1].shape[0] < 2 or dataset[2].shape[0] < 2 or dataset[3].shape[0] < 2 or \
                    dataset[4].shape[0] < 2 or dataset[5].shape[0] < 2:
                return False
            return True

    def get_NOTNULL_dataset(self, original_dataset):
        """
        因为存在多进程的问题，有可能那么几组就一条也没有，后面的计算绘图数据可能会有问题，以及
        后面多组数据的叠加也会有问题，就头疼哈哈，所以这里直接把空的去掉！
        :param original_dataset: 多进程得到的数据
        :return: 非空数据
        """
        effective_counts = 0
        dataset = []
        for data in original_dataset:
            checkStatue = self.check_dataset(data)
            if checkStatue:
                dataset.append(data)
                effective_counts += 1

        if effective_counts == 0:
            errMsg = "Cut fail, advice：\n1.Modify HIGH_CUT\n2.Modify instrument fitting parameters\n3.Poor data quality"
            self.addErrorMsgWithBox(errMsg)
            return dataset, False
        else:
            return dataset, True

    def cal_draw(self):
        """
        开启计算绘图数据的进程
        :return:无
        """
        try:
            self._drawdata_thread = QThread()
            self.cal_draw_data = CalDrawData(self.key_para, self.dataset)
            self.cal_draw_data.pbar.connect(self.set_progressBar_int)
            self.cal_draw_data.tbw.connect(self.add_textBrowser_str)
            self.cal_draw_data.sbar.connect(self.add_statusBar_str)
            self.cal_draw_data.run_end.connect(lambda: self.stop_thread(self._drawdata_thread))

            self.cal_draw_data.moveToThread(self._drawdata_thread)
            self._drawdata_thread.started.connect(self.cal_draw_data.run)
            self._drawdata_thread.finished.connect(self.start_draw)

            logMsg = "Drawing data calculation..."
            self.logger.debug(logMsg)

            self._drawdata_thread.start()

            self.logger.debug(
                f"Start the drawing data calculation thread--{self._drawdata_thread.currentThread()},Now state:{self._drawdata_thread.isRunning()}")
        except Exception as e:
            errMsg = f"CALCULATE DRAWDATA ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)

    def start_draw(self):
        """
        准备绘图及相关按钮设置
        :return: 无
        """
        self.logger.debug("Drawing data calculation completed, Ready to drawing")
        self.set_progressBar_int(96)
        self.draw_dataset = self.cal_draw_data.draw_dataset
        draw_dataset = copy.deepcopy(self.draw_dataset)
        try:
            *drawdata_temp, statue = self.get_cumulative_drawdata(draw_dataset)
        except Exception as e:
            errMsg = f"The parallel computing draw data aggregation error:{e}"
            self.addErrorMsgWithBox(errMsg)
            self.set_progressBar_int(0)
        else:
            if not statue:
                self.set_progressBar_int(0)

            else:
                self.distance, self.conductance, self.length, self.distance_draw, self.conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = drawdata_temp
                self.set_trace_ratio(ALL_TRACE_NUM, SELECT_TRACE_NUM)

                logMsg = "Start drawing..."
                self.addLogMsgWithBar(logMsg)

                try:
                    self.draw(self.distance_draw, self.conductance_draw, self.length)
                except Exception as e:
                    errMsg = f"DRAW ERROR:{e}"
                    self.addErrorMsgWithBox(errMsg)
                    self.set_progressBar_int(0)
                else:
                    self.set_progressBar_int(100)
                    self.ui.btn_Update.setEnabled(True)
                    self.ui.btn_Redraw.setEnabled(True)
        finally:
            self.ui.actRun.setEnabled(True)  # 需要注意的是，在绘图完成后将run按钮重新打开，就不用再次加载数据了

    def draw(self, distance, conductance, length):
        """
        画图
        :param distance: 距离
        :param conductance: 叠加后的一维电导
        :param length: 叠加后的一维长度
        :return: 无
        """

        FONTSIZE = 8
        CM = plt.cm.coolwarm
        _2D_BINSX = int(self.key_para["le_2D_BinsX"])
        _2D_BINSY = int(self.key_para["le_2D_BinsY"])
        _2D_XLEFT = self.key_para["le_2D_Xleft"]
        _2D_XRIGHT = self.key_para["le_2D_Xright"]
        _2D_YLEFT = self.key_para["le_2D_Yleft"]
        _2D_YRIGHT = self.key_para["le_2D_Yright"]
        _2D_VMAX = int(self.key_para["le_2D_V_max"])
        _1D_COND_XLEFT = self.key_para["le_1D_Cond_Xleft"]
        _1D_COND_XRIGHT = self.key_para["le_1D_Cond_Xright"]
        _1D_COND_BINS = int(self.key_para["le_1D_Cond_Bins"])
        _1D_LENG_XLEFT = self.key_para["le_1D_Leng_Xleft"]
        _1D_LENG_XRIGHT = self.key_para["le_1D_Leng_Xright"]
        _1D_LENG_BINS = int(self.key_para["le_1D_Leng_Bins"])
        _mean_length = round(np.mean(length), 2)
        # _sigma_length = np.std(length)

        self._2DCondFig = self._2DCondCanvas.fig
        self._2DCondFig.clf()
        self._2DCondAxes = self._2DCondFig.add_subplot()
        *_2D_DATA_FIG, image = self._2DCondAxes.hist2d(distance, conductance, bins=[_2D_BINSX, _2D_BINSY],
                                                       range=[[_2D_XLEFT, _2D_XRIGHT],
                                                              [_2D_YLEFT, _2D_YRIGHT]], vmin=0,
                                                       vmax=_2D_VMAX, cmap=CM)
        self._2DCondAxes.set_xlabel('Length / nm', fontsize=FONTSIZE)
        self._2DCondAxes.set_ylabel('Conductance', fontsize=FONTSIZE)
        # self._2D_conductance_fig.fig.tight_layout()
        self._2DCondFig.colorbar(image, pad=0.02, aspect=50, ticks=None)
        self._2DCondFig.canvas.draw()
        self._2DCondFig.canvas.flush_events()

        self._1DCondFig = self._1DCondCanvas.fig
        self._1DCondFig.clf()
        self._1DCondAxes = self._1DCondFig.add_subplot()
        _1D_DATA_FIG = self._1DCondAxes.hist(conductance, bins=_1D_COND_BINS, color='green', alpha=0.8,
                                             range=[_1D_COND_XLEFT, _1D_COND_XRIGHT])
        self._1DCondAxes.set_xlabel('Conductance', fontsize=FONTSIZE)
        self._1DCondAxes.set_ylabel('Counts', fontsize=FONTSIZE)
        self._1DCondAxes.set_xlim((_1D_COND_XLEFT, _1D_COND_XRIGHT))
        self._1DCondAxes.grid(True)
        # self._1D_conductance_fig.axes.yaxis.get_major_formatter().set_powerlimits((0, 1))
        # 换一种科学计数法
        self._1DCondAxes.ticklabel_format(style='scientific', scilimits=(0, 2), useMathText=True)
        # scilimits=(m,n)表示如果刻度范围超出10^m10m到10^n10n，那么就是用科学计数法。
        # 如果将scilimits参数设为(0,0)，那么对于所有的刻度范围都自动显示成科学计数的形式。所以这里设置为10^2以外的才用科学计数法
        # 令useMathText=False的时候，会显示为1eX1eX的形式，useMathText=True的时候，会显示成10^X10X的形式。

        # self._1D_conductance_fig.fig.tight_layout()
        # TODO 这个后面考虑是采用自己继承的NavigationToolbar还是tight_layout()？
        self._1DCondFig.canvas.draw()
        self._1DCondFig.canvas.flush_events()

        self._1DLengthFig = self._1DLengthCanvas.fig
        self._1DLengthFig.clf()
        self._1DLengthAxes = self._1DLengthFig.add_subplot()
        # density=True,
        _, BINS_LENGTH, _ = self._1DLengthAxes.hist(length, bins=_1D_LENG_BINS,
                                                    range=[_1D_LENG_XLEFT, _1D_LENG_XRIGHT],
                                                    label="length: " + str(_mean_length))
        # self._1D_length_fig.axes.yaxis.get_major_formatter().set_powerlimits((0, 1))
        self._1DLengthAxes.ticklabel_format(style='scientific', scilimits=(0, 2), useMathText=True)
        # temp_y = norm.pdf(BINS_LENGTH, _mean_length, _sigma_length)
        # self._1DLengthAxes.plot(BINS_LENGTH, temp_y, "r--", label="length: " + str(_mean_length))
        self._1DLengthAxes.set_xlabel('Length / nm', fontsize=FONTSIZE)
        self._1DLengthAxes.set_ylabel('counts', fontsize=FONTSIZE)
        self._1DLengthAxes.set_xlim((_1D_LENG_XLEFT, _1D_LENG_XRIGHT))
        self._1DLengthAxes.grid(True)
        self._1DLengthAxes.legend(loc=1)
        # self._1D_length_fig.fig.tight_layout()
        self._1DLengthFig.canvas.draw()
        self._1DLengthFig.canvas.flush_events()

        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.key_para["SaveData_Statue"] = True  # 这个true放在这里的目的是只要绘图完成一遍，就说明产生了新数据，可以保存

    def set_trace_ratio(self, ALL_TRACE_NUM, SELECT_TRACE_NUM):
        """
        在ui上面设置筛选结果
        :param ALL_TRACE_NUM: 所有曲线条数
        :param SELECT_TRACE_NUM: 筛选曲线条数
        :return: 无
        """
        self.ui.le_AllTrace.setText(str(ALL_TRACE_NUM))
        self.ui.le_SelectedTrace.setText(str(SELECT_TRACE_NUM))
        self.ui.le_Ratio.setText(f"{SELECT_TRACE_NUM / ALL_TRACE_NUM:.2%}")

    def get_cumulative_drawdata(self, draw_dataset):
        """
        得到聚合结果（将多进程得到的绘图数据聚合）
        :param draw_dataset: 绘图数据（list，list长度为绘图进程数）
        :return: 返回聚合结果
        """
        if len(draw_dataset) == 1:
            if self.check_draw_dataset(draw_dataset[0]):
                return draw_dataset[0][0], draw_dataset[0][1], draw_dataset[0][2], draw_dataset[0][3], draw_dataset[0][
                    4], \
                       draw_dataset[0][5], draw_dataset[0][6], True
            else:
                errMsg = "No valid drawing data, please adjust data"
                self.addErrorMsgWithBox(errMsg)
                return None, False
        else:
            effective_counts = 0
            distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = None, None, None, None, None, None, None,
            for draw_data in draw_dataset:
                if self.check_draw_dataset(draw_data):
                    if effective_counts == 0:
                        effective_counts += 1
                        distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM = \
                            draw_dataset[0][0], draw_dataset[0][1], draw_dataset[0][2], draw_dataset[0][3], \
                            draw_dataset[0][4], draw_dataset[0][5], draw_dataset[0][6]
                    else:
                        distance = np.concatenate((distance, draw_data[0]))
                        conductance = np.concatenate((conductance, draw_data[1]))
                        length = np.concatenate((length, draw_data[2]))
                        distance_draw = np.concatenate((distance_draw, draw_data[3]))
                        conductance_draw = np.concatenate((conductance_draw, draw_data[4]))
                        ALL_TRACE_NUM += draw_data[5]
                        SELECT_TRACE_NUM += draw_data[6]
            if effective_counts == 0:
                errMsg = "No valid drawing data, please adjust data"
                self.addErrorMsgWithBox(errMsg)
                return None, False
            else:
                return distance, conductance, length, distance_draw, conductance_draw, ALL_TRACE_NUM, SELECT_TRACE_NUM, True

    def check_draw_dataset(self, draw_dataset):
        if not draw_dataset:
            return False
        else:
            if draw_dataset[0].shape[0] < 2 or draw_dataset[1].shape[0] < 2 or draw_dataset[2].shape[0] < 2:
                return False
            return True

    def show_finished_save(self):
        data_save_path = self.key_para["Data_Save_Path"]
        logMsg = f"All data has been saved. Path:{data_save_path}"
        self.addLogMsgWithBar(logMsg)
        QMessageBox.information(self, "Info", logMsg)


if __name__ == '__main__':
    freeze_support()
    # 这行是为了解决多进程的问题
    app = QApplication(sys.argv)
    basicAnalysisModule = QmyBasicAnalysisModule()
    basicAnalysisModule.show()
    sys.exit(app.exec_())
