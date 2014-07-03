__author__ = 'Jon Waterhouse'
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from TextDisplayUI import Ui_Dialog

class TextDisplay(Ui_Dialog):
    """
    Create a small text box to display various information
    """
    def __init__(self, parent, text):
        """
        Create the text box based on QObject parent and populated with
        lines from the list of text text
        """
        dlg = QDialog()
        self.setupUi(dlg)
        self.plainTextEdit.setReadOnly(True)
        self.lineEdit.returnPressed.connect(self.find)
        count = 0
        for t in text:
            count += 1
            self.plainTextEdit.insertPlainText(t)
        self.countLabel.setText(repr(count) + ' lines')
        self.plainTextEdit.moveCursor(QTextCursor.Start)
        dlg.setVisible(True)
        dlg.exec_()

    def find(self):
        cursor = self.plainTextEdit.textCursor()
        # Setup the desired format for matches
        format = QTextCharFormat()
        format.setBackground(QBrush(QColor("red")))
        #Setup regex
        srchTxt = self.lineEdit.text()
        regex = QRegExp(srchTxt)
        # Process the displayed document
        pos, count = 0, 0
        index = regex.indexIn(self.plainTextEdit.toPlainText(), pos)
        while (index != -1):
            # Select the matched text and apply the desired format
            cursor.setPosition(index)
            cursor.setPosition(index+len(srchTxt),QTextCursor.KeepAnchor)
            cursor.mergeCharFormat(format)
            # Move to the next match
            pos = index + regex.matchedLength()
            index = regex.indexIn(self.plainTextEdit.toPlainText(), pos)
            count += 1
        self.countLabel.setText(repr(count) + ' ocurrences of searched for text')
