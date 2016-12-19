from PyQt5.QtGui import QCursor

__author__ = 'user'
from PyQt5 import QtCore, QtWidgets
from SVGView import Ui_Dialog
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox, QLabel

class SVGDisplay(Ui_Dialog):
    """
    Create a small webkit based box to display schedule diagrams
    """
    def __init__(self,parent,svgFile, fullSched, sqlite_db):
        """
        Create the display box based on input parent widget and populated with
        svg file whose fully qualified path and filename must be passed
        """
        self._sched = fullSched
        self._sqlite_db = sqlite_db
        self._parent_dialog = parent
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
        sched = self.webView.selectedText()
        try: name = self._sched.getSchedName(sched, self._sqlite_db)
        except KeyError: return
        #Display label with description
        label = QLabel('<font style="color: grey; background-color: yellow"><p>' + name + '</p></font>')
        label.move(QCursor.pos().x()+30,QCursor.pos().y()+20)
        label.setWindowFlags(QtCore.Qt.SplashScreen)
        label.show()
        QTimer.singleShot(10000,label.destroy)
        #set schedule selected in main parent dialog to be that selected in the graph display
        try:
            self._parent_dialog.comboBoxSched.setCurrentText(sched) #Change display of combo box
            i = self._parent_dialog.findIndex(sched) # Where in selection combo list
            self._parent_dialog.comboBoxSched.setCurrentIndex(i)
            self._parent_dialog.tablePopulate(i) #Populate main display
        except TypeError : pass


