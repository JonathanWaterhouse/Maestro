from PyQt5.QtCore import *
from PyQt5.QtWidgets import QApplication

__author__ = 'user'
class JobTableModel(QAbstractTableModel):
    """
    Subclass QAbstractTableModel to provide a table model representing
    the data in the jobs for a schedule so it can be displayed in a QTableView
    """
    def __init__(self, datain, parent = None, *args):
        #QAbstractTableModel.__init__(self,parent,*args)
        QAbstractTableModel.__init__(self,parent=None,*args)
        self._datain = datain

    def rowCount(self,parent):
        return len(self._datain)

    def columnCount(self,parent): return 3

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return (self._datain[index.row()][index.column()])

class ScheduleTableModel(QAbstractTableModel):
    """
    Subclass QAbstractTableModel to provide a table model representing
    the data in the preceding schedules for a schedule so it can be displayed in a QTableView
    """
    def __init__(self, datain, parent = None, *args):
        """
        datain is a list of 2-tuples [(schedule,schedule name)]
        """
        #QAbstractTableModel.__init__(self,parent,*args)
        QAbstractTableModel.__init__(self,parent = None,*args)
        self._datain = datain

    def rowCount(self,parent):
        return len(self._datain)

    def columnCount(self,parent): return 2

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return (self._datain[index.row()][index.column()])

class KeyPressEater(QObject):
    """
    This class is to be used as part of a mechanism to trap CTRL-C on table view
    to allow screen print of all table data
    """
    def eventFilter(self, tableView, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_C and (event.modifiers() & Qt.ControlModifier):
                print("Ate key press CTRL-C")
                #Allow screen print
                cb = QApplication.clipboard()
                screenData = []
                #Force selection of all cells (User manually selecting them did not appear to work)
                tableView.selectAll()
                for index in tableView.selectionModel().selectedIndexes():
                    if index.column() == 0: screenData.append('\n' + index.data() + '\t')
                    else: screenData.append(index.data() + '\t')
                cb.setText("".join(screenData))
                tableView.clearSelection() #Unselect all cells
                return True
            else: return False
        else:
            return False