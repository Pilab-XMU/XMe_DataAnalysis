# -*- coding: utf-8 -*-
# @Time   : 2020/12/18 10:39
# @Author : Gang
# @File   : mySingleTraceAnalysisModule.py
import sys
import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QVBoxLayout

from ui_QWSingleTraceAnalysisModule import Ui_QWSingleTraceAnalysisModule
from other_function_single import *

class QmySingleTraceAnalysisModule(QMainWindow):


    def __init__(self,parent=None):
        super(QmySingleTraceAnalysisModule, self).__init__(parent)
        self.ui=Ui_QWSingleTraceAnalysisModule()
        self.ui.setupUi(self)
        self.init_widget_para()

    def init_widget_para(self):
        self.ui.actSaveFinalData.setEnabled(False)
        self.ui.btn_Save_Current_Trace.setEnabled(False)
        self.ui.btn_Drop_Current_Trace.setEnabled(False)
        self.ui.btn_Last_Trace.setEnabled(False)
        self.ui.btn_Next_Trace.setEnabled(False)
        self._single_curve_layout=QVBoxLayout(self)

        self.file_path=""
        self.save_file_path=""
        self.condutance=None
        self.distance=None
        self.additional_length=None
        self.IS_SELECT_ARRAR=None
        self.TRACE_NUM=None
        self.CURRENT_INDEX=None
        self.SELECT_COUNT=None
        self.save_filt="npz Files(*.npz)"

        self.create_figure()

    # =============== 控件触发函数===============
    @pyqtSlot()
    def on_actQuit_triggered(self):
        self.close()

    @pyqtSlot()
    def on_actSaveFinalData_triggered(self):
        """
        保存筛选之后的数据
        :return: 无返回值
        """
        dlg_title = "提示"
        str_info = f"已选定{self.SELECT_COUNT} 条数据，确认保存？"
        reply = QMessageBox.question(self, dlg_title, str_info,
                                    QMessageBox.Yes | QMessageBox.Cancel,
                                    QMessageBox.Yes)
        if reply==QMessageBox.Yes:
            self.get_save_filt()
            dlg_title_1 = "保存文件"
            filt = self.save_filt  # 文件过滤器
            save_dir=os.path.dirname(self.file_path)
            STATUE=False
            while not STATUE:
                self.save_file_path, _=QFileDialog.getSaveFileName(self,dlg_title_1,save_dir,filt)
                if self.save_file_path==self.file_path:
                    QMessageBox.warning(self,"警告","为了不覆盖原有文件，自动存储为后缀为当前时间的新文件")
                    self.save_file_path=self.get_save_path_with_time()
                    break
                STATUE=False if self.save_file_path== "" else True
                if not STATUE:
                    result = QMessageBox.warning(self, "警告", "取消保存吗？", QMessageBox.Ok | QMessageBox.Cancel,
                                                 QMessageBox.Ok)
                    if result == QMessageBox.Ok:
                        break
                else:
                    try:
                        self.save_select_data()
                    except Exception as e:
                        print(f"发生错误：{e}")
                    else:
                        QMessageBox.information(self,"通知","筛选数据已保存成功！")

    @pyqtSlot()
    def on_actOpenFiles_triggered(self):
        """
        打开按钮，目前暂只支持单个goodtrace的查看
        :return: 无返回值
        """
        dlg_title = "选择一个单条数据文件"  # 对话框标题
        filt = "npz Files(*.npz)"  # 文件过滤器
        desptop_path = get_desktop_path()
        load_statue = False
        while not load_statue:
            file_path, _ = QFileDialog.getOpenFileName(self, dlg_title, desptop_path, filt)
            load_statue = False if file_path=="" else True
            if not load_statue:
                result = QMessageBox.warning(self, "警告", "请选择一个文件!", QMessageBox.Ok | QMessageBox.Cancel,
                                             QMessageBox.Ok)
                if result == QMessageBox.Cancel:
                    break
            else:
                # 当程序执行到这里，说明成功加载，初始化数据，显示第一条单条
                self.file_path=file_path
                self.init_dataset(file_path)
                self.init_first_curve()
                self.draw_fig()

                if self.CURRENT_INDEX==self.TRACE_NUM-1:
                    self.ui.btn_Next_Trace.setEnabled(False)
                else:
                    self.ui.btn_Next_Trace.setEnabled(True)


                self.ui.btn_Save_Current_Trace.setEnabled(True)
                self.ui.actSaveFinalData.setEnabled(True)

    @pyqtSlot()
    def on_btn_Next_Trace_clicked(self):
        self.CURRENT_INDEX+=1
        if self.CURRENT_INDEX == self.TRACE_NUM-1:
            self.ui.btn_Next_Trace.setEnabled(False)

        index=self.CURRENT_INDEX
        self.ui.btn_Last_Trace.setEnabled(True)
        self.ui.horizontalSlider.setValue(index)
        self.ui.progressBar.setValue(index)
        self.ui.le_Current_Index.setText(str(index+1))
        self.draw_fig()

        if self.IS_SELECT_ARRAR[index]==0:
            self.ui.btn_Save_Current_Trace.setEnabled(True)
            self.ui.btn_Drop_Current_Trace.setEnabled(False)
        else:
            self.ui.btn_Save_Current_Trace.setEnabled(False)
            self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_btn_Last_Trace_clicked(self):
        self.CURRENT_INDEX-=1
        if self.CURRENT_INDEX==0:
            self.ui.btn_Last_Trace.setEnabled(False)

        index = self.CURRENT_INDEX
        self.ui.btn_Next_Trace.setEnabled(True)
        self.ui.horizontalSlider.setValue(index)
        self.ui.progressBar.setValue(index)
        self.ui.le_Current_Index.setText(str(index + 1))
        self.draw_fig()

        if self.IS_SELECT_ARRAR[index]==0:
            self.ui.btn_Save_Current_Trace.setEnabled(True)
            self.ui.btn_Drop_Current_Trace.setEnabled(False)
        else:
            self.ui.btn_Save_Current_Trace.setEnabled(False)
            self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_actOperateGuide_triggered(self):
        pass

    @pyqtSlot(int)
    def on_horizontalSlider_valueChanged(self,value):
        self.CURRENT_INDEX=value
        self.ui.le_Current_Index.setText(str(value + 1))
        self.ui.progressBar.setValue(value)
        self.draw_fig()

        if self.IS_SELECT_ARRAR[value]==0:
            self.ui.btn_Save_Current_Trace.setEnabled(True)
            self.ui.btn_Drop_Current_Trace.setEnabled(False)
        else:
            self.ui.btn_Save_Current_Trace.setEnabled(False)
            self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_rdo_Format_csv_clicked(self):
        dlg_title = "提示"
        str_info = "建议采用默认数据存储格式 npz \n确认修改吗？"
        reply = QMessageBox.warning(self, dlg_title, str_info,
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.No:
            self.ui.rdo_Format_npz.setChecked(True)

    @pyqtSlot()
    def on_btn_Save_Current_Trace_clicked(self):
        index=self.CURRENT_INDEX
        self.IS_SELECT_ARRAR[index]=1
        self.SELECT_COUNT+=1
        self.ui.le_Select_Trace_Num.setText(str(self.SELECT_COUNT))
        self.ui.btn_Save_Current_Trace.setEnabled(False)
        self.ui.btn_Drop_Current_Trace.setEnabled(True)

    @pyqtSlot()
    def on_btn_Drop_Current_Trace_clicked(self):
        index = self.CURRENT_INDEX
        self.IS_SELECT_ARRAR[index] = 0
        self.SELECT_COUNT -= 1
        self.ui.le_Select_Trace_Num.setText(str(self.SELECT_COUNT))
        self.ui.btn_Save_Current_Trace.setEnabled(True)
        self.ui.btn_Drop_Current_Trace.setEnabled(False)

    def closeEvent(self, event):
        """
        重写窗口关闭函数
        :param event: 无
        :return: 无
        """
        dlg_title = "警告"
        str_info = "确定退出吗?"
        reply = QMessageBox.question(self, dlg_title, str_info,
                                     QMessageBox.Yes | QMessageBox.Cancel,
                                     QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            time.sleep(0.1)
            event.accept()
        else:
            event.ignore()

    # =============== 控件触发函数===============

    def init_dataset(self,file_path):
        """
        初始化数据集，针对读取的数据将参数初始化
        :param file_path: goodtrace文件路径
        :return:
        """
        dataset = np.load(file_path)
        self.condutance, self.distance, self.additional_length = dataset['condutance_array'], dataset['distance_array'], int(
            dataset["additional_length"])
        self.ui.le_DataPath.setText(file_path)
        self.IS_SELECT_ARRAR = np.zeros(self.condutance.shape[0],dtype=np.int)
        self.TRACE_NUM = self.condutance.shape[0]
        self.CURRENT_INDEX=0
        self.SELECT_COUNT=0

    def init_first_curve(self):
        """
        根据读取进来数据的信息设置面板上的初始化参数
        :return:
        """
        self.ui.horizontalSlider.setMaximum(self.TRACE_NUM-1)
        self.ui.progressBar.setMaximum(self.TRACE_NUM-1)
        self.ui.horizontalSlider.setValue(0)
        self.ui.progressBar.setValue(0)
        self.ui.le_ALL_Tracce_Num.setText(str(self.TRACE_NUM))
        self.ui.le_Current_Index.setText(str(self.CURRENT_INDEX+1))
        self.ui.le_Select_Trace_Num.setText(str(self.SELECT_COUNT))

    def create_figure(self):
        """
        在程序ui建立的初期，就创建Figure()，后面不断地刷新即可
        :return:
        """
        self.fig=Figure()
        fig_canvas=FigureCanvas(self.fig)
        self._single_curve_layout.addWidget(fig_canvas)
        self.ui.grp_Single_Trace.setLayout(self._single_curve_layout)

    def draw_fig(self):
        """
        刷新式绘图
        :return:
        """
        self.fig.clf()
        current_index=self.CURRENT_INDEX
        condutance,distance=self.condutance[current_index], self.distance[current_index]
        ax = self.fig.add_subplot()
        ax.plot(distance,condutance)
        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def get_save_path_with_time(self):
        """
        用户选择覆盖旧文件的时候，给他创建一个时间后缀的新文件保存，避免覆盖
        :return:
        """
        time=get_current_time()
        dir=os.path.dirname(self.file_path)
        base_name=os.path.basename(self.file_path)
        file_name=base_name.split(".")[0]
        suffix=base_name.split(".")[1]
        base_name_new=file_name+"_"+time+"."+suffix
        return os.path.join(dir,base_name_new)

    def save_select_data(self):
        """
        保存数据函数的实现
        :return:
        """
        save_file_path = self.save_file_path
        select_index = np.where(self.IS_SELECT_ARRAR == 1)[0]
        condutance_select, distance_select, additional_length = self.condutance[select_index], self.distance[
            select_index], self.additional_length
        if self.ui.rdo_Format_npz.isChecked():
            np.savez(save_file_path,distance_array=distance_select, condutance_array=condutance_select,additional_length=additional_length)
        else:
            csv_data=self.get_csv_data(condutance_select,distance_select)
            np.savetxt(save_file_path,csv_data,delimiter=",")

    def get_csv_data(self,condutance_select, distance_select):
        """
        获取csv格式的数据并返回
        :param condutance_select: 
        :param distance_select:
        :return:
        """
        rows=condutance_select.shape[0]
        cols=condutance_select.shape[1]
        dataset=np.zeros((rows*2,cols))
        for i in range(rows):
            dataset[i*2,:]=distance_select[i,:]
            dataset[i*2+1,:]=condutance_select[i,:]
        return dataset.T

    def get_save_filt(self):
        """
        无参数
        :return: 在存储数据前获取存储的格式
        """
        if self.ui.rdo_Format_npz.isChecked():
            self.save_filt="npz Files(*.npz)"
        else:
            self.save_filt="csv Files(*.csv)"


if __name__ == '__main__':
    app = QApplication(sys.argv)
    basicAnalysisModule = QmySingleTraceAnalysisModule()
    basicAnalysisModule.show()
    sys.exit(app.exec_())
