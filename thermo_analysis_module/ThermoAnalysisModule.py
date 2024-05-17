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
from ui_QWThermoAnalysisModule import *
from ThermoConst import *
from myFigure import *
from ThermoAnalysis import ThermoAnalysis, gaussian


class ThermoAnalysisModule(QMainWindow):
    logger = MyLog("ThermoAnalysisModule", BASEDIR)

    def __init__(self, parent=None):
        super(ThermoAnalysisModule, self).__init__(parent)
        self.ui = Ui_QWEThermoModule()
        self.ui.setupUi(self)
        self.init_set()
        self.checkConfig()
        self.init_widget()
#===============初始化相关=====================  
    def init_set(self):
        """成员变量的初始化
        """
        self.keyPara = {}
        self.keyPara["SAVE_DATA_STATUE"] = False  # 数据保存标志位，初始化false，另外在点击run之后也应该设置false，绘图完成设置true
        self.lastOpenPath = BASEDIR # 打开文件夹的初始地址
        self.keyPara['PARA_ID'] = 0

    def init_widget(self):
        """绘图区初始化
        """
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
        self._rightLayout  = QVBoxLayout(self)
        self._centerLayout = QVBoxLayout(self)
        self._leftLayout = QVBoxLayout(self)
        #self._blankLayout = QVBoxLayout(self)

        self._rightCanvas = MyFigureCanvas()
        self._centerCanvas = MyFigureCanvas()
        self._leftCanvas = MyFigureCanvas()
        #self._blankCanvas = MyFigureCanvas()

        self._rightToolBar = MyNavigationToolbar(self._rightCanvas, self._rightCanvas.mainFrame)
        self._centerToolBar = MyNavigationToolbar(self._centerCanvas, self._centerCanvas.mainFrame)
        self._leftToolBar = MyNavigationToolbar(self._leftCanvas, self._leftCanvas.mainFrame)
        #self._blankToolBar = MyNavigationToolbar(self._blankCanvas, self._blankCanvas.mainFrame)

        self._rightLayout.addWidget(self._rightCanvas)
        self._rightLayout.addWidget(self._rightToolBar)
        self._centerLayout.addWidget(self._centerCanvas)
        self._centerLayout.addWidget(self._centerToolBar)
        self._leftLayout.addWidget(self._leftCanvas)
        self._leftLayout.addWidget(self._leftToolBar)
        # self._blankLayout.addWidget(self._blankCanvas)
        # self._blankLayout.addWidget(self._blankToolBar)
        
        self.ui.grp_right_hist.setLayout(self._rightLayout)
        self.ui.grp_center_hist.setLayout(self._centerLayout)
        self.ui.grp_left_hist.setLayout(self._leftLayout)
        #self.ui.grp_blank.setLayout(self._blankLayout)

    def initSaveDir(self):
        """
        初始化保存数据路径是桌面路径，后续加载完数据后应当修改为数据的文件路径！！
        :return:
        """
        deskPath = GeneralUtils.getDesktopPath()
        self.ui.le_Data_Save_Dir.setText(deskPath)
    
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
                    self.lastOpenPath = os.path.dirname(fileList[0])    
                    self.keyPara['FILE_PATHS'] = fileList
                    self.add_textBrowser_str(f"{len(fileList)} files have been loaded:")
                    self.add_textBrowser_list(fileList)
                    self.add_textBrowser_str("*" * 45, showtime=False)
                    # 加载文件成功之后，应当对运行按钮进行释放
                    self.ui.actRun.setEnabled(True)
                    # 默认结果保存路径与数据文件一致
                    self.ui.le_Data_Save_Dir.setText(self.lastOpenPath)
                    self.logger.debug("File loading completed.")
        except Exception as e:
            errMsg = f"DATA FILE LOAD ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
        

    @pyqtSlot()
    def on_actRun_triggered(self):
        try:
            self.ui.actRun.setEnabled(False)  # 不可连续点
            self.ui.actSaveData.setEnabled(False) # 不可保存
            self.ui.actQuit.setEnabled(False)
            self.ui.actOpenFiles.setEnabled(False)
            self.keyPara["SAVE_DATA_STATUE"] = False
            keyPara = self.getPanelPara()
            if keyPara is None:
                return
            else:
                self.keyPara.update(keyPara)
                self.logger.debug(f"Parameters are updated before running. Parameter list:{self.keyPara}")
                self.dataThread = QThread()
                self.dataAnalysis = ThermoAnalysis(self.keyPara)
                self.dataAnalysis.plotRightHist.connect(self._drawRH)
                self.dataAnalysis.plotCenterHist.connect(self._drawCH)
                self.dataAnalysis.plotLeftHist.connect(self._drawLH)
                # 正常运行结束
                self.dataAnalysis.runEnd.connect(lambda: self.stopThread(self.dataThread))
                # 数据处理出错
                self.dataAnalysis.error.connect(self.threadError)


                self.dataAnalysis.moveToThread(self.dataThread)
                self.dataThread.started.connect(self.dataAnalysis.run)
                self.dataThread.finished.connect(self.threadFinish)

                logMsg = "Data calculation..."
                self.addLogMsgWithBar(logMsg)

                self.dataThread.start()
                self.logger.debug(
                    f"Start the data calculation thread--{self.dataThread.currentThread()},Now state:{self.dataThread.isRunning()}")
                pass
        except Exception as e:
            errMsg = f"RUN ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
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
#=================绘图=============================
    def _drawRH(self):
        binsx = int(self.keyPara['le_BinsX'])
        self._drawHist(self.dataAnalysis.rightData, binsx, self._rightCanvas, self.dataAnalysis.rightFit)
    
    def _drawCH(self):
        binsx = int(self.keyPara['le_BinsX'])
        self._drawHist(self.dataAnalysis.centerData, binsx, self._centerCanvas, self.dataAnalysis.centerFit)
    
    def _drawLH(self):
        binsx = int(self.keyPara['le_BinsX'])
        self._drawHist(self.dataAnalysis.leftData, binsx, self._leftCanvas, self.dataAnalysis.leftFit)
    
    def _drawHist(self, data, bins, canvas, paras):
        fig = canvas.fig
        fig.clf()
        ax = fig.add_subplot()
        if len(data) == 0:
            ax.set_title("No valid value")
            fig.tight_layout()
            fig.canvas.draw()
            fig.canvas.flush_events()
            return
        vec = np.concatenate([item['volt'] for item in data])
        y, edges, _ = ax.hist(vec, bins = bins)
        x = (edges[:-1] + edges[1:]) / 2
        
        center = gaussian(paras[1], *paras)
        
        y_fit = gaussian(x, *paras)
        ax.plot(x, y_fit, 'r')
        ax.set_xlabel('Volt / uV')
        ax.set_ylabel('Counts')
        ax.set_title(f"num={len(data)}, mean = {paras[1]: .3f}", fontsize=15)
        
        fig.tight_layout()
        fig.canvas.draw()
        fig.canvas.flush_events()
        
        

#=================辅助函数=============================
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
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.grp_AdvancePara, self.ui.grp_Analysis]
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
        defaultName = "Result"
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
    
    def threadFinish(self):
        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.keyPara["SAVE_DATA_STATUE"] = True
        self.ui.actSaveData.setEnabled(True)
        self.ui.actOpenFiles.setEnabled(True)
        self.ui.actRun.setEnabled(True)
        self.ui.actQuit.setEnabled(True)
    
    def threadError(self, msg):
        if (self.dataThread.isRunning):
            self.dataThread.quit()
            self.dataThread.wait()
        self.addErrorMsgWithBox(msg)
        self.ui.actRun.setEnabled(True)
    def getPanelPara(self):
        """
        run之后, 需要进行面板的参数采集
        :return:
        """
        keyPara = {}
        try:
            #keyPara["PARA_ID"] = self.ui.cmb_Fit.currentIndex()
            leObjList = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.grp_AdvancePara, self.ui.grp_Analysis]
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

    def getSameWidget(self, widgetName, activeXName):
        """
        获取某个 widget 中同类型的控件
        :param widgetName: widget名, 传入的是ui中的某个widget名
        :param activeXName: 控件类型，传入的是对象
        :return: 寻找到的对象集合(List)
        """
        return widgetName.findChildren(activeXName)

    def saveFig(self):
        save_path = self.keyPara["Data_Save_Path"]
        center_path = os.path.join(save_path, "center.png")
        right_path = os.path.join(save_path, "right.png")
        left_path = os.path.join(save_path, "left.png")
        
        self._rightCanvas.fig.savefig(right_path, dpi=300, bbox_inches='tight')
        self._centerCanvas.fig.savefig(center_path, dpi=300, bbox_inches='tight')
        self._leftCanvas.fig.savefig(left_path, dpi=300, bbox_inches='tight')
        
    def saveData(self):
        save_path = self.keyPara["Data_Save_Path"]
        data_dir = os.path.join(save_path, "Data")
        GeneralUtils.creatFolder(save_path, "Data")
        # 保存centerCurrentToVolt·
        c2v = np.concatenate([item['c2v'] for item in self.dataAnalysis.centerData])
        x = np.linspace(-0.005, 0.005, 150)
        h, edges = np.histogram(c2v, bins=x)
        bin_centers = (edges[:-1] + edges[1:]) / 2
        res = np.column_stack([bin_centers, h])
        np.savetxt(os.path.join(data_dir, 'centerCurrentToVolt.txt'), res, fmt='%0.18e', delimiter='\t')
        # 保存rightCurrentToVolt
        c2v = np.concatenate([item['c2v'] for item in self.dataAnalysis.rightData])
        x = np.linspace(-0.005, 0.005, 150)
        h, edges = np.histogram(c2v, bins=x)
        bin_centers = (edges[:-1] + edges[1:]) / 2
        res = np.column_stack([bin_centers, h])
        np.savetxt(os.path.join(data_dir, 'rightcurrentToVolt.txt'), res, fmt='%0.18e', delimiter='\t')
        # 保存center
        bins = bins = int(self.keyPara['le_BinsX'])
        vec = np.concatenate([item['volt'] for item in self.dataAnalysis.centerData])
        y, bin_edges = np.histogram(vec, bins=bins)
        x = (bin_edges[:-1] + bin_edges[1:]) / 2
        res = np.column_stack([x, y])
        np.savetxt(os.path.join(data_dir, 'autoPickedCenterVoltHist.txt'), res, fmt='%0.18e', delimiter='\t')
        # 保存right
        vec = np.concatenate([item['volt'] for item in self.dataAnalysis.rightData])
        y, bin_edges = np.histogram(vec, bins=bins)
        x = (bin_edges[:-1] + bin_edges[1:]) / 2
        res = np.column_stack([x, y])
        np.savetxt(os.path.join(data_dir, 'autoPickedRightVoltHist.txt'), res, fmt='%0.18e', delimiter='\t')
        # 保存left
        vec = np.concatenate([item['volt'] for item in self.dataAnalysis.leftData])
        y, bin_edges = np.histogram(vec, bins=bins)
        x = (bin_edges[:-1] + bin_edges[1:]) / 2
        res = np.column_stack([x, y])
        np.savetxt(os.path.join(data_dir, 'autoPickedLeftVoltHist.txt'), res, fmt='%0.18e', delimiter='\t')
            
        
        # 保存rightData 中的每个volt
    
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
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.grp_BasicPara, self.ui.grp_AdvancePara, self.ui.grp_Analysis]
            for wdt in LINEEDIT_WIDGET_NEED_LIST:
                leObjList.extend(self.getSameWidget(wdt, QLineEdit))
            for obj in leObjList:
                config.set(section_name, obj.objectName(), obj.text())
            # ========这一部分需要手动添加=====
            obj_list_manual = [self.ui.le_Data_Save_Dir]
            for obj in obj_list_manual:
                config.set(section_name, obj.objectName(), obj.text())
            with open(config_path, mode="w", encoding="utf-8") as f:
                config.write(f)
            self.logger.debug("Parameters have been saved")
        except Exception as e:
            errMsg = f"PARA SAVE ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
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
    thermoAnalysisModule = ThermoAnalysisModule()
    thermoAnalysisModule.show()
    sys.exit(app.exec_())