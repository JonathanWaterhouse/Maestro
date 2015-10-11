import os
import sqlite3

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
    def __init__(self,sourceFiles, sqlite_db):
        """
        This code embodies the rules required to parse the schedule and job files and store as an internal object
        """
        # initialisations required for schedule file processing
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

        self.setup_db(sqlite_db)

    def getAllSchedIds(self):
        """
        Return a view of all schedule ids contained in full schedule
        """
        return self._sched.keys()

    def getSchedName(self,schedNumber):
        """
        Given input of String schedNumber, output string the schedule name
        """
        return self._sched[schedNumber]['NAME']

    def getScheduleJobs(self, schedNumber):
        """
        Find schedule jobs for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of schedule jobs
        """
        return self._sched[schedNumber]['CONTAINS']

    def getPreviousSchedules(self, schedNumber):
        """
        Find previous schedules for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of immediately previous schedules
        """
        return self._sched[schedNumber]['FOLLOWS']

    def getFollowingSchedules(self, schedNumber):
        """
        Find following schedules for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of immediately following schedules
        """
        return self._sched[schedNumber]['PRECEDES']

    def getFullSchedule(self, schedNumber):
        """
        Find full schedule for a given input schedule. Return a list.
        @param schedNumber: input schedule number
        @return: List of all schedule lines
        """
        return self._sched[schedNumber]['ALL']

    def getFullJob(self, schedNumber):
        """
        Find full job for a given input job number. Return a list.
        @param schedNumber: input schedule number
        @return: List of all job lines
        """
        return self._jobs[schedNumber]['ALL']

    def getJobName(self,jobNumber):
        """
        Given input of String jobNumber, output string the job name
        """
        return self._jobs[jobNumber]['DESCRIPTION']

    def getJobScript(self,jobNumber):
        """
        Given input of String jobNumber, output string the job script
        """
        return self._jobs[jobNumber]['SCRIPT']

    def getGraphvizPart(self, startKey, showFileDeps):
        """
        Return List of all schedules preceding or following a given input schedule "startKey"
        in a format processsable by Graphviz dot program.
        cf http://www.graphviz.org/
        """
        out = [];
        schedsIncludedF, schedsIncludedP, schedsIncluded, removeDups = set(), set(), set(), set()
        schedsIncludedP = self.recursive(startKey, "PRECEDES", out)
        schedsIncludedF = self.recursive(startKey, "FOLLOWS", out)
        schedsIncluded = schedsIncludedF.union(schedsIncludedP)
        # Derive the forward and backward dependencies
        for el in out: removeDups.add(el)
        #Derive the dependencies from requirements for input file if user requested that
        if showFileDeps:
            for s in schedsIncluded:
                for opns in self._sched[s]["OPENS"]:
                    opnsNode = opns.replace('"','').split('/')[-1]
                    if opnsNode[-3:].lower() == "ctl": #Just control files
                        removeDups.add("\""+ opnsNode + "\"" + " -> " + "\""+ s +"\"" + '[color=violet]')
                        removeDups.add('"' + opnsNode + '"' + ' [color=white, fillcolor=violet, style="rounded,filled", shape=box]')
        # Final formatting steps
        outList = [s for s in removeDups]
        outList.append("\""+ startKey +"\" "+"[fillcolor=yellow, style=\"rounded,filled\", shape=box, fontsize=22]" )
        outList.insert(0,"digraph G {")
        outList.append("}")
        return outList

    def recursive(self, key, direction, outList):
        """
        Recursively move through all dependent schedules either forwards or backwards
        as defined by input direction
        String key
        String direction (has to correspond to a key in stored self._sched (currently "FOLLOWS", "PRECEDES")
        List outList
        """
        schedsIncluded = set()
        schedsIncluded.add(key)
        precedes = self._sched[key][direction] # retrieve dependent schedules of input schedule (key)
        if len(precedes) !=0:
            for f in precedes:
                schedsIncluded.add(f)
                fStrip = re.split("[^0-9a-zA-Z-]",f)[0]
                if direction == "PRECEDES": outList.append("\""+ key +"\"" + " -> " + "\""+ fStrip + "\"")
                else: outList.append("\""+ fStrip + "\"" + " -> " + "\""+ key +"\"")
                self.recursive(f, direction, outList)
        else:
            if direction == "PRECEDES": outList.append("\""+ key +"\" "+"[shape=diamond, color=blue]" )
        return schedsIncluded

    def findAllConnected(self, start, showFileDeps):
        """
        Find all nodes connected to the starting node
        @param start: initial schedule node
        @param showFileDeps Boolean true if we want to show control files etc.
        @return List object of lines for Graphviz dot program:
        """
        nodes = set()
        nodes.add(start)
        completed = set()
        while (len(nodes) != 0):
            currNode = nodes.pop()
            for nbr in self._sched[currNode]["FOLLOWS"]:
                if nbr not in completed: nodes.add(nbr)
            for nbr in self._sched[currNode]["PRECEDES"]:
                if nbr not in completed: nodes.add(nbr)
            completed.add(currNode)
        out = set()
        for el in completed:
            for fwd in self._sched[el]["PRECEDES"]: out.add("\""+ el +"\"" + " -> " + "\""+ fwd + "\"")
            for bwd in self._sched[el]["FOLLOWS"]: out.add("\""+ bwd + "\"" + " -> " + "\""+ el +"\"")
            if showFileDeps:
                for opns in self._sched[el]["OPENS"]:
                    opnsNode = opns.replace('"','').split('/')[-1]
                    if opnsNode[-3:].lower() == "ctl": #Just control files
                        out.add('"'+ opnsNode + '"' + ' -> ' + '"' + el + '"' +'[color=violet]')
                        out.add('"' + opnsNode + '"' + ' [color=white, fillcolor=violet, style="rounded,filled", shape=box]')
        outList = [el for el in out]
        outList.append("\""+ start +"\" " + '[fillcolor=yellow, style="rounded,filled", shape=box, fontsize=22]' )
        outList.sort()
        outList.insert(0,"ranksep=0.75")
        outList.insert(0,"digraph G {")
        outList.append("}")
        return outList

    def findtext(self,searchText):
        """
        @param searchText: input text to search
        @return: List of results lines from schedule and jobs
        """
        result = []
        for k,v in self._sched.items():
            for line in v["ALL"]:
                if line.lower().find(searchText.lower())!= -1: result.append(k + " -> " + line )
            for job in v["CONTAINS"]:
                try:
                    for line in self._jobs[job]["ALL"]:
                        if line.lower().find(searchText.lower())!= -1: result.append(k + " : " + job + " -> " + line)
                except KeyError: pass
        return result

    def setup_db(self,sqlite_db):
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
        conn = sqlite3.connect(sqlite_db)
        c = conn.cursor()
        #Delete tables if already exist and recreate
        c.execute('DROP TABLE IF EXISTS SCHEDULE')
        c.execute("""CREATE TABLE SCHEDULE(SCHEDULE TEXT, NAME TEXT, PLATFORM TEXT, FREQ TEXT, ACTION TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_LINES')
        c.execute("""CREATE TABLE SCH_LINES (SCHEDULE TEXT, JOB TEXT)""")
        c.execute ('DROP TABLE IF EXISTS SCH_LINKS')
        c.execute("""CREATE TABLE SCH_LINKS (SCHEDULE TEXT, PRECEDES TEXT, FOLLOWS TEXT)""")
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
        #Populate Tables by looping through previously stored schedules
        sched_names, sched_jobs, sched_links, sched_needs, sched_comments, sched_opens, sched_all = [], [], [], [], [], [], []
        for sched in self._sched.keys():
            platform, freq, action = '', '', ''
            for line in self._sched[sched]['ALL']:
                sched_all.append((sched,line))
                if line.startswith('SCHEDULE'): platform = line[line.find(' ')+1:line.find('#')]
                if line.startswith('ON'): freq = line[3:len(line)]
                if line.startswith('CARRYFORWARD'): action = 'CARRYFORWARD'
            sched_names.append((sched,self._sched[sched]['NAME'], platform, freq, action))
            for job in self._sched[sched]['CONTAINS']: sched_jobs.append((sched,job))
            for link in self._sched[sched]['PRECEDES']: sched_links.append((sched,link))
            for needs in self._sched[sched]['NEEDS']: sched_needs.append((sched,needs))
            for comments in self._sched[sched]['COMMENTS']: sched_comments.append((sched,comments))
            for opens in self._sched[sched]['OPENS']: sched_opens.append((sched,opens))
        #Add to sql tables
        c.executemany('INSERT INTO SCHEDULE (SCHEDULE, NAME, PLATFORM, FREQ, ACTION) VALUES (?,?,?,?, ?)', sched_names)
        c.executemany('INSERT INTO SCH_LINES (SCHEDULE, JOB) VALUES (?,?)', sched_jobs)
        c.executemany('INSERT INTO SCH_LINKS (SCHEDULE, PRECEDES) VALUES (?,?)', sched_links)
        c.executemany('INSERT INTO SCH_NEEDS (SCHEDULE, NEEDS) VALUES (?,?)', sched_needs)
        c.executemany('INSERT INTO SCH_COMMENTS (SCHEDULE, COMMENT) VALUES (?,?)', sched_comments)
        c.executemany('INSERT INTO SCH_OPENS (SCHEDULE, OPENS) VALUES (?,?)', sched_opens)
        c.executemany('INSERT INTO SCH_ALL (SCHEDULE, LINE) VALUES (?,?)', sched_all)
        #Populate Tables by looping through previously stored jobs
        jobs = []
        for job in self._jobs.keys():
            platform = job[0:job.find('#')]
            jobs.append((job, platform, self._jobs[job]['DESCRIPTION'], self._jobs[job]['SCRIPT'],
                         self._jobs[job]['CONTROL-FILE']))
        c.executemany('INSERT INTO JOBS (JOB, PLATFORM, DESCRIPTION, SCRIPT, CTRL_FILE) VALUES (?, ?, ?, ?, ?)', jobs)
        conn.commit()