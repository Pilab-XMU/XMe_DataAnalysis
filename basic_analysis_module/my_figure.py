# -*- coding: utf-8 -*-
# @Time   : 2020/12/2 8:47
# @Author : Gang
# @File   : my_figure.py

from PyQt5.QtWidgets import QWidget, QSizePolicy
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MyFigureCanvas(FigureCanvas):
    def __init__(self,width=4,height=4,dpi=80):
        self.main_frame = QWidget()
        self.fig=Figure(figsize=(width,height),dpi=dpi)
        # self.fig=plt.figure(figsize=(width,height),dpi=dpi)
        # self.fig_canvas=FigureCanvas(self.fig)
        # self.fig_canvas.setParent(self.main_frame) 这两句没啥用
        self.axes=self.fig.add_subplot()
        super(MyFigureCanvas, self).__init__(self.fig)
        # 执行父类的初始化方法 相当于 FigureCanvas.__init__(self.fig)
        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
