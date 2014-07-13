__author__ = 'user'
from PyQt5 import QtCore, QtWidgets
from SVGView import Ui_Dialog
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox, QLabel

class SVGDisplay(Ui_Dialog):
    """
    Create a small webkit based box to display schedule diagrams
    """
    def __init__(self,parent,svgFile,fullSched):
        """
        Create the display box based on input parent widget and populated with
        svg file whose fully qualified path and filename must be passed
        """
        self._sched = fullSched
        dlg = QtWidgets.QDialog()
        self.setupUi(dlg)
        imageUrl = QtCore.QUrl.fromLocalFile(svgFile) # Fully qualified filename
        self.webView.load(imageUrl)
        self.webView.setZoomFactor(0.5)
        self.horizontalSlider.setValue(50)
        self.horizontalSlider.valueChanged.connect(self.magnification)
        self.webView.selectionChanged.connect(self.showDetails)
        dlg.setVisible(True)
        dlg.exec_()

    def magnification(self):
        self.webView.setZoomFactor(self.horizontalSlider.sliderPosition()/100)

    def showDetails(self):
        msg = QMessageBox()
        try: name = self._sched.getSchedName(self.webView.selectedText())
        except KeyError: return
        #msg.setText(name)
        #msg.setIcon(QMessageBox.Information)
        #msg.setStandardButtons(QMessageBox.Close)
        #msg.setDefaultButton(QMessageBox.Close)
        #rc = msg.exec()
        label = QLabel("<font color=grey size=15><p>" + name + "</p></font>")
        label.setWindowFlags(QtCore.Qt.SplashScreen)
        label.show()
        QTimer.singleShot(5000,label.destroy)
        #label.exec()

