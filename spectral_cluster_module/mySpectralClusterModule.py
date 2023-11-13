# -*- coding: utf-8 -*-
# @Time   : 2021/10/20 15:51
# @Author : Gang
# @File   : mySpectralClusterModule.py
import sys
import time

from PyQt5.QtCore import pyqtSlot, QThread
import numpy as np
import matplotlib.colors as colors

from gangLogger.myLog import MyLog
from spectralClusterConst import *
from gangUtils.generalUtils import GeneralUtils
from spectralClusterDataAnalysis import SpectralClusterDataAnalysis as DataAnalysis

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QMessageBox, QLineEdit, QFileDialog
import matplotlib.pyplot as plt
from spectralClusterFigure import *
from ui_QWSpectralClusterModule import *
from DataSave import *


class QmySpectralClusterModule(QMainWindow):
    logger = MyLog("QmySpectralClusterModule", BASEDIR)

    def __init__(self, parent=None):
        super(QmySpectralClusterModule, self).__init__(parent)
        self.ui = Ui_QWSpectralClusterModule()
        self.ui.setupUi(self)
        self.initSet()
        self.initWidget()

    def initSet(self):
        self.keyPara = {}
        self.redraw = False
        self.keyPara["SAVE_DATA_STATUE"] = False  # 数据保存标志位，初始化false，另外在点击run之后也应该设置false，绘图完成设置true

    def initWidget(self):
        self.ui.actRun.setEnabled(False)
        self.ui.actSaveData.setEnabled(False)
        self.condCloudOriLayout = QVBoxLayout()
        self.clusterValidLayout = QVBoxLayout()
        self.condClusterLayout = QVBoxLayout()
        self.condCloudClusterLayout = QVBoxLayout()

        self.createFigure()

    # ============控件触发函数===============
    @pyqtSlot()
    def on_actSaveData_triggered(self):
        try:
            preCheck = self.savePre()
            if preCheck:
                self._save_thread = QThread()
                self._data_save = DataSave(self.conductance, self.distance, self.length_arr, self.additional_length,
                                           self.labelsList[self.KoptIndex], self.KoptIndex+2, self.keyPara)
                self._data_save.run_end.connect(lambda: self.stopThread(self._save_thread))
                self._data_save.moveToThread(self._save_thread)
                self._save_thread.started.connect(self._data_save.run)
                self._save_thread.finished.connect(self.saveFinish)
                self._save_thread.start()
                logMsg = "Save data..."
                self.addLogMsgWithBar(logMsg)
                self.ui.actSaveData.setEnabled(False)
                save_path = self.keyPara['SAVE_FOLDER_PATH']
                ch_fig_path = os.path.join(save_path, 'CHIndex.png')
                self._CHIndexFig.savefig(ch_fig_path, dpi=300, bbox_inches='tight')
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
    def on_btn_Redraw_clicked(self):
        try:
            self.redraw = True
            self.ui.btn_Redraw.setEnabled(False)
            keyPara = self.getPanelPara()
            self.keyPara.update(keyPara)
            self.draw()
        except Exception as e:
            errMsg = f"REDRAW ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
        self.ui.btn_Redraw.setEnabled(True)
        self.redraw = False

    # ============控件触发函数===============
    def savePre(self):
        root_dir = os.path.dirname(self.keyPara['FILE_PATH'])
        folder_name = self.ui.le_SaveFolder_Name.text()
        save_path = os.path.join(root_dir, folder_name)
        self.keyPara['SAVE_FOLDER_PATH'] = save_path
        cluster_num = self.KoptIndex + 2

        try:
            GeneralUtils.creatFolder(root_dir, folder_name)
            for i in range(cluster_num):
                GeneralUtils.creatFolder(save_path, f'cluster{i+1}')
        except Exception as e:
            errMsg = f"NEW FOLDER ERROR:{e}"
            self.addErrorMsgWithBox(errMsg)
            return False
        else:
            return True
    

    def saveFinish(self):
        logMsg = f"Save data in {self.keyPara['SAVE_FOLDER_PATH']} success!"
        self.addLogMsgWithBar(logMsg)
        QMessageBox.information(self, "Info", logMsg)
        self.ui.actSaveData.setEnabled(True)

    
    def drawPre(self):
        """
        绘图之前的准备工作
        :return:
        """
        try:
            self.logger.debug("The computing process exits safely and begins computing drawing data")
            dataset = self.dataAnalysis.dataset
            if dataset is None:
                errMsg = "DATASET ERROR"
                self.addErrorMsgWithBox(errMsg)
            else:
                self.conductance, self.distance, self.length_arr, self.additional_length,self.dataHistAll, \
                self.dataHistAll_X, self.labelsList, self.calinskiHarabaszIndex = dataset
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

    def draw(self):
        """
        聚类结果的绘图工作，此部分是比较复杂的
        :return:
        """

        def makeBar(rgbTest, colorName='my_color'):

            r1 = np.linspace(rgbTest[0], 255, 128)
            r2 = np.linspace(rgbTest[1], 255, 128)
            r3 = np.linspace(rgbTest[2], 255, 128)

            rgbTest2 = np.vstack((r1, r2, r3))
            icmapTest = colors.ListedColormap(rgbTest2.T[::-1] / 255, name=colorName)
            return icmapTest

        colorSet = np.array([106, 165, 171,
                             246, 138, 65,
                             26, 70, 105,
                             206, 190, 175,
                             157, 89, 130,
                             242, 174, 65,
                             61, 68, 78,
                             230, 81, 77])
        colorSetTest = colorSet.reshape(-1, 3) / 255

        colorBarCmap = []
        for rgb in colorSet.reshape(-1, 3):
            colorCmap = makeBar(rgb)
            colorBarCmap.append(colorCmap)

        # 原始二维图绘制
        _2DCloud_BINSX = int(self.keyPara["le_2D_Cloud_BinsX"])
        _2DCloud_BINSY = int(self.keyPara["le_2D_Cloud_BinsY"])
        _2DCloud_XLEFT = self.keyPara["le_2D_Cloud_Xleft"]
        _2DCloud_XRIGHT = self.keyPara["le_2D_Cloud_Xright"]
        _2DCloud_YLEFT = self.keyPara["le_2D_Cloud_Yleft"]
        _2DCloud_YRIGHT = self.keyPara["le_2D_Cloud_Yright"]
        _2DCloud_VMIN = self.keyPara["le_2D_Cloud_VMin"]
        _2DCloud_VMAX = self.keyPara["le_2D_Cloud_VMax"]
        _2DCloud_CMAP = plt.cm.get_cmap("coolwarm")  # 此处的颜色后续看是否需要自定义

        conductanceDraw = self.conductance.reshape(-1)
        distanceDraw = self.distance.reshape(-1)

        self._2DCloudFig = self.condCloudOriCanvas.fig
        self._2DCloudFig.clf()
        self._2DCloudAx = self._2DCloudFig.add_subplot()
        *_2DCloud_FIG, image_2DCloud = self._2DCloudAx.hist2d(
            distanceDraw, conductanceDraw,
            bins=[_2DCloud_BINSX, _2DCloud_BINSY],
            range=[[_2DCloud_XLEFT, _2DCloud_XRIGHT],
                   [_2DCloud_YLEFT, _2DCloud_YRIGHT]],
            vmin=_2DCloud_VMIN,
            vmax=_2DCloud_VMAX,
            cmap=_2DCloud_CMAP
        )
        self._2DCloudAx.set_xlabel("Length/nm")
        self._2DCloudAx.set_ylabel("Conductance/log(G/G$_0$)")
        self._2DCloudFig.colorbar(image_2DCloud, pad=0.02, aspect=50, ticks=None)
        self._2DCloudFig.tight_layout()
        self._2DCloudFig.canvas.draw()
        self._2DCloudFig.canvas.flush_events()

        # 不同聚类数指标分布
        CH_INDEX = self.calinskiHarabaszIndex
        ClusterNMax = int(self.keyPara["le_ClusterNumMax"])
        CH_INDEX_X = range(2, ClusterNMax + 1)

        self._CHIndexFig = self.clusterValidCanvas.fig
        self._CHIndexFig.clf()
        self._CHIndexAx = self._CHIndexFig.add_subplot()
        self._CHIndexAx.plot(CH_INDEX_X, CH_INDEX, color=colorSetTest[-1], linestyle='-', lw=2)
        self._CHIndexAx.set_xlabel("Number of clusters")
        self._CHIndexAx.set_ylabel("CH index")
        self._CHIndexAx.set_title("Cluster validation")
        self._CHIndexAx.set_xticks(CH_INDEX_X)

        self._CHIndexFig.tight_layout()
        self._CHIndexFig.canvas.draw()
        self._CHIndexFig.canvas.flush_events()

        # 一维电导图聚类结果
        dataHistAll, dataHistAll_X = self.dataHistAll, self.dataHistAll_X
        condHigh, condLow = self.keyPara["le_1DCluster_LogG_High"], self.keyPara["le_1DCluster_LogG_Low"]
        trueIndex = np.where((dataHistAll_X >= condLow) & (dataHistAll_X <= condHigh))[0]
        dataHistAllSelect = dataHistAll[:, trueIndex]
        dataHistAll_XSelect = dataHistAll_X[trueIndex]

        KoptIndex = np.argmax(self.calinskiHarabaszIndex)
        self.KoptIndex = KoptIndex
        labels = self.labelsList[KoptIndex]
        ClusterNGreat = KoptIndex + 2
        self._1DClusterFig = self.condClusterCanvas.fig
        self._1DClusterFig.clf()
        self._1DClusterAx = self._1DClusterFig.add_subplot()
        self._1DClusterAx.plot(dataHistAll_XSelect, dataHistAllSelect.mean(axis=0), color='b', lw=1.5,
                               label='All traces')
        self._1DClusterAx.set_xlabel('Conductance/log(G/G$_0$)')
        self._1DClusterAx.set_ylabel("Counts per trace")
        self._1DClusterAx.set_title("Original data and Cluster")
        for i in range(ClusterNGreat):
            index_i = np.where(labels == i)[0]
            Cluster_i_hist = dataHistAllSelect[index_i]
            self._1DClusterAx.plot(dataHistAll_XSelect,
                                   Cluster_i_hist.mean(axis=0),
                                   color=colorSetTest[i % len(colorSetTest)],
                                   lw=0)
            self._1DClusterAx.fill_between(
                dataHistAll_XSelect,
                Cluster_i_hist.mean(axis=0),
                color=colorSetTest[i % len(colorSetTest)],
                label=f"Cluster {i + 1}",
                alpha=0.81)
        self._1DClusterAx.legend()
        self._1DClusterAx.ticklabel_format(style='scientific', scilimits=(0, 2), useMathText=True)

        self._1DClusterFig.tight_layout()
        self._1DClusterFig.canvas.draw()
        self._1DClusterFig.canvas.flush_events()

        # 二维图聚类结果

        # 首先动态创建figure对象
        _2DCluster_BINSX = int(self.keyPara["le_2DCluster_Cloud_BinsX"])
        _2DCluster_BINSY = int(self.keyPara["le_2DCluster_Cloud_BinsY"])
        _2DCluster_XLEFT = self.keyPara["le_2DCluster_Cloud_Xleft"]
        _2DCluster_XRIGHT = self.keyPara["le_2DCluster_Cloud_Xright"]
        _2DCluster_YLEFT = self.keyPara["le_2DCluster_Cloud_Yleft"]
        _2DCluster_YRIGHT = self.keyPara["le_2DCluster_Cloud_Yright"]
        _2DCluster_VMIN = self.keyPara["le_2DCluster_Cloud_VMin"]
        _2DCluster_VMAX = self.keyPara["le_2DCluster_Cloud_VMax"]

        self._2DClusterFig = self.condCloudClusterCanvas.fig
        self._2DClusterFig.clf()
        if self.redraw == False:
            if (ClusterNGreat < 3):
                self._2DClusterFig.set_figwidth(ClusterNGreat * 5)
            # self._2DClusterFig.set_figheight(5)
            # self.condCloudClusterCanvas.updateGeometry()
            # self.condCloudClusterLayout.update()
        

        conductance, distance = self.conductance, self.distance
        self._2DAxesList = []
        for i in range(ClusterNGreat):
            index_i = np.where(labels == i)[0]
            Cluster_i_cond = conductance[index_i].reshape(-1)
            Cluster_i_dist = distance[index_i].reshape(-1)

            self._2DAxesList.append(self._2DClusterFig.add_subplot(1, ClusterNGreat, i + 1))
            self._2DAxesList[i].hist2d(
                Cluster_i_dist, Cluster_i_cond,
                bins=[_2DCluster_BINSX, _2DCluster_BINSY],
                range=[[_2DCluster_XLEFT, _2DCluster_XRIGHT],
                       [_2DCluster_YLEFT, _2DCluster_YRIGHT]],
                vmin=_2DCluster_VMIN,
                vmax=_2DCluster_VMAX,
                cmap=colorBarCmap[i % len(colorBarCmap)],
            )
            self._2DAxesList[i].set_title(f'Cluster {i + 1}: {len(index_i)}')
            self._2DAxesList[i].set_xlabel("Length/nm")
            if i == 0:
                self._2DAxesList[i].set_ylabel("Conductance/log(G/G$_0$)")

        self._2DClusterFig.tight_layout()
        self._2DClusterFig.canvas.draw()
        self._2DClusterFig.canvas.flush_events()

        logMsg = "Draw finished"
        self.addLogMsgWithBar(logMsg)
        self.keyPara["SaveData_Statue"] = True  # 这个true放在这里的目的是只要绘图完成一遍，就说明产生了新数据，可以保存
        self.ui.actSaveData.setEnabled(True)

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
        获取面板参数，目前处于 todo 状态
        :return:
        """
        keyPara = {}
        try:
            keyPara["cmb_Metric"] = self.ui.cmb_Metric.currentText()

            leObjList = []
            LINEEDIT_WIDGET_NEED_LIST = [self.ui.tw_BasicParams, self.ui.tw_FigureParams]
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

    def createFigure(self):
        """
        创建绘图对象
        :return:
        """
        self.condCloudOriCanvas = MyFigureCanvas()
        self.condCloudOriLayout.addWidget(self.condCloudOriCanvas)
        self.ui.grp_CondCloudOriginal.setLayout(self.condCloudOriLayout)

        self.clusterValidCanvas = MyFigureCanvas()
        self.clusterValidLayout.addWidget(self.clusterValidCanvas)
        self.ui.grp_ClusterValidation.setLayout(self.clusterValidLayout)

        self.condClusterCanvas = MyFigureCanvas()
        self.condClusterLayout.addWidget(self.condClusterCanvas)
        self.ui.grp_CondCluster.setLayout(self.condClusterLayout)

        self.condCloudClusterCanvas = MyFigureCanvas()
        self.condCloudClusterLayout.addWidget(self.condCloudClusterCanvas)
        self.ui.grp_CondCloudCluster.setLayout(self.condCloudClusterLayout)
        
        # self.condCloudClusterCanvas.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        self.logger.debug("Drawing window initialization is complete...")

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
    spectralClusterModule = QmySpectralClusterModule()
    spectralClusterModule.show()
    sys.exit(app.exec_())
