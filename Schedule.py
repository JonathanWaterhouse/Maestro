from collections import OrderedDict
import os
import sqlite3

from PyQt5.QtGui import QIcon
from typing import List, Set

from PyQt5.QtWidgets import QMessageBox

__author__ = 'Jonathan Waterhouse'
import re
class Schedule():
    """
    Read and store the schedule and jobs from external text files provided from runbook
    Internal storage format:
    {schedId:{'NAME':string, 'NUMBER' = int, 'FOLLOWS':[String], 'NEEDS':[String],
         'CONTAINS':[String], 'COMMENTS':[String], 'ALL':[String], OPENS:[String]}}
         'CONTAINS' list has the jobs in the schedule
         'ALL' list is a list of all the schedule lines
    {JobId:{"DESCRIPTION":String, "SCRIPT":String, "CONTROL-FILE":String, "ALL":[]}}
        "CONTROL-FILE" is an attempt to getthe control file the job depends on
        "ALL is a list of the complete job
    """
    def __init__(self,sourceFiles, maestro_db, window_icon):
        """
        This code embodies the rules required to parse the schedule and job files and store as an internal object
        """
        # initialisations required for schedule file processing
        self._icon = window_icon
        msg = QMessageBox()
        msg.setWindowIcon(QIcon(self._icon))
        msg.setWindowTitle('Maestro')
        msg.setText("Refresh SQLite maestro database?\nHint: You only need to do it if you selected new Maestro files.")
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        rc = msg.exec()
        #We don't want to refresh any data in internal database (presumably maestro schedule files did not change)
        if rc == QMessageBox.No: return

        all, follows,needs,opens,comments,jobs = [],[],[],[],[],[]
        schedNum = 0
        thisSched, thisName = '',''
        self._sched ,jobSchedule = {},{}
        weAreAtJobs = False
        ### ------->  process schedule file
        schedFile = open(sourceFiles['SCHEDULE'],'r')
        for line in schedFile:
            all.append(line)
            if line.startswith("#*T*") or line.startswith("#**T*") or line.startswith("#T*")or \
                    line.startswith("**T*") or line.startswith("***T*"):
                thisName = line[line.find("T*"):len(line)].strip()
            if line.startswith("SCHEDULE"):
                schedNum += 1
                thisSched = line[line.find("#")+1:len(line)-1].strip()
            if line.startswith("FOLLOWS"):
                l = line[line.find("#")+1:len(line)-1].replace("\n","") # Bit following # which delimits Machine
                #Some follows schedules have .@ at end (meaning after all jobs in schedule?)
                if l.find('.@') != -1:
                    fTemp = l[0:l.find('.@')]
                else: fTemp = l
                #In some case dependency is on a specific job in the schedule specified schedule.job we just want the schedule
                if fTemp.find(".") != -1: f = fTemp.split(".")[0]
                else: f = fTemp
                follows.append(f)
                #Update schedule that this schedule precedes
                prec = []
                t = {}
                if f not in self._sched: #No mention of preceding schedule yet
                    prec.append(thisSched)
                    # Need to add in proper initialisation of sched[f]
                    t["NAME"],t["NUMBER"],t["FOLLOWS"],t["NEEDS"],t["CONTAINS"],t["COMMENTS"],t["ALL"],t["OPENS"] = [],[],[],[],[],[],[],[]
                elif "PRECEDES" not in self._sched[f]:
                    #Assumes in a previous pass that this sched[f] was properly initialised
                    prec.append(thisSched)
                    t = self._sched[f]
                else:
                    #Assumes in a previous pass that this sched[f] was properly initialised
                    prec = self._sched[f]["PRECEDES"]
                    prec.append(thisSched)
                    t = self._sched[f]
                t["PRECEDES"] = prec
                self._sched[f] = t
            if line.startswith("NEEDS"):
                f = line[line.find("#")+1:len(line)-1].replace("\n","")
                needs.append(f)
            if line.startswith("OPENS"):
                #f = line[line.find(" ")+1:line.find("\"",line.find("\"")+1)+1].replace("\n","")
                f = line[line.find(" ")+1:len(line)].replace("\n","")
                opens.append(f)
            if line.startswith("**"):
                if line[0: 2] == "**": comments.append(line)
            if line.startswith("#"):
                if line[0: 1] == "#": comments.append(line)
            #
            #Processing of jobs information
            #
            if line.startswith(":"): weAreAtJobs = True
            if weAreAtJobs and thisName == '':
                try: thisName = comments[0] # Assign something to name if we got nothing so far
                except (IndexError): pass
            if weAreAtJobs and (line!= "" and not line.startswith(" ") and
                    line.find("NEEDS") == -1 and line.find("OPENS") == -1 and
                    line.find("FOLLOWS") == -1 and
                    not line.startswith("#") and line.find("END") == -1 and
                    not line.startswith(":") and not line.startswith("*")):
                if line.strip() !="":
                    jobs.append(line.strip())
                    #Update the jobSchedule link data
                    s = []
                    if line.strip() not in jobSchedule: s = []
                    else: s = jobSchedule[line.strip()]
                    s.append(thisSched)
                    jobSchedule[line.strip()] = s
            #End of schedule processing
            if line.startswith("END"):
                col = {}
                col["NAME"] = thisName
                col["NUMBER"] = schedNum
                col["FOLLOWS"] = follows
                col["NEEDS"] = needs
                col["CONTAINS"] = jobs
                col["COMMENTS"] = comments
                col["ALL"] = all
                col["OPENS"] = opens
                weAreAtJobs = False
                tmp = []
                if thisSched in self._sched:
                    #The process above which derives "PRECEDES" already created
                    #an entry for this schedule which we need to replace without change.
                    #Otherwise we need to create a blank entry.
                    tmp = []
                    if "PRECEDES" in self._sched[thisSched]:
                        tmp = self._sched[thisSched]["PRECEDES"]
                else: tmp = []
                col["PRECEDES"] = tmp
                self._sched[thisSched] = col
                thisName = ""; thisSched = ""
                all, follows,needs,opens,comments,jobs = [],[],[],[],[],[]
        schedFile.close()

        ###-----> schedule file processing completed process Job file

        jobFile = open(sourceFiles['JOBS'],'r')
        jobs = {}
        line, prevJob, thisJob, thisDesc, thisScript, thisCtl = "","","","","",""
        for line in jobFile:
            if line == "": continue #Do Nothing, read next line
            if not line.startswith(" ")and not line.startswith("$"): # New Job
                thisJob = line.strip()
                if thisJob != prevJob:
                    cols = {}
                    cols["DESCRIPTION"] = thisDesc
                    cols["SCRIPT"] = thisScript
                    cols["CONTROL-FILE"] = thisCtl
                    cols["ALL"] = all
                    jobs[prevJob] = cols
                    all = []
                    thisDesc ,thisScript, thisCtl = "","",""
                    prevJob = thisJob;
            all.append(line);
            if line.find("DESCRIPTION") == 1: thisDesc = line[line.find("DESCRIPTION")+11:len(line)-1]
            if line.find("SCRIPTNAME") == 1: thisScript = line[line.find("SCRIPTNAME")+10:len(line)-1]
        jobFile.close()
        self._jobs = jobs

        ###-----> job file processing completed process Calendar file
        cal_file = open(sourceFiles['CALENDARS'],'r')
        calendar = {}
        self._calendar_text = {}
        cal_dates = []
        for line in cal_file:
            if line.startswith('$CALENDAR'): continue
            if line.startswith('  "'):
                self._calendar_text[calendar_name] = line[line.find('"')+ 1 : line.rfind('"')].replace('\\"','',-1).strip()
                continue
            if not line.startswith(' ') and not line.startswith('\n'):
                calendar_name = line[0:line.find(' ')]
                cal_dates = []
            if line.startswith(' ') and line != '':
                cal_dates.append(line.rstrip('\n').strip())
            if line == '\n': # End calendar
                calendar[calendar_name] = cal_dates


        cal_file.close()
        #calendar[k] is a list l=each element contains 'mm/dd/yy mm/dd/yy ...'
        self._cal = {}
        for k in calendar.keys():
            #calendar[k] is a list l=each elemsnt contains 'mm/dd/yy mm/dd/yy ...'
            self._cal[k] = ' '.join(calendar[k]).split(' ')

        #Do SQLite setup to represent the schedule
        self.setup_db(maestro_db)

    def getAllSchedIds(self, maestro_db : str) -> list:
        """
        Return a view of all schedule ids contained in full schedule
        """
        l = []
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        for row in c.execute("SELECT DISTINCT SCHEDULE FROM SCHEDULE ORDER BY SCHEDULE ASC"):
            l.append(row[0])
        conn.close()
        return l

    def getSchedName(self,schedNumber: str, maestro_db: str) -> str:
        """
        Given input of String schedNumber, output string the schedule name
        """
        if schedNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            c.execute("SELECT DISTINCT NAME FROM SCHEDULE WHERE SCHEDULE=?",(schedNumber,))
            name =  c.fetchone()
            conn.close()
            return name[0]
        else: return ''

    def getScheduleJobs(self, schedNumber: str, maestro_db: str) -> List:
        """
        Find schedule jobs for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of schedule jobs
        """
        l = []
        if schedNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            for row in c.execute("SELECT JOB FROM SCH_LINES WHERE SCHEDULE=?", (schedNumber,)):
                l.append(row[0])
            conn.close()
            return l
        else:
            return ''

    def getPreviousSchedules(self, schedNumber: str, maestro_db: str) -> List:
        """
        Find previous schedules for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of immediately previous schedules
        """
        l = []
        if schedNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            for row in c.execute("SELECT SCHEDULE FROM SCH_LINKS WHERE PRECEDES=? ORDER BY SCHEDULE ASC", (schedNumber,)):
                l.append(row[0])
            conn.close()
            return l
        else:
            return ''

    def getFollowingSchedules(self, schedNumber: str, maestro_db: str) -> List:
        """
        Find following schedules for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of immediately following schedules
        """
        l = []
        if schedNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            for row in c.execute("SELECT PRECEDES FROM SCH_LINKS WHERE SCHEDULE=? ORDER BY PRECEDES ASC", (schedNumber,)):
                l.append(row[0])
            conn.close()
            return l
        else:
            return ''

    def getFullSchedule(self, schedNumber: str, maestro_db: str) -> List:
        """
        Find full schedule for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of all schedule lines
        """
        l = []
        if schedNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            for row in c.execute("SELECT LINE FROM SCH_ALL WHERE SCHEDULE=?", (schedNumber,)):
                l.append(row[0])
            conn.close()
            return l
        else:
            return ''

    def getFullJob(self, jobNumber: str, maestro_db: str) -> List:
        """
        Find full job for a given input job number. Return a list.
        @param schedNumber: input schedule number
        @return: List of all job lines
        """
        l = []
        if jobNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            for row in c.execute("SELECT LINE FROM JOBS_ALL WHERE JOB=?", (jobNumber,)):
                l.append(row[0])
            conn.close()
            return l
        else:
            return ''

    def getJobName(self,jobNumber: str, maestro_db: str) -> str:
        """
        Given input of String jobNumber, output string the job name
        """
        if jobNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            c.execute("SELECT DISTINCT DESCRIPTION FROM JOBS WHERE JOB=?", (jobNumber,))
            name = c.fetchone()
            conn.close()
            return name[0]
        else:
            return ''

    def getJobScript(self,jobNumber: str, maestro_db: str) -> str:
        """
        Given input of String jobNumber, output string the job script
        """
        if jobNumber != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            c.execute("SELECT DISTINCT SCRIPT FROM JOBS WHERE JOB=?", (jobNumber,))
            name = c.fetchone()
            conn.close()
            return name[0]
        else:
            return ''

    def getGraphvizPart(self, start_key: str, showFileDeps: bool, maestro_db: str) -> List:
        """
        Return List of all schedules preceding or following a given input schedule "startKey"
        in a format processsable by Graphviz dot program.
        cf http://www.graphviz.org/
        """
        nodes_f, completed, nodes  = set(), set(), set()
        out_set = set() #Ensure any duplicates are omitted from output
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        #Going forward
        nodes_f.add(start_key)
        nodes.add(start_key) #This is for a permanent record of all nodes in map for later
        while (len(nodes_f) != 0):
            curr_node = nodes_f.pop()
            if curr_node not in completed:
                c.execute("SELECT PRECEDES FROM SCH_LINKS WHERE SCHEDULE=?", (curr_node,))
                rows = c.fetchall()
                for row in rows:
                    nodes_f.add(row[0])
                    nodes.add(row[0])
                    out_set.add("\""+ curr_node +"\"" + " -> " + "\""+ row[0] + "\"")
                if len(rows) == 0: out_set.add("\""+ curr_node +"\" "+"[shape=diamond, color=blue]")
                completed.add(curr_node)
        #Going backward
        nodes_b, completed = set(), set() #Initialise them
        nodes_b.add(start_key)
        while (len(nodes_b) != 0):
            curr_node = nodes_b.pop()
            if curr_node not in completed:
                for row in c.execute("SELECT SCHEDULE FROM SCH_LINKS WHERE PRECEDES=?", (curr_node,)):
                    nodes_b.add(row[0])
                    nodes.add(row[0])
                    out_set.add("\"" + row[0] + "\"" + " -> " + "\"" + curr_node + "\"")
                completed.add(curr_node)
        #Derive NEEDS and OPENS dependencies if user requested that
        if showFileDeps: out_set = out_set.union(self._get_ctrl_file_and_rsrce_deps(nodes, maestro_db))

        out_list = list(out_set)
        #Highlight start node and add graph start and end signature
        out_list.append("\"" + start_key + "\" " + "[fillcolor=yellow, style=\"rounded,filled\", shape=box, fontsize=22]")
        out_list.insert(0, "digraph G {")
        out_list.append("}")
        conn.close()

        return out_list

    def getAllConnected(self, start_key: str, showFileDeps: bool, maestro_db: str) -> List:
        """
        Find all nodes connected to the starting node
        @param start: initial schedule node
        @param showFileDeps Boolean true if we want to show control files etc.
        @return List object of lines for Graphviz dot program:
        """
        completed, nodes = set(), set()
        out_set = set()  # Ensure any duplicates are omitted from output
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        nodes.add(start_key)
        while (len(nodes) != 0):
            curr_node = nodes.pop()
            if curr_node not in completed:
                c.execute("SELECT PRECEDES FROM SCH_LINKS WHERE SCHEDULE=?", (curr_node,))
                rows = c.fetchall()
                for row in rows:
                    nodes.add(row[0])
                    out_set.add("\"" + curr_node + "\"" + " -> " + "\"" + row[0] + "\"")
                if len(rows) == 0: out_set.add("\"" + curr_node + "\" " + "[shape=diamond, color=blue]")
                for row in c.execute("SELECT SCHEDULE FROM SCH_LINKS WHERE PRECEDES=?", (curr_node,)):
                    nodes.add(row[0])
                    out_set.add("\"" + row[0] + "\"" + " -> " + "\"" + curr_node + "\"")
                if len(rows) == 0: out_set.add("\"" + curr_node + "\" " + "[shape=diamond, color=blue]")
                completed.add(curr_node) #We now finished with this node

        conn.close()
        # Derive NEEDS and OPENS dependencies if user requested that
        if showFileDeps: out_set = out_set.union(self._get_ctrl_file_and_rsrce_deps(completed, maestro_db))

        out_list = list(out_set)
        #Highlight start node and add graph start and end signature
        out_list.append("\"" + start_key + "\" " + "[fillcolor=yellow, style=\"rounded,filled\", shape=box, fontsize=22]")
        out_list.insert(0, "digraph G {")
        out_list.append("}")
        return out_list

    def _get_ctrl_file_and_rsrce_deps(self, nodes: Set, maestro_db: str) -> Set:
        """ Internal routine to find resource  and control dependencies of a set of nodes.
        @param: nodes: Set of nodes to find dependencies of
        @return: Set of lines in graphviz format showing dependencies
        """
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        out_set = set()
        for s in nodes:
            c.execute("SELECT OPENS FROM SCH_OPENS WHERE SCHEDULE=?", (s,))
            rows = c.fetchall()
            for opns in rows:
                opnsNode = opns[0].replace('"', '').split('/')[-1]
                if opnsNode[-3:].lower() == "ctl":  # Just control files
                    out_set.add("\"" + opnsNode + "\"" + " -> " + "\"" + s + "\"" + '[color=violet]')
                    out_set.add(
                        '"' + opnsNode + '"' + ' [color=white, fillcolor=violet, style="rounded,filled", shape=box]')
            c.execute("SELECT NEEDS FROM SCH_NEEDS WHERE SCHEDULE=?", (s,))
            rows = c.fetchall()
            for needs in rows:
                out_set.add("\"" + needs[0] + "\"" + " -> " + "\"" + s + "\"" + '[color=limegreen]')
                out_set.add(
                    '"' + needs[0] + '"' + ' [color=white, fillcolor=limegreen, style="rounded,filled", shape=box]')
        conn.close()
        return out_set

    def get_calendars(self, maestro_db):
        """
        Load calendars for display. Incoming data is a sequence of records from sqlite (Calendar, date) with
        one record per date in the calendar. The returned values is a list of lines that can be displayed in a
        text popup. Each line needs to have new line character at end so text box works properly.
        It has records like:
            Calendar Name
            Calendar Text
               Line of (dates_per_line) number of dates in the calendar
               Next line of (dates_per_line) number of dates in the calendar
               etc.

        @param maestro_db: Database containing schedule details
        @return: lis of calendars and their dates split into groups of dates_per_line
        """
        dates_per_line = 8 # How many date entries we want in an output line
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        cals, cal_names = OrderedDict(), {}
        #Get calendar data from sqlite database
        for row in c.execute("""SELECT A.CALENDAR, A.DATE, B.NAME
            FROM CALENDARS AS A INNER JOIN CALENDAR_NAMES AS B ON A.CALENDAR = B.CALENDAR
            ORDER BY A.CALENDAR"""):
            try: # row is a tuple (calendar, date)
                days_list = cals[row[0]]
                days_list.append(row[1])
                cals[row[0]] = days_list
            except (KeyError):
                cals[row[0]] = [row[1]]
                cal_names[row[0]] = row[2]
        c.close()
        cal_lines = []
        # Format the calendar data into output lines
        for k in cals.keys(): # k contains the calendar name in input sequence since cals is an OrderedDict
            cal_lines.append(k + '\n') #First section line - the calendar id
            try: cal_lines.append('    ' + cal_names[k] + '\n') #Second section line - the calendar name, if found
            except (KeyError): pass
            i = 0
            cal_split_line = []
            for v in cals[k]:
                if i < dates_per_line: #Build up a line of dates for the calendar
                    cal_split_line.append(v)
                    i += 1
                else:
                    # We are beyond agreed length of line so format it for output and add to output records
                    cal_lines.append('    ' + '   '.join(cal_split_line) + '\n')
                    cal_split_line = []
                    # Don't lose the current date which will be the first entry on the next line
                    cal_split_line.append(v)
                    i = 1
            #Make sure we output the last line of the current calendar before moving to next calendar
            if cal_split_line is not []: cal_lines.append('    ' + '   '.join(cal_split_line) + '\n')
            cal_lines.append('\n')

        return cal_lines

    def getControlFiles(self,maestro_db):
        """
        Search schedules database and return a list of control files
        @param: maestro_db: The location of the schedule database
        @return: List of control files
        """
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        cFiles = []
        for row in c.execute("SELECT DISTINCT SUBSTR(OPENS,INSTR(OPENS,'\"')+1,INSTR(OPENS,'.CTL')-INSTR(OPENS,'\"')+3) AS File "
                             "FROM SCH_OPENS where opens glob ('*.CTL*') ORDER BY File"):

            cFiles.append(row[0])
        return cFiles

    def get_resources(self, maestro_db):
        """
        Search schedules database and return a list of control files
        @param: maestro_db: The location of the schedule database
        @return: List of control files
        """
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        needs = []
        for row in c.execute(
                "SELECT DISTINCT NEEDS FROM SCH_NEEDS ORDER BY NEEDS"):
            needs.append(row[0])
        return needs

    def getControlFileDependentScheds(self,maestro_db, ctl_file):
        """
        Find all nodes dependent on control file to the starting node
        @param: maestro_db: The location of the schedule database
        @param: ctl_file: the control file we are to work with
        @return: List of dependent schedules in Graphviz format
        """
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        sql = []
        sql.append("WITH RECURSIVE ")
        sql.append("ctrl_file_deps (deps) AS ( ")
        sql.append("SELECT SCHEDULE FROM SCH_OPENS where opens glob ('*" + ctl_file+ "*')), ")
        sql.append("sched_fwd (n) AS (")
        sql.append("SELECT deps from ctrl_file_deps ")
        sql.append("UNION ")
        sql.append("SELECT precedes from sch_links inner join sched_fwd ")
        sql.append("WHERE sch_links.schedule = sched_fwd.n) ")
        sql.append("Select distinct f.n, a.precedes ")
        sql.append("from sched_fwd As f left outer join sch_links As a on f.n = a.schedule ")
        sql.append("ORDER BY f.n, a.precedes ")
        out = set()
        for row in c.execute(''.join(sql)):
            if repr(row[1]) == 'None' : target = 'END'
            else: target = repr(row[1]).strip("'")
            out.add('"' + repr(row[0]).strip("'") + '" -> "' + target + '"' )
        #This next read is to find the link between the control file and the highest level schedules
        sql = []
        sql.append ("SELECT SCHEDULE FROM SCH_OPENS where opens glob ('*" + ctl_file+ "*')")
        for row in c.execute(''.join(sql)): out.add('"' + ctl_file + '" -> "' + repr(row[0]).strip("'") + '"' )

        out.add('"' + ctl_file + '"' + ' [color=white, fillcolor=violet, style="rounded,filled", shape=box]')
        out.add('"' + 'END' + '"' + ' [color=white, fillcolor=pink, style="rounded,filled", shape=circle]')
        out_list = [el for el in out]
        out_list.sort()
        out_list.insert(0,"ranksep=0.75")
        out_list.insert(0,"digraph G {")
        out_list.append('}')

        conn.close()
        return out_list

    def get_resource_dependent_scheds(self, maestro_db, resource):
        """
        Find all nodes dependent on control file to the starting node
        @param: maestro_db: The location of the schedule database
        @param: ctl_file: the control file we are to work with
        @return: List of dependent schedules in Graphviz format
        """
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        sql = []
        sql.append("WITH RECURSIVE ")
        sql.append("ctrl_file_deps (deps) AS ( ")
        sql.append("SELECT SCHEDULE FROM SCH_NEEDS where NEEDS glob ('*" + resource + "*')), ")
        sql.append("sched_fwd (n) AS (")
        sql.append("SELECT deps from ctrl_file_deps ")
        sql.append("UNION ")
        sql.append("SELECT precedes from sch_links inner join sched_fwd ")
        sql.append("WHERE sch_links.schedule = sched_fwd.n) ")
        sql.append("Select distinct f.n, a.precedes ")
        sql.append("from sched_fwd As f left outer join sch_links As a on f.n = a.schedule ")
        sql.append("ORDER BY f.n, a.precedes ")
        out = set()
        for row in c.execute(''.join(sql)):
            if repr(row[1]) == 'None':
                target = 'END'
            else:
                target = repr(row[1]).strip("'")
            out.add('"' + repr(row[0]).strip("'") + '" -> "' + target + '"')
        # This next read is to find the link between the resource and the highest level schedules
        sql = []
        sql.append("SELECT SCHEDULE FROM SCH_NEEDS where NEEDS glob ('*" + resource + "*')")
        for row in c.execute(''.join(sql)): out.add('"' + resource + '" -> "' + repr(row[0]).strip("'") + '"')

        out.add('"' + resource + '"' + ' [color=white, fillcolor=limegreen, style="rounded,filled", shape=box]')
        out.add('"' + 'END' + '"' + ' [color=white, fillcolor=limegreen, style="rounded,filled", shape=circle]')
        out_list = [el for el in out]
        out_list.sort()
        out_list.insert(0, "ranksep=0.75")
        out_list.insert(0, "digraph G {")
        out_list.append('}')

        conn.close()
        return out_list

    def findtext(self,searchText: str, maestro_db: str) -> List:
        """
        @param searchText: input text to search
        @return: List of results lines from schedule and jobs
        """
        result = []
        if searchText != '':
            conn = sqlite3.connect(maestro_db)
            c = conn.cursor()
            for row in c.execute("SELECT SCHEDULE, LINE FROM SCH_ALL WHERE LINE LIKE ?", ('%' + searchText + '%',)):
                result.append(row[0] + " -> " + row[1])

            sql = 'SELECT SL.SCHEDULE, SL.JOB, J.LINE from SCH_LINES AS SL INNER JOIN JOBS_ALL AS J ON J.JOB = SL.JOB WHERE LINE LIKE ?'
            for row in c.execute(sql, ('%' + searchText + '%',)):
                result.append(row[0] + " : " + row[1] + " -> " + row[2])
            conn.close()
            result.sort()
        else:
            return []

        return result

    def setup_db(self,maestro_db: str):
        """
        Create a representation in sqlite database of the schedule store in internal storage.
        This is primarily for offline analysis:
        {schedId:{'NAME':string, 'NUMBER' = int, 'FOLLOWS':[String], 'NEEDS':[String],
             'CONTAINS':[String], 'COMMENTS':[String], 'ALL':[String], OPENS:[String]}}
             'CONTAINS' list has the jobs in the schedule
             'ALL' list is a list of all the schedule lines
        {JobId:{"DESCRIPTION":String, "SCRIPT":String, "CONTROL-FILE":String, "ALL":[]}}
            "CONTROL-FILE" is an attempt to getthe control file the job depends on
            "ALL is a list of the complete job
        """
        conn = sqlite3.connect(maestro_db)
        c = conn.cursor()
        #Delete tables if already exist and recreate
        c.execute('DROP TABLE IF EXISTS SCHEDULE')
        c.execute("""CREATE TABLE SCHEDULE(SCHEDULE TEXT, NAME TEXT, PLATFORM TEXT, ACTION TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_FREQ')
        c.execute("""CREATE TABLE SCH_FREQ (SCHEDULE TEXT, FREQ TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_LINES')
        c.execute("""CREATE TABLE SCH_LINES (SCHEDULE TEXT, JOB TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_LINKS')
        c.execute("""CREATE TABLE SCH_LINKS (SCHEDULE TEXT, PRECEDES TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_NEEDS')
        c.execute("""CREATE TABLE SCH_NEEDS (SCHEDULE TEXT, NEEDS TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_COMMENTS')
        c.execute("""CREATE TABLE SCH_COMMENTS (SCHEDULE TEXT, COMMENT TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_OPENS')
        c.execute("""CREATE TABLE SCH_OPENS (SCHEDULE TEXT, OPENS TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_ALL')
        c.execute("""CREATE TABLE SCH_ALL (SCHEDULE TEXT, LINE TEXT)""")
        c.execute ('DROP TABLE IF EXISTS JOBS')
        c.execute("""CREATE TABLE JOBS (JOB TEXT, PLATFORM TEXT, DESCRIPTION TEXT, SCRIPT TEXT, CTRL_FILE TEXT)""")
        c.execute ('DROP TABLE IF EXISTS JOBS_ALL')
        c.execute("""CREATE TABLE JOBS_ALL (JOB TEXT, LINE TEXT)""")
        c.execute('DROP TABLE IF EXISTS CALENDAR_NAMES')
        c.execute("""CREATE TABLE CALENDAR_NAMES (CALENDAR TEXT, NAME TEXT)""")
        c.execute('DROP TABLE IF EXISTS CALENDARS')
        c.execute("""CREATE TABLE CALENDARS (CALENDAR TEXT, DATE TEXT)""")

        #Populate Tables by looping through previously stored schedules
        sched_names, sched_jobs, sched_needs, sched_comments, \
        sched_opens, sched_all, sched_freq = [], [], [], [], [], [], []
        sched_links = set() # use set to remove duplicate links
        for sched in self._sched.keys():
            platform,  action = '', ''
            freq = []
            for line in self._sched[sched]['ALL']:
                sched_all.append((sched,line))
                if line.startswith('SCHEDULE'): platform = line[line.find(' ')+1:line.find('#')]
                if line.startswith('ON'): freq.append(line[3:len(line)])
                if line.startswith('CARRYFORWARD'): action = 'CARRYFORWARD'
            sched_names.append((sched,self._sched[sched]['NAME'], platform, action))
            for fr in freq: sched_freq.append((sched,fr))
            for job in self._sched[sched]['CONTAINS']: sched_jobs.append((sched,job))
            for link in self._sched[sched]['PRECEDES']: sched_links.add((sched,link))
            for link in self._sched[sched]['FOLLOWS']: sched_links.add((link,sched))
            for needs in self._sched[sched]['NEEDS']: sched_needs.append((sched,needs))
            for comments in self._sched[sched]['COMMENTS']: sched_comments.append((sched,comments))
            for opens in self._sched[sched]['OPENS']: sched_opens.append((sched,opens))
        #Add to sql tables
        c.executemany('INSERT INTO SCHEDULE (SCHEDULE, NAME, PLATFORM, ACTION) VALUES (?,?,?,?)', sched_names)
        c.executemany('INSERT INTO SCH_FREQ (SCHEDULE, FREQ) VALUES (?,?)', sched_freq)
        c.executemany('INSERT INTO SCH_LINES (SCHEDULE, JOB) VALUES (?,?)', sched_jobs)
        c.executemany('INSERT INTO SCH_LINKS (SCHEDULE, PRECEDES) VALUES (?,?)', sched_links)
        c.executemany('INSERT INTO SCH_NEEDS (SCHEDULE, NEEDS) VALUES (?,?)', sched_needs)
        c.executemany('INSERT INTO SCH_COMMENTS (SCHEDULE, COMMENT) VALUES (?,?)', sched_comments)
        c.executemany('INSERT INTO SCH_OPENS (SCHEDULE, OPENS) VALUES (?,?)', sched_opens)
        c.executemany('INSERT INTO SCH_ALL (SCHEDULE, LINE) VALUES (?,?)', sched_all)

        #Populate Tables by looping through previously stored jobs
        jobs, job_lines = [],[]
        for job in self._jobs.keys():
            platform = job[0:job.find('#')]
            jobs.append((job, platform, self._jobs[job]['DESCRIPTION'], self._jobs[job]['SCRIPT'],
                         self._jobs[job]['CONTROL-FILE']))
            for job_line in self._jobs[job]['ALL']:
                job_lines.append((job, job_line))
        c.executemany('INSERT INTO JOBS (JOB, PLATFORM, DESCRIPTION, SCRIPT, CTRL_FILE) VALUES (?, ?, ?, ?, ?)', jobs)
        c.executemany('INSERT INTO JOBS_ALL (JOB, LINE) VALUES (?, ?)', job_lines)

        #Populate Tables by looping through previously stored calendars
        cal_entries = []
        for k in self._cal.keys():
            for v in self._cal[k]: cal_entries.append((k,v))
        c.executemany('INSERT INTO CALENDARS (CALENDAR, DATE) VALUES (?, ?)', cal_entries)
        cal_names = []
        for k in self._calendar_text.keys(): cal_names.append((k,self._calendar_text[k]))
        c.executemany('INSERT INTO CALENDAR_NAMES (CALENDAR, NAME) VALUES (?, ?)', cal_names)

        conn.commit()