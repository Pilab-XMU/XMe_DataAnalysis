# -*- coding: utf-8 -*-
# @Time   : 2021/9/26 9:38
# @Author : Gang
# @File   : psdStaticFigure.py
from PyQt5.QtWidgets import QWidget, QSizePolicy
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


class MyFigureCanvas(FigureCanvas):
    def __init__(self, width=8, height=6, dpi=100):
        self.mainFrame = QWidget()
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MyFigureCanvas, self).__init__(self.fig)
        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MyNavigationToolbar(NavigationToolbar):
    # 直接粗暴的重写！！
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


