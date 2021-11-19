# -*- coding: utf-8 -*-
# @Time   : 2021/10/29 17:05
# @Author : Gang
# @File   : myAbout.py
import sys

from PyQt5.QtWidgets import QWidget, QApplication
from ui_QWAboutXMeWidget import Ui_QWAboutXMeWidget


class QmyAbout(QWidget):

    def __init__(self, parent=None):
        super(QmyAbout, self).__init__(parent)
        self.ui = Ui_QWAboutXMeWidget()
        self.ui.setupUi(self)
        text = self.ui.lbl_Title.text()
        newText = text.format(version="1.0.0")
        self.ui.lbl_Title.setText(newText)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    about = QmyAbout()
    about.show()
    sys.exit(app.exec_())
