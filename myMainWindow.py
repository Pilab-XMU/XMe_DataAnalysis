# -*- coding: utf-8 -*-
# @Time   : 2020/11/10 21:11
# @Author : Gang
# @File   : myMainWindow.py

import sys

from PyQt5.QtWidgets import QMainWindow,QApplication
from PyQt5.QtCore import pyqtSlot

from ui_MainWindow import Ui_MainWindow
from myBasicAnalysisModule import QmyBasicAnalysisModule

class QmyMainWindow(QMainWindow):
    def __init__(self,parent=None):
        super(QmyMainWindow, self).__init__(parent)
        self.ui=Ui_MainWindow()
        self.ui.setupUi(self)

# ==========定义按钮对应唤醒的功能模块=============

    @pyqtSlot()  ## 基础分析模块
    def on_btn_BasicAnalysis_clicked(self):
        basicAnalysisModule=QmyBasicAnalysisModule(self)
        basicAnalysisModule.show()



if __name__ == '__main__':
    app=QApplication(sys.argv)
    mainWindow=QmyMainWindow()
    mainWindow.show()
    sys.exit(app.exec_())