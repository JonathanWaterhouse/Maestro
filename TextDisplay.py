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
        self.findPushButton.clicked.connect(self.find)
        self.plainTextEdit.cursorPositionChanged.connect(self.set_new_cursor)
        self._search_text = ''
        self._first_search = True
        count = 0
        for t in text:
            count += 1
            self.plainTextEdit.insertPlainText(t)
        self.countLabel.setText(repr(count) + ' lines')
        self.plainTextEdit.moveCursor(QTextCursor.Start)
        dlg.setVisible(True)
        dlg.exec_()

    def find(self):
        """
        Every time search is done this method will be called
        This method does two things
        a) for first time of search for a new search text it highlights all occurrences so that they are easily visible
        b) Successive searches for the search text cycle through occurrences, moving the whole text so current found
        value is in view.
        It has been found necessary to set focus on the plainTextView in order that the cursor in point b) be visible for
        the current position in the text.
        @return:
        """

        ### Do Some setup ###
        self.plainTextEdit.setFocus() #reguired so cursor shows up when tabbing through data found in search
        self.plainTextEdit.centerOnScroll = True
        cursor = self.plainTextEdit.textCursor()
        # Setup the desired format for matches
        format = QTextCharFormat()
        format.setBackground(QBrush(QColor(0,255,150,180))) # (R,G,G, transparency)
        srchTxt = self.lineEdit.text().upper()
        if srchTxt == '':
            self.countLabel.setText('Please select some text to search for')
            return
        # reset all previous search highlighting, move cursor to beginning of document
        if srchTxt != self._search_text:
            no_format = QTextCharFormat() # reset all formatting from any previous searches
            no_format.setBackground(QBrush(QColor(0,0,0,0)))
            cursor.setPosition(0) # Apply from start to end of document
            cursor.setPosition(len(self.plainTextEdit.toPlainText()),QTextCursor.KeepAnchor)
            cursor.setCharFormat(no_format)
            curr_cursor = self.plainTextEdit.textCursor() # Ensure we start search at beginning of document
            curr_cursor.setPosition(0)
            self.plainTextEdit.setTextCursor(curr_cursor)
            self._search_text = srchTxt #This step is critical, we now assign the variable with the current search
            self._first_search = True # It was a new search text, therefore its first time

        ### Now highlight all occurrences of the search text in the document ###
        regex = QRegExp(srchTxt)
        pos, count = 0, 0
        index = regex.indexIn(self.plainTextEdit.toPlainText().upper(), pos)
        #First highlight all occurrences of the search term for easy visibility
        while (index != -1 and self._first_search):
            cursor.setPosition(index)
            cursor.setPosition(index+len(srchTxt),QTextCursor.KeepAnchor) #so cursor has selected from start to end of text
            cursor.mergeCharFormat(format)
            # Move to the next match
            pos = index + regex.matchedLength()
            index = regex.indexIn(self.plainTextEdit.toPlainText().upper(), pos)
            count += 1
        # set the message box to show number items found only on first time for new srchTxt or will get set to 0
        if self._first_search: self.countLabel.setText(repr(count) + ' occurrences of searched for text')
        self._first_search = False

        ### Move cursor through text occurrences ###
        self.plainTextEdit.setCurrentCharFormat(format)
        if not self.plainTextEdit.find(srchTxt): #This statement moves the cursor
            #Next statements move to beginning of document and restart the search, moving cursor to first instance
            self.plainTextEdit.moveCursor(QTextCursor.Start,QTextCursor.MoveAnchor)
            self.plainTextEdit.find(srchTxt)

    def set_new_cursor(self):
        """
        Set new cursor position in plainTextEdit widget if user selects a position with the mouse
        @return:
        """
        curr_cursor = self.plainTextEdit.textCursor()
        self.plainTextEdit.setTextCursor(curr_cursor)
        return