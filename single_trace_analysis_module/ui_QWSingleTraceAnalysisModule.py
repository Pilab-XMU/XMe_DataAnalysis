# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'single_trace_analysis_module/QWSingleTraceAnalysisModule.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_QWSingleTraceAnalysisModule(object):
    def setupUi(self, QWSingleTraceAnalysisModule):
        QWSingleTraceAnalysisModule.setObjectName("QWSingleTraceAnalysisModule")
        QWSingleTraceAnalysisModule.resize(775, 498)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/ico/images/pilab_logo.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        QWSingleTraceAnalysisModule.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget(QWSingleTraceAnalysisModule)
        self.centralwidget.setObjectName("centralwidget")
        self.grp_TracePreview = QtWidgets.QGroupBox(self.centralwidget)
        self.grp_TracePreview.setGeometry(QtCore.QRect(10, 10, 551, 381))
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        self.grp_TracePreview.setFont(font)
        self.grp_TracePreview.setObjectName("grp_TracePreview")
        self.horizontalSlider = QtWidgets.QSlider(self.centralwidget)
        self.horizontalSlider.setGeometry(QtCore.QRect(10, 400, 551, 16))
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.grp_Data_Statue = QtWidgets.QGroupBox(self.centralwidget)
        self.grp_Data_Statue.setGeometry(QtCore.QRect(570, 10, 191, 101))
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setBold(False)
        font.setWeight(50)
        self.grp_Data_Statue.setFont(font)
        self.grp_Data_Statue.setObjectName("grp_Data_Statue")
        self.layoutWidget = QtWidgets.QWidget(self.grp_Data_Statue)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 20, 171, 74))
        self.layoutWidget.setObjectName("layoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.layoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.le_Trace_Nums = QtWidgets.QLineEdit(self.layoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.le_Trace_Nums.sizePolicy().hasHeightForWidth())
        self.le_Trace_Nums.setSizePolicy(sizePolicy)
        self.le_Trace_Nums.setMinimumSize(QtCore.QSize(80, 20))
        self.le_Trace_Nums.setMaximumSize(QtCore.QSize(80, 20))
        self.le_Trace_Nums.setReadOnly(True)
        self.le_Trace_Nums.setObjectName("le_Trace_Nums")
        self.gridLayout.addWidget(self.le_Trace_Nums, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.le_Chosen_Nums = QtWidgets.QLineEdit(self.layoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.le_Chosen_Nums.sizePolicy().hasHeightForWidth())
        self.le_Chosen_Nums.setSizePolicy(sizePolicy)
        self.le_Chosen_Nums.setMinimumSize(QtCore.QSize(80, 20))
        self.le_Chosen_Nums.setMaximumSize(QtCore.QSize(80, 20))
        self.le_Chosen_Nums.setReadOnly(True)
        self.le_Chosen_Nums.setObjectName("le_Chosen_Nums")
        self.gridLayout.addWidget(self.le_Chosen_Nums, 1, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.le_Current_Index = QtWidgets.QLineEdit(self.layoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.le_Current_Index.sizePolicy().hasHeightForWidth())
        self.le_Current_Index.setSizePolicy(sizePolicy)
        self.le_Current_Index.setMinimumSize(QtCore.QSize(80, 20))
        self.le_Current_Index.setMaximumSize(QtCore.QSize(80, 20))
        self.le_Current_Index.setReadOnly(True)
        self.le_Current_Index.setObjectName("le_Current_Index")
        self.gridLayout.addWidget(self.le_Current_Index, 2, 1, 1, 1)
        self.grp_Save_Format = QtWidgets.QGroupBox(self.centralwidget)
        self.grp_Save_Format.setGeometry(QtCore.QRect(570, 120, 191, 111))
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.grp_Save_Format.setFont(font)
        self.grp_Save_Format.setObjectName("grp_Save_Format")
        self.tabWidget = QtWidgets.QTabWidget(self.grp_Save_Format)
        self.tabWidget.setGeometry(QtCore.QRect(0, 20, 191, 81))
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.layoutWidget1 = QtWidgets.QWidget(self.tab)
        self.layoutWidget1.setGeometry(QtCore.QRect(10, 10, 161, 25))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.layoutWidget1)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.rdo_Format_npz = QtWidgets.QRadioButton(self.layoutWidget1)
        self.rdo_Format_npz.setChecked(True)
        self.rdo_Format_npz.setObjectName("rdo_Format_npz")
        self.horizontalLayout.addWidget(self.rdo_Format_npz)
        self.rdo_Format_csv = QtWidgets.QRadioButton(self.layoutWidget1)
        self.rdo_Format_csv.setObjectName("rdo_Format_csv")
        self.horizontalLayout.addWidget(self.rdo_Format_csv)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.le_SaveFolder_Name = QtWidgets.QLineEdit(self.tab_2)
        self.le_SaveFolder_Name.setGeometry(QtCore.QRect(10, 10, 171, 23))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.le_SaveFolder_Name.sizePolicy().hasHeightForWidth())
        self.le_SaveFolder_Name.setSizePolicy(sizePolicy)
        self.le_SaveFolder_Name.setObjectName("le_SaveFolder_Name")
        self.tabWidget.addTab(self.tab_2, "")
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progressBar.setGeometry(QtCore.QRect(580, 380, 181, 16))
        self.progressBar.setStyleSheet("::chunk {background-color: rgb(18, 150, 219);}")
        self.progressBar.setProperty("value", 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setInvertedAppearance(False)
        self.progressBar.setTextDirection(QtWidgets.QProgressBar.TopToBottom)
        self.progressBar.setObjectName("progressBar")
        self.layoutWidget2 = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget2.setGeometry(QtCore.QRect(570, 250, 201, 121))
        self.layoutWidget2.setObjectName("layoutWidget2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.layoutWidget2)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.btn_Save_Current_Trace = QtWidgets.QPushButton(self.layoutWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_Save_Current_Trace.sizePolicy().hasHeightForWidth())
        self.btn_Save_Current_Trace.setSizePolicy(sizePolicy)
        self.btn_Save_Current_Trace.setMinimumSize(QtCore.QSize(80, 50))
        self.btn_Save_Current_Trace.setMaximumSize(QtCore.QSize(80, 50))
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.btn_Save_Current_Trace.setFont(font)
        self.btn_Save_Current_Trace.setObjectName("btn_Save_Current_Trace")
        self.gridLayout_2.addWidget(self.btn_Save_Current_Trace, 0, 0, 1, 1)
        self.btn_Drop_Current_Trace = QtWidgets.QPushButton(self.layoutWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_Drop_Current_Trace.sizePolicy().hasHeightForWidth())
        self.btn_Drop_Current_Trace.setSizePolicy(sizePolicy)
        self.btn_Drop_Current_Trace.setMinimumSize(QtCore.QSize(80, 50))
        self.btn_Drop_Current_Trace.setMaximumSize(QtCore.QSize(80, 50))
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.btn_Drop_Current_Trace.setFont(font)
        self.btn_Drop_Current_Trace.setObjectName("btn_Drop_Current_Trace")
        self.gridLayout_2.addWidget(self.btn_Drop_Current_Trace, 0, 1, 1, 1)
        self.btn_Last_Trace = QtWidgets.QPushButton(self.layoutWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_Last_Trace.sizePolicy().hasHeightForWidth())
        self.btn_Last_Trace.setSizePolicy(sizePolicy)
        self.btn_Last_Trace.setMaximumSize(QtCore.QSize(80, 40))
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.btn_Last_Trace.setFont(font)
        self.btn_Last_Trace.setObjectName("btn_Last_Trace")
        self.gridLayout_2.addWidget(self.btn_Last_Trace, 1, 0, 1, 1)
        self.btn_Next_Trace = QtWidgets.QPushButton(self.layoutWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_Next_Trace.sizePolicy().hasHeightForWidth())
        self.btn_Next_Trace.setSizePolicy(sizePolicy)
        self.btn_Next_Trace.setMaximumSize(QtCore.QSize(80, 40))
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        self.btn_Next_Trace.setFont(font)
        self.btn_Next_Trace.setObjectName("btn_Next_Trace")
        self.gridLayout_2.addWidget(self.btn_Next_Trace, 1, 1, 1, 1)
        QWSingleTraceAnalysisModule.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(QWSingleTraceAnalysisModule)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 775, 23))
        self.menubar.setObjectName("menubar")
        QWSingleTraceAnalysisModule.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(QWSingleTraceAnalysisModule)
        self.statusbar.setObjectName("statusbar")
        QWSingleTraceAnalysisModule.setStatusBar(self.statusbar)
        self.toolBar = QtWidgets.QToolBar(QWSingleTraceAnalysisModule)
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.toolBar.setObjectName("toolBar")
        QWSingleTraceAnalysisModule.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actOpenFiles = QtWidgets.QAction(QWSingleTraceAnalysisModule)
        self.actOpenFiles.setEnabled(True)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/png/images/openfile.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actOpenFiles.setIcon(icon1)
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        self.actOpenFiles.setFont(font)
        self.actOpenFiles.setObjectName("actOpenFiles")
        self.actSaveData = QtWidgets.QAction(QWSingleTraceAnalysisModule)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/png/images/save.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actSaveData.setIcon(icon2)
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        self.actSaveData.setFont(font)
        self.actSaveData.setVisible(True)
        self.actSaveData.setObjectName("actSaveData")
        self.actGuideSet = QtWidgets.QAction(QWSingleTraceAnalysisModule)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/png/images/guide1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actGuideSet.setIcon(icon3)
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        self.actGuideSet.setFont(font)
        self.actGuideSet.setObjectName("actGuideSet")
        self.actQuit = QtWidgets.QAction(QWSingleTraceAnalysisModule)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":/png/images/quit.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actQuit.setIcon(icon4)
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(9)
        self.actQuit.setFont(font)
        self.actQuit.setObjectName("actQuit")
        self.toolBar.addAction(self.actOpenFiles)
        self.toolBar.addAction(self.actSaveData)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actGuideSet)
        self.toolBar.addAction(self.actQuit)

        self.retranslateUi(QWSingleTraceAnalysisModule)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(QWSingleTraceAnalysisModule)

    def retranslateUi(self, QWSingleTraceAnalysisModule):
        _translate = QtCore.QCoreApplication.translate
        QWSingleTraceAnalysisModule.setWindowTitle(_translate("QWSingleTraceAnalysisModule", "SingleTraceAnalysis"))
        self.grp_TracePreview.setTitle(_translate("QWSingleTraceAnalysisModule", "Trace Preview"))
        self.grp_Data_Statue.setTitle(_translate("QWSingleTraceAnalysisModule", "Status"))
        self.label.setText(_translate("QWSingleTraceAnalysisModule", "Trace Nums"))
        self.le_Trace_Nums.setText(_translate("QWSingleTraceAnalysisModule", "0"))
        self.label_2.setText(_translate("QWSingleTraceAnalysisModule", "Chosen Nums"))
        self.le_Chosen_Nums.setText(_translate("QWSingleTraceAnalysisModule", "0"))
        self.label_3.setText(_translate("QWSingleTraceAnalysisModule", "Cur Index"))
        self.le_Current_Index.setText(_translate("QWSingleTraceAnalysisModule", "0"))
        self.grp_Save_Format.setTitle(_translate("QWSingleTraceAnalysisModule", "Save Setting"))
        self.rdo_Format_npz.setText(_translate("QWSingleTraceAnalysisModule", "npz"))
        self.rdo_Format_csv.setText(_translate("QWSingleTraceAnalysisModule", "csv"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("QWSingleTraceAnalysisModule", "Format"))
        self.le_SaveFolder_Name.setText(_translate("QWSingleTraceAnalysisModule", "SingleTraceAnalysis"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("QWSingleTraceAnalysisModule", "Name"))
        self.btn_Save_Current_Trace.setText(_translate("QWSingleTraceAnalysisModule", "Retain"))
        self.btn_Drop_Current_Trace.setText(_translate("QWSingleTraceAnalysisModule", "Discard"))
        self.btn_Last_Trace.setText(_translate("QWSingleTraceAnalysisModule", "Last"))
        self.btn_Next_Trace.setText(_translate("QWSingleTraceAnalysisModule", "Next"))
        self.toolBar.setWindowTitle(_translate("QWSingleTraceAnalysisModule", "toolBar"))
        self.actOpenFiles.setText(_translate("QWSingleTraceAnalysisModule", "Open"))
        self.actOpenFiles.setToolTip(_translate("QWSingleTraceAnalysisModule", "open files"))
        self.actOpenFiles.setShortcut(_translate("QWSingleTraceAnalysisModule", "Ctrl+O"))
        self.actSaveData.setText(_translate("QWSingleTraceAnalysisModule", "Save"))
        self.actSaveData.setToolTip(_translate("QWSingleTraceAnalysisModule", "save data"))
        self.actGuideSet.setText(_translate("QWSingleTraceAnalysisModule", "UseGuide"))
        self.actGuideSet.setToolTip(_translate("QWSingleTraceAnalysisModule", "use guide"))
        self.actQuit.setText(_translate("QWSingleTraceAnalysisModule", "Quit"))
        self.actQuit.setToolTip(_translate("QWSingleTraceAnalysisModule", "quit"))
        self.actQuit.setShortcut(_translate("QWSingleTraceAnalysisModule", "Alt+Q"))
import images_rc
