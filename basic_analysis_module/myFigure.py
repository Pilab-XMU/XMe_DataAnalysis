# -*- coding: utf-8 -*-
# @Time   : 2020/12/2 8:47
# @Author : Gang
# @File   : myFigure.py

from PyQt5.QtWidgets import QWidget, QSizePolicy
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


class MyFigureCanvas(FigureCanvas):
    def __init__(self,width=4,height=4,dpi=80):
        self.main_frame = QWidget()
        self.fig=Figure(figsize=(width,height),dpi=dpi)
        # self.fig=plt.figure(figsize=(width,height),dpi=dpi)
        # self.fig_canvas=FigureCanvas(self.fig)
        # self.fig_canvas.setParent(self.main_frame) 这两句没啥用
        super(MyFigureCanvas, self).__init__(self.fig)
        # 执行父类的初始化方法 相当于 FigureCanvas.__init__(self.fig)
        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MyNavigationToolbar(NavigationToolbar):

    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        (None, None, None, None),
        ('Pan',
         'Left button pans, Right button zooms\n'
         'x/y fixes axis, CTRL fixes aspect',
         'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis, CTRL fixes aspect',
         'zoom_to_rect', 'zoom'),
        ("Customize", "Edit axis, curve and image parameters",
         "qt4_editor_options", "edit_parameters"),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure')
    )
