__author__ = 'user'
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtNetwork import *
from SVGView import Ui_Dialog
from PyQt5.QtWebKit import *
from PyQt5.QtPrintSupport import *

class SVGDisplay(Ui_Dialog):
    """
    Create a small webkit based box to display schedule diagrams
    """
    def __init__(self,parent,svgFile):
        """
        Create the display box based on input parent widget and populated with
        svg file whose fully qualified path and filename must be passed
        """
        dlg = QtWidgets.QDialog()
        self.setupUi(dlg)
        imageUrl = QtCore.QUrl.fromLocalFile(svgFile) # Fully qualified filename
        self.webView.load(imageUrl)
        self.webView.setZoomFactor(0.5)
        self.horizontalSlider.setValue(50)
        self.horizontalSlider.valueChanged.connect(self.magnification)
        dlg.setVisible(True)
        dlg.exec_()

    def magnification(self):
        self.webView.setZoomFactor(self.horizontalSlider.sliderPosition()/100)

