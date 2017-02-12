import os, sqlite3, subprocess
import sys, json

from Schedule import Schedule
from bottle import Bottle, run, template, request, static_file

# TODO How to best handle long running server requests in the browser
# TODO visjs layout is nothing like as good as graphviz dot. Any other browser based alternatives?


class Maestro(Bottle):
    def __init__(self,name):
        """Run Bottle init. Initialise certain locally required variables. Set up the routes to
        allow interception of url's"""
        super(Maestro, self).__init__()
        # Instance variables
        self.name = name
        datadir = self.getDataDir()  # os.getcwd() + os.sep
        self._db = datadir + os.sep + 'schedule.db'
        self._sqlite_ini_name = 'ini.db'
        self._graphviz_svg_file = "Graphviz.svg"
        self._graphvizTxtFile = datadir + os.sep + "Graphviz.txt"
        self._graphvizSvgFile = datadir + os.sep + self._graphviz_svg_file
        self._s = Schedule()
        # Routes
        self.route('/', method='GET', callback=self.display)
        self.route('/display', method='GET', callback=self.display)
        self.route('<filepath:path>', callback=self.serve_static_file)
        self.route('/search', method='GET', callback=self.search)
        self.route('/show_full_schedule', method='GET', callback=self.show_full_schedule)
        self.route('/get_sched_lines', method="POST", callback=self.get_sched_lines)
        self.route('/display_jobs', method='GET', callback=self.display_jobs)
        self.route('/show_calendars',callback=self.show_calendars)
        self.route('/display_svg', callback=self.display_svg_form)
        self.route('/get_svg_data', method='POST', callback=self.dependency_map)
        self.route('/get_text', method="POST", callback=self.get_text)
        self.route('/display_svg_full', callback=self.display_svg_form_full)
        self.route('/get_svg_data_full', method='POST', callback=self.dependency_map_full)
        self.route('/show_control_files', callback=self.show_control_files)
        self.route('/show_control_file_deps', method="POST", callback=self.show_ctl_file_deps)
        self.route('/show_resources', callback=self.show_resources)
        self.route('/show_resource_deps', method="POST", callback=self.show_resource_deps)
        self.route('/upload_schedule_files', method="GET", callback=self.find_schedule_files)
        self.route('/store_schedule_data', method='POST', callback=self.load_file_locs)
        self.route('/show_file_locs', method='GET', callback=self.show_file_locs)
        self.route("/visjs_dependency_map", callback=self.visjs_dependency_map)
        self.route("/visjs_get_map_text", method="POST", callback=self.visjs_get_map_text)

    def serve_static_file(self, filepath):
        # Aim of this method is to serve static css and js files
        return static_file(filepath, root=os.getcwd() + os.sep)

    def getDataDir(self):
        """
        This application may have a windows executable built from it using cx_Freeze in
        which case  the local directly that the script runs from assumed by python
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

    def display(self):
        """This is the main method used at system startup. First time in
        It displays a combo box of schedules. Second and later it displays
        the jobs or dependencies of the selected schedule (/display route)
        """
        # Check that the schedule database exists
        if not os.path.isfile(self._db):
            msg = "Schedule has not been loaded, please use 'Properties' menu to do so."
            cols = ["Job", "Job Description", "Job Details"]
            return template('display_schedule', name='', text=msg, r_button_selected='Jobs',
                            display_lines=[], schedules=[], col_names=cols)

        # Main processing if data was already loaded
        # global schedule
        schedule = request.GET.schedule.strip()
        type = request.GET.display_type.strip()
        sched_text = self._s.getSchedName(schedule, self._db)
        sched_lines = [k for k in self._s.getAllSchedIds(self._db)]
        if type == '': type = 'Jobs'  # Radio button selection is not maintained in html form
        if type == 'Precedes':
            prec = self._s.getFollowingSchedules(schedule, self._db)
            detail_lines = [(sch, self._s.getSchedName(sch, self._db)) for sch in prec]
            cols = ["Following Schedule", "Description"]
        elif type == 'Follows':
            prev = self._s.getPreviousSchedules(schedule, self._db)
            detail_lines = [(sch, self._s.getSchedName(sch, self._db)) for sch in prev]
            cols = ["Preceding Schedule", "Description"]
        else:  # 'Jobs' or undefined (don't remove the undefined option or things will break elsewhere)
            jobs = self._s.getScheduleJobs(schedule, self._db)
            detail_lines = [(j, self._s.getJobName(j, self._db), self._s.getJobScript(j, self._db)) for j in jobs]
            cols = ["Job", "Job Description", "Job Details"]
        return template('display_schedule', name=schedule, text=sched_text, r_button_selected=type,
                        display_lines=detail_lines, schedules=sched_lines, col_names=cols)

    def display_jobs(self):
        """Display the details of a given job. The job is selected from the schedule display screen by
        clicking on a job line"""
        job = request.GET.job.strip()
        job_lines = self._s.getFullJob(job, self._db)
        return template('display_jobs', result_lines=job_lines)

    def search(self):
        """React to a request to search all schedule lines for specific text."""
        search_string = request.GET.search.strip()
        results = self._s.findtext(search_string, self._db)
        return template('search_results', result_lines=results)

    def show_full_schedule(self):
        """Only purpose of this method is to display an empty form in response to menu click
        on display_schedule.html. Method get_sched_lines will populate the form in response
        to an AJAX call
        """
        return template('show_full_schedule')

    def get_sched_lines(self):
        """Return all the schedule. Invoked by AJAX call in show_full_schedule.html"""
        schedule = request.cookies.schedule
        s_lines = self._s.getFullSchedule(schedule, self._db)
        return json.dumps(s_lines)

    def show_calendars(self):
        """show the full set of maestro calendars"""
        results = self._s.get_calendars(self._db)
        return template('show_calendars', result_lines=results)

    def display_svg_form(self):
        """Only purpose of this method is to display an empty form in response to menu click
        on display_schedule.html. Method dependency_map will populate the form in response
        to an AJAX call
        """
        return template('display_svg')

    def dependency_map(self):
        """Display dependency map from chosen schedule.
        schedule is returned by AJAX call from server"""
        schedule = request.cookies.SVGObject
        results = self._s.getGraphvizPart(schedule, 'Y', self._db)
        error_thrown, msg = self._draw(results)  # Outputs an svg file to be picked up by javascript in the web page
        if error_thrown:
            err = 'True'  # Bottle seems to have trouble returning a logical
        else:
            err = 'False'
        return json.dumps({"error": err, 'message': msg})  # convert to JSON for easier reading in browser

    def display_svg_form_full(self):
        """Only purpose of this method is to display an empty form in response to menu click
        on display_schedule.html. Method dependency_map will populate the form in response
        to an AJAX call
        """
        return template('display_svg_full')

    def dependency_map_full(self):
        """Display connection map from chosen schedule.
        schedule is returned by AJAX call from server"""
        schedule = request.cookies.SVGObject
        results = self._s.getAllConnected(schedule, 'Y', self._db)
        error_thrown, msg = self._draw(results)  # Outputs an svg file to be picked up by javascript in the web page
        if error_thrown:
            err = 'True'  # Bottle seems to have trouble returning a logical
        else:
            err = 'False'
        return json.dumps({"error": err, 'message': msg})  # convert to JSON for easier reading in browser

    def show_control_files(self):
        """Return an html page containing a selection box filled with available control files"""
        results = self._s.getControlFiles(self._db)
        return template('control_files', result_lines=results)

    def show_ctl_file_deps(self):
        """In response to selected control file on control_files.html returns all succededing
        schedules and draws an svg diagram of them. This routine is called by AJAX from the html page."""
        resource = request.cookies.SVGObject
        results = self._s.getControlFileDependentScheds(self._db, resource)
        error_thrown, msg = self._draw(results)  # Outputs an svg file to be picked up by javascript in the web page
        if error_thrown:
            err = 'True'  # Bottle seems to have trouble returning a logical
        else:
            err = 'False'
        return json.dumps({"error": err, 'message': msg})  # convert to JSON for easier reading in browser

    def show_resources(self):
        results = self._s.get_resources(self._db)
        return template('resources', result_lines=results)

    def show_resource_deps(self):
        # resource = request.GET.resource.strip()
        resource = request.cookies.SVGObject
        results = self._s.get_resource_dependent_scheds(self._db, resource)
        error_thrown, msg = self._draw(results)
        if error_thrown:
            err = 'True'  # Bottle seems to have trouble returning a logical
        else:
            err = 'False'
        return json.dumps({"error": err, 'message': msg})  # convert to JSON for easier reading in browser

    def get_text(self):
        """
        In response to a click on SVG schedule graph use schedule id to return the schedule text
        """
        schedule = request.cookies.graph_click_schedule
        # schedule = request.cookies.schedule
        text = self._s.getSchedName(schedule, self._db)
        return text

    def find_schedule_files(self):
        """returns a form to allow selection of the schedule files for upload to server"""
        return template('upload_schedule_files')

    def load_file_locs(self):
        """Upload the schedule file locations to ini database"""
        sched_file = request.POST.sched_file
        job_file = request.POST.job_file
        cal_file = request.POST.cal_file
        s_name, s_ext = os.path.splitext(sched_file.filename)
        j_name, j_ext = os.path.splitext(job_file.filename)
        c_name, c_ext = os.path.splitext(cal_file.filename)
        sf_name = os.getcwd() + os.sep + s_name + s_ext
        jf_name = os.getcwd() + os.sep + j_name + j_ext
        cf_name = os.getcwd() + os.sep + c_name + c_ext
        self._set_file_info(sf_name, jf_name, cf_name)
        # Get rid of any old files of same name hanging around
        try:
            os.remove(sf_name)
            os.remove(jf_name)
            os.remove(cf_name)
        except (IOError):
            pass
        sched_file.save(os.getcwd())
        job_file.save(os.getcwd())
        cal_file.save(os.getcwd())
        # Populate sql database from uploaded flat files
        self._s.read_runbook_files(self._sqlite_ini_name, self._db)
        msg = 'Files uploaded and database update complete.'
        return template("application_messages", message=msg)

    def _set_file_info(self, f_sched, f_job, f_cal):
        """Set the locations of files for parsing and storage in database
        """
        # Check the ini file exists and if not create it
        conn = sqlite3.connect(self._sqlite_ini_name)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS SETTINGS (KEY TEXT PRIMARY KEY, VALUE TEXT)")
        conn.commit()
        # Create entries for the schedule files - Only used for display so user knows what runbook they are using
        c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('SCHEDULE', f_sched))
        c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('JOBS', f_job))
        c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('CALENDARS', f_cal))
        c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('DOT', "dot.exe"))
        conn.commit()
        conn.close()

    def show_file_locs(self):
        """retrieve the supporting file locations for this application, that is the schedule, job
        and calendar file names and locations. Allows to tell what weeks files we are using"""
        locs = self._get_file_info()
        return template('show_file_locs', locations=locs)

    def visjs_dependency_map(self):
        """Only purpose of this method is to display an empty form in response to menu click
        on display_schedule.html. Method dependency_map will populate the form in response
        to an AJAX call
        """
        return template('visjs_dependency_map')

    def visjs_get_map_text(self):
        """Experimental: Try to use vis.js in browser to render the map
        Display dependency map from chosen schedule.
         schedule is returned by AJAX call from server"""
        schedule = request.cookies.schedule
        results = self._s.getGraphvizPart(schedule, 'Y', self._db)
        f = open(self._graphvizTxtFile, 'w')
        for line in results:
            f.write(line + '\n')
        f.close()
        return template('visjs_dependency_map')

    def _get_file_info(self):
        """Output the fully qualified paths and names of the  current
        Maestro schedule and job files that are selected"""
        files = {}
        conn = sqlite3.connect(self._sqlite_ini_name)  # Settings database
        c = conn.cursor()
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='DOT'")
        files['DOT'] = c.fetchone()[0]
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='SCHEDULE'")
        files['SCHEDULE'] = c.fetchone()[0]
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='JOBS'")
        files['JOBS'] = c.fetchone()[0]
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='CALENDARS'")
        files['CALENDARS'] = c.fetchone()[0]
        txtList = []
        try:
            for k, v in files.items(): txtList.append(k + ": " + v + "\n")
            txt = "\n".join(txtList)
        except AttributeError:
            txt = "No initialisations yet performed"
        return files

    def _draw(self, dependencies):
        """
        Starting from current schedule output all succeeding and preceeding schedules
        recursively in Graphviz format. Run Graphviz to create an svg file picture
        """
        f = open(self._graphvizTxtFile, 'w')
        data = []
        for line in dependencies:
            f.write(line + '\n')
            data.append(line + '\n')
        f.close()
        conn = sqlite3.connect(self._sqlite_ini_name)
        c = conn.cursor()
        # Settings database
        c.execute("SELECT DISTINCT VALUE FROM SETTINGS WHERE KEY ='DOT'")
        returnObject = c.fetchone()
        # Handle invalid values by asking user to choos correct location
        if returnObject:  # i.e. we got something back
            dotLoc = returnObject[0]
        error_thrown = False
        msg = ''
        try:
            subprocess.call([dotLoc, '-Tsvg', self._graphvizTxtFile, '-o',
                             self._graphvizSvgFile], stderr=None, shell=False)
            subprocess.check_call([dotLoc, '-Tsvg', self._graphvizTxtFile, '-o',
                                   self._graphvizSvgFile], stderr=None, shell=False)
        except (subprocess.CalledProcessError) as e:
            msg = "Returncode {0} command {1} output {2}".format(e.returncode, e.cmd, e.output) \
                  + ". Please ensure that dot.exe is installed and on your path."
            error_thrown = True
        except OSError as e:
            msg = "Returncode = {0} meaning '{1}' file = {2}".format(e.errno, e.strerror, e.filename) \
                  + ". Please ensure that dot.exe is installed and on your path."
            error_thrown = True
        except ValueError as e:
            msg = "ValueError error Handling......." \
                  + ". Please ensure that dot.exe is installed and on your path."
            error_thrown = True

        return error_thrown, msg

if __name__ == '__main__':
    maestro = Maestro('maestro')
    maestro.run(host='localhost', port=8080, debug=True, reloader=True)