import os
import sqlite3
import subprocess

from MainUI import Ui_MainWindow
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import *
from SVGDisplay import *
from Schedule import Schedule
from TableModels import *
from TextDisplay import *

__author__ = 'Jonathan Waterhouse'

#class MaestroUi(Ui_MainWindow, QMainWindow):
class MaestroUi(Ui_MainWindow):
    """
    This class inherits from a gui class design using QTDesigner and is designed
    to isolate change to the gui layout from any code which deals with user interaction
    and data display. The key to populating the GUI with data is to populate the
    schedule combo Box, everything else will cascade from that eg. schedule defines
    contents of Table view etc.
    """
    def __init__(self, mainWindow):
        """
        Retrieve Stored locations of Maestro and Job files if they have been saved previously.
        With those names, read the schedule and job files and store as an internal object
        accessible via self.getSched. If the locations have not been previously stored output
        a message asking for them to be selected.
        """
        #Setup main window
        #QMainWindow.__init__(self)
        self.setupUi(MainWindow)
        self.fileSchedule.setText("Read New Runbook Files")
        self.otherGuiSetup()
        #Setup some internally required file locations
        dataDir = self.getDataDir()
        dataDir = self.getDataDir() + os.sep
        self._sqlite_ini_name = 'ini.db'
        self._graphvizTxtFile = dataDir + "Graphviz.txt"
        self._graphvizSvgFile = dataDir + "Graphviz.svg"
        self._db = dataDir + 'schedule.db'
        self._icon = 'Monitor_Screen_32xSM.png'
        self._s = Schedule()
        #Populate GUI with data
        try:
            self.getData()
        except(KeyError):
            return
        self.popSchedsCombo()

    def getDataDir(self):
        """
        This application may have a windows executable built from it using cx_Freeze in
        which case the local directly that the script runs from assumed by python
        will be incorrect. Here we derive the data directory. This allows the ini file
        Maestro.ini to be found and intermediate files for Graphviz
        """
        if getattr(sys, 'frozen', False):
        # The application is frozen
            datadir = os.path.dirname(sys.executable)
        else:
        # The application is not frozen
        # Change this bit to match where you store your data files:
            datadir = os.getcwd()

        return datadir

    def getData(self):
        """
        Check schedule database exists. This is done when this class is initialised.
        :return: None
        """
        #Setup an ini.db file for various stored values if it does not exist
        conn = sqlite3.connect(self._sqlite_ini_name)
        c = conn.cursor()
        # Settings database
        c.execute("CREATE TABLE IF NOT EXISTS SETTINGS (KEY TEXT PRIMARY KEY, VALUE TEXT)")
        conn.commit()
        conn.close()
        #Read schedule text files into database table if such table does not exist
        if not os.path.exists(self._db):
            msg = QMessageBox()
            msg.setWindowIcon(QIcon(self._icon))
            msg.setWindowTitle('Maestro')
            msg.setText("Error")
            msg.setIcon(QMessageBox.Critical)
            msg.setInformativeText("Schedule files not yet loaded. Please select them.")
            msg.exec()

            self.getSchedFileNames()  # prompt for new files names and load database
            return

    def otherGuiSetup(self):
        """ Do other setup things required to get the static GUI components set up, and
        components acting correctly upon user interaction. There should NOT be any
        code associated with date reading or population in here.
        """
        self.fileSchedule.triggered.connect(self.getSchedFileNames) #File menu option to look up data file names
        self.exportAction.triggered.connect(self.exportDirectConnections) #File menu option to export current schedule direct dependencies
        self.exportFullConnectionAction.triggered.connect(self.exportFullConnections) #File menu option to export current schedule full connection Map
        self.actionSetDotLoc.triggered.connect(self.setDotLoc) #File menu option to export current schedule
        self.actionShowFullSchedule.triggered.connect(self.showFullSchedule) #File menu option to export current schedule
        self.actionShowCalendars.triggered.connect(self.showFullCalendar)#File menu option to display all calendars
        self.actionFile_Locations.triggered.connect(self.fileInfo) #Options menu, display file names selected
        self.actionCtrl_File_Deps.triggered.connect(self.show_ctrl_file_deps) # File menu, display dependencies of a given control file
        self.actionResource_Dependencies.triggered.connect(self.show_resource_deps) #File menu display resource succ. deps
        #Connect combo box selection to table population
        self.comboBoxSched.activated.connect(self.tablePopulate)
        self.comboBoxSched.currentIndexChanged.connect(self.tablePopulate)
        self.comboBoxSched.editTextChanged.connect(self.findIndex)
        self.comboBoxSched.highlighted.connect(self.tablePopulate)
        #Ensure that a change in the radio button leads to re-population of table view
        self.buttonGroup.buttonClicked[int].connect(self.handleBGChange)
        self.tableView.clicked.connect(lambda: self.tableClicked(self.tableView))
        self.tableView.activated.connect(lambda: self.tableClicked(self.tableView))
        #Connect find processing
        self.lineEditFind.returnPressed.connect(self.findText)

    def getSchedFileNames(self):
        """Allow selection of the schedule and job file names from the ui.
        Displays in succession file dialogs to allow selection of schedule file from
        Maestro followed by the job file. The full paths are serialised in a pickle file
        so that they are available for future runs of the program, until next changed.
        File specification is performed via the File menu on the gui.
        """
        w = QWidget()
        s = QFileDialog.getOpenFileName(w,"Select SCHEDULE file")[0]
        j = QFileDialog.getOpenFileName(w,"Select JOB file")[0]
        cal = QFileDialog.getOpenFileName(w,"Select CALENDAR file")[0]
        #Check Files actually exist - will be an issue in case of cancellation first time in
        msg_text = ''
        if not os.path.exists(s): msg_text = 'SCHEDULE file ' + s + ' does not exist.'
        if not os.path.exists(s): msg_text = 'JOBS file ' + j + ' does not exist.'
        if not os.path.exists(cal): msg_text = 'CALENDAR file ' + cal + ' does not exist.'
        if msg_text != '': #ie. no file chosen in one of the 3 cases
            msg = QMessageBox()
            msg.setWindowIcon(QIcon(self._icon))
            msg.setWindowTitle('Maestro')
            msg.setText(msg_text)
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return
        #Store values for later use if we got valid file names
        conn = sqlite3.connect(self._sqlite_ini_name)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('SCHEDULE', str(s)))
        c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('JOBS', str(j)))
        c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('CALENDARS', str(cal)))
        conn.commit()
        conn.close()
        self.statusbar.showMessage('Populating database........please wait.')
        self._s.read_runbook_files(self._sqlite_ini_name, self._db, self._icon)#Read in schedule and job files to pop. schedule object.
        self.statusbar.showMessage('Database population complete.',1000)
        self.popSchedsCombo()
        self.comboBoxSched.activateWindow()

    def setDotLoc(self):
        """Allow selection of the dot executable location on the windows workstation. This
        must have been installed first. Displays  file dialog to allow selection of file.
        The full paths are serialised in a pickle file so that they are available for
        future runs of the program, until next changed.
        File specification is performed via the File menu on the gui.
        """
        w = QWidget()
        dotLoc = QFileDialog.getOpenFileName(w,"SELECT DOT EXECUTABLE FILE")[0]
        if dotLoc != "":  #Allow cancellation and retain current value
            # Store values for later use
            conn = sqlite3.connect(self._sqlite_ini_name)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('DOT', str(dotLoc)))
            conn.commit()
            conn.close()
        return dotLoc

    def fileInfo(self):
        """Output a message box with the fully qualified paths and names of the  current
        Maestro schedule and job files that are selected"""
        files = {}
        conn = sqlite3.connect(self._sqlite_ini_name)         # Settings database
        c = conn.cursor()
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='DOT'")
        files['DOT'] = c.fetchone()[0]
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='SCHEDULE'")
        files['SCHEDULE'] = c.fetchone()[0]
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='JOBS'")
        files['JOBS'] = c.fetchone()[0]
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='CALENDARS'")
        files['CALENDARS'] = c.fetchone()[0]
        msg = QMessageBox()
        msg.setWindowIcon(QIcon(self._icon))
        msg.setWindowTitle('Maestro')
        msg.setText("File Locations........")
        txtList = []
        try:
            for k, v in files.items(): txtList.append(k + ": " + v + "\n")
            txt = "\n".join(txtList)
        except AttributeError: txt = "No initialisations yet performed"
        msg.setInformativeText(txt)
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def popSchedsCombo(self):
        """ Populate the schedule combo box with all schedule names sorted alphabetically """
        display = [k for k in self._s.getAllSchedIds(self._db)]
        display.sort()
        self.comboBoxSched.addItems(display)

    def handleBGChange(self):
        txt = self.comboBoxSched.currentText()
        if self.comboBoxSched.findText(txt) != -1:
            self.tablePopulate(self.comboBoxSched.findText(txt))

    def findIndex (self, txt):
        if self.comboBoxSched.findText(txt) != -1:
            self.tablePopulate(self.comboBoxSched.findText(txt))

    def tablePopulate(self, index):
        """
        Populate table view depending on selected schedule and Radio button selections
        """
        name = self.comboBoxSched.itemText(index)
        try:
            self.scheduleNameLabel.setText(self._s.getSchedName(name, self._db))
            self.statusbar.showMessage('')
        except KeyError:
            self.statusbar.showMessage('Schedule ' + name + ' does not exist.')
            return
        if self.radioButtonJobs.isChecked(): self.populateJobs(name)
        elif self.radioButtonPrecedes.isChecked(): self.populatePrecScheds(name)
        else: self.populateFollowingScheds(name)

    def populateJobs(self,schedNm):
        """Populate jobs from selected schedule"""
        jobs = self._s.getScheduleJobs(schedNm, self._db)
        jobDetails = [(j,self._s.getJobName(j, self._db),self._s.getJobScript(j, self._db)) for j in jobs]
        tModel = JobTableModel(jobDetails,self) #Instantiate this project's table model class with data
        self.tableView.setModel(tModel) # Set the table model of the table view Component on the main Ui
        self.tableView.resizeColumnsToContents()

    def populatePrecScheds(self,schedNm):
        """Populate future schedules from selected schedule"""
        prec = self._s.getFollowingSchedules(schedNm, self._db)
        preceding = [(sch,self._s.getSchedName(sch, self._db)) for sch in prec ]
        tModel = ScheduleTableModel(preceding,self) #Instantiate this project's table model class with data
        self.tableView.setModel(tModel) # Set the table model of the table view Component on the main Ui
        self.tableView.resizeColumnsToContents()

    def populateFollowingScheds(self, schedNm):
        """Populate previous schedules from selected schedule"""
        prev = self._s.getPreviousSchedules(schedNm, self._db)
        preceding = [(sch,self._s.getSchedName(sch, self._db)) for sch in prev ]
        tModel = ScheduleTableModel(preceding,self) #Instantiate this project's table model class with data
        self.tableView.setModel(tModel) # Set the table model of the table view Component on the main Ui
        self.tableView.resizeColumnsToContents()

    def showFullSchedule(self,qComboBox):
        """
        Method to pop up a dialog and display a list of full text of schedule
        """
        text = self._s.getFullSchedule(self.comboBoxSched.currentText(), self._db)
        tDisplay = TextDisplay(self,text)

    def showFullCalendar(self):
        """
        Method to pop up a dialog and display a list of all calendars
        """
        text = self._s.get_calendars(self._db)
        cDisplay = TextDisplay(self,text)

    def show_ctrl_file_deps(self):
        """
        Method to display a picture of all schedules depending on a control file.
        """
        ctl_file_list = self._s.getControlFiles(self._db)
        msg = QInputDialog()
        msg.setWindowIcon(QIcon('Monitor_Screen_32xSM.png'))
        msg.setWindowTitle('Chooser')
        msg.setLabelText('Choose a control file')
        msg.setComboBoxItems(ctl_file_list)
        ok = msg.exec()
        if ok == 0: return # Cancel pressed
        ctl_file = msg.textValue()
        out_list = self._s.getControlFileDependentScheds(self._db, ctl_file)
        self.draw(out_list)
        return

    def show_resource_deps(self):
        """
        Method to display a picture of all schedules depending on a resource.
        """
        resource_list = self._s.get_resources(self._db)
        msg = QInputDialog()
        msg.setWindowIcon(QIcon('Monitor_Screen_32xSM.png'))
        msg.setWindowTitle('Chooser')
        msg.setLabelText('Choose a resource file')
        msg.setComboBoxItems(resource_list)
        ok = msg.exec()
        if ok == 0: return  # Cancel pressed
        needs = msg.textValue()
        out_list = self._s.get_resource_dependent_scheds(self._db, needs)
        self.draw(out_list)
        return

    def tableClicked(self, tView):
        """
        If column 0 of table is clicked take the job or schedule identifier and do something useful with it
        """
        modelIndex = tView.selectionModel().selectedIndexes()
        for index in modelIndex:
            if index.column() == 0: # We selected the first column which contains identifiers
                selection = index.data()
                if self.radioButtonJobs.isChecked():
                    text = self._s.getFullJob(selection, self._db)
                    tDisplay = TextDisplay(self,text) # Pop up dialog with full job
                else:  # Change selected schedule to the one clicked
                    self.comboBoxSched.setCurrentText(selection)

    def exportDirectConnections(self):
        msg = QMessageBox()
        msg.setWindowIcon(QIcon(self._icon))
        msg.setWindowTitle('Maestro')
        msg.setText("Show control files and resources needed?")
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        rc = msg.exec()
        if rc == QMessageBox.Yes: showFileDeps = True
        else : showFileDeps = False

        self.draw(self._s.getGraphvizPart(self.comboBoxSched.currentText(), showFileDeps, self._db))

    def exportFullConnections(self):
        msg = QMessageBox()
        msg.setWindowIcon(QIcon(self._icon))
        msg.setWindowTitle('Maestro')
        msg.setText("Show control files  and resources needed?")
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        rc = msg.exec()
        if rc == QMessageBox.Yes: showFileDeps = True
        else : showFileDeps = False

        self.draw(self._s.getAllConnected(self.comboBoxSched.currentText(), showFileDeps, self._db))

    def draw(self, dependencies):
        """
        Starting from current schedule output all succeeding and preceeding schedules
        recursively in Graphviz format. Run Graphviz to create an svg file picture
        """
        f = open(self._graphvizTxtFile, 'w')
        data = []
        for line in dependencies:
            f.write(line+'\n')
            data.append(line+'\n')
        f.close()
        conn = sqlite3.connect(self._sqlite_ini_name)
        c = conn.cursor()
        # Settings database
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='DOT'")
        returnObject = c.fetchone()
        #Handle invalid values by asking user to choos correct location
        if returnObject: #i.e. we got something back
            dotLoc = returnObject[0]
        else : dotLoc = self.setDotLoc()
        if dotLoc == '': dotLoc = self.setDotLoc()
        #Invoke dot.exe
        try:
            subprocess.call([dotLoc,'-Tsvg', self._graphvizTxtFile, '-o',
                         self._graphvizSvgFile], stderr = None, shell=False)
            subprocess.check_call([dotLoc,'-Tsvg', self._graphvizTxtFile, '-o',
                         self._graphvizSvgFile],stderr = None, shell=False)
            #TODO Proper user friendly error handling DELETE
        except (subprocess.CalledProcessError) as e:
            print ("CalledProcessError error Handling.......")
            print("Returncode {0} command {1} output {2}".format(e.returncode, e.cmd, e.output))
        except OSError as e:
            print ("OSError error Handling.......")
            print("Returncode = {0} meaning '{1}' file = {2}".format(e.errno, e.strerror, e.filename))
            msg = QMessageBox()
            msg.setWindowIcon(QIcon(self._icon))
            msg.setWindowTitle('Maestro')
            msg.setText("Error")
            msg.setIcon(QMessageBox.Critical)
            msg.setInformativeText("Please check dot file location is correctly specified. New map cannot be drawn.")
            msg.exec()
        except ValueError as e:
            print ("ValueError error Handling.......")
        #File to be read for display has been placed above in current working directory
        #Must pass fully qualified filename of graphviz svg file
        SVGDisplay(self,self._graphvizSvgFile, self._s, self._db)

    def findText(self):
        """
        Retrieve text entered from search text bar on screen and look for it
        across jobs and schedules. Output results to a popup window.
        """
        results = self._s.findtext(self.lineEditFind.text(), self._db)
        tDisplay = TextDisplay(self,results)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = MaestroUi(MainWindow)
    # Set up CTRL-C Capture on table view
    kpe = KeyPressEater() #TODO Understand why this code needs to be outside of the main class
    ui.tableView.installEventFilter(kpe) #TODO Understand why this code needs to be outside of the main class
    MainWindow.show()
    sys.exit(app.exec_())

