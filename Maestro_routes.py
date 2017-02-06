import os, sqlite3, subprocess
import sys, json

from Schedule import Schedule
from bottle import Bottle, run, template, request, static_file, abort


def getDataDir():
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

def draw(dependencies):
    """
    Starting from current schedule output all succeeding and preceeding schedules
    recursively in Graphviz format. Run Graphviz to create an svg file picture
    """
    f = open(graphvizTxtFile, 'w')
    data = []
    for line in dependencies:
        f.write(line + '\n')
        data.append(line + '\n')
    f.close()
    conn = sqlite3.connect(sqlite_ini_name)
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
        subprocess.call([dotLoc, '-Tsvg', graphvizTxtFile, '-o',
                         graphvizSvgFile], stderr=None, shell=False)
        subprocess.check_call([dotLoc, '-Tsvg', graphvizTxtFile, '-o',
                               graphvizSvgFile], stderr=None, shell=False)
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

def get_file_info():
    """Output the fully qualified paths and names of the  current
    Maestro schedule and job files that are selected"""
    files = {}
    conn = sqlite3.connect(sqlite_ini_name)         # Settings database
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
    except AttributeError: txt = "No initialisations yet performed"
    return files

def set_file_info(f_sched, f_job, f_cal):
    """Set the locations of files for parsing and storage in database
    """
    #Check the ini file exists and if not create it
    conn = sqlite3.connect(sqlite_ini_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS SETTINGS (KEY TEXT PRIMARY KEY, VALUE TEXT)")
    conn.commit()
    #Create entries for the schedule files - Only used for display so user knows what runbook they are using
    c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('SCHEDULE', f_sched))
    c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('JOBS', f_job))
    c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('CALENDARS', f_cal))
    c.execute("INSERT OR REPLACE INTO SETTINGS (KEY, VALUE) VALUES (?,?)", ('DOT', "dot.exe"))
    conn.commit()
    conn.close()

# Web UI handling code
maestro = Bottle()

@maestro.route('<filepath:path>')
def server_static(filepath):
    #Aim of this function is to serve static css and js files
    return static_file(filepath, root=os.getcwd()+os.sep)

@maestro.route('/', method='GET')
@maestro.route('/display', method='GET')
def display():
    """This is the main method used at system startup. First time in
    It displays a combo box of schedules. Second and later it displays
    the jobs or dependencies of the selected schedule (/display route)
    """
    #Check that the schedule database exists
    if not os.path.isfile(db):
        msg = "Schedule has not been loaded, please use 'Properties' menu to do so."
        cols = ["Job", "Job Description", "Job Details"]
        return template('display_schedule', name='', text=msg, r_button_selected='Jobs',
                        display_lines=[], schedules=[], col_names=cols)

    # Main processing if data was already loaded
    global schedule
    schedule = request.GET.schedule.strip()
    type = request.GET.display_type.strip()
    sched_text = s.getSchedName(schedule, db)
    sched_lines = [k for k in s.getAllSchedIds(db)]
    if type == '': type = 'Jobs' #Radio button selection is not maintained in html form
    if type == 'Precedes':
        prec = s.getFollowingSchedules(schedule, db)
        detail_lines = [(sch, s.getSchedName(sch, db)) for sch in prec]
        cols = ["Following Schedule", "Description"]
    elif type == 'Follows':
        prev = s.getPreviousSchedules(schedule, db)
        detail_lines = [(sch, s.getSchedName(sch, db)) for sch in prev]
        cols = ["Preceding Schedule", "Description"]
    else: #'Jobs' or undefined (don't remove the undefined option or things will break elsewhere)
        jobs = s.getScheduleJobs(schedule, db)
        detail_lines = [(j, s.getJobName(j, db), s.getJobScript(j, db)) for j in jobs]
        cols = ["Job", "Job Description", "Job Details"]
    return template('display_schedule', name=schedule, text=sched_text, r_button_selected=type,
                        display_lines=detail_lines, schedules=sched_lines, col_names=cols)

@maestro.route('/search', method='GET')
def search():
    search_string = request.GET.search.strip()
    results = s.findtext(search_string, db)
    return template('search_results', result_lines=results)

@maestro.route('/show_full_schedule', method='GET')
def show_full_schedule():
    """Only purpose of this method is to display an empty form in response to menu click
    on display_schedule.html. Method get_sched_lines will populate the form in response
    to an AJAX call
    """
    return template('show_full_schedule')

@maestro.route('/get_sched_lines', method="POST")
def get_sched_lines():
    """Return all the schedule. Invoked by AJAX call in show_full_schedule.html"""
    schedule = request.cookies.schedule
    s_lines = s.getFullSchedule(schedule, db)
    return json.dumps(s_lines)

@maestro.route('/show_calendars')
def show_full_schedule():
    results = s.get_calendars(db)
    return template('show_calendars', result_lines=results)

@maestro.route('/get_svg_data', method='POST')
def dependency_map():
    """Display dependency map from chosen schedule.
    schedule is returned by AJAX call from server"""
    schedule = request.cookies.SVGObject
    results = s.getGraphvizPart(schedule, 'Y', db)
    error_thrown , msg = draw(results) #Outputs an svg file to be picked up by javascript in the web page
    if error_thrown: err = 'True' #Bottle seems to have trouble returning a logical
    else: err = 'False'
    return json.dumps({"error" : err, 'message' : msg}) #convert to JSON for easier reading in browser

@maestro.route('/get_ctl_file_svg_data', method='POST')
def dependency_map():
    """Display dependency map from chosen control file.
    control file is returned by AJAX call from server"""
    ctl_file = request.cookies.SVGObject
    results = s.getControlFileDependentScheds(ctl_file, db)
    error_thrown , msg = draw(results) #Outputs an svg file to be picked up by javascript in the web page
    if error_thrown: err = 'True' #Bottle seems to have trouble returning a logical
    else: err = 'False'
    return json.dumps({"error" : err, 'message' : msg}) #convert to JSON for easier reading in browser

@maestro.route('/get_svg_data_full', method='POST')
def dependency_map():
    """Display connection map from chosen schedule.
    schedule is returned by AJAX call from server"""
    schedule = request.cookies.SVGObject
    results = s.getAllConnected(schedule, 'Y', db)
    error_thrown , msg = draw(results) #Outputs an svg file to be picked up by javascript in the web page
    if error_thrown: err = 'True' #Bottle seems to have trouble returning a logical
    else: err = 'False'
    return json.dumps({"error" : err, 'message' : msg}) #convert to JSON for easier reading in browser

@maestro.route('/display_svg')
def display_svg_form():
    """Only purpose of this method is to display an empty form in response to menu click
    on display_schedule.html. Method dependency_map will populate the form in response
    to an AJAX call
    """
    return template('display_svg')

@maestro.route('/display_svg_full')
def display_svg_form():
    """Only purpose of this method is to display an empty form in response to menu click
    on display_schedule.html. Method dependency_map will populate the form in response
    to an AJAX call
    """
    return template('display_svg_full')

@maestro.route('/show_control_files')
def show_control_files():
    results = s.getControlFiles(db)
    return template('control_files',result_lines=results)

@maestro.route('/show_resources')
def show_resourcess():
    results = s.get_resources(db)
    return template('resources',result_lines=results)

@maestro.route('/show_control_file_deps', method="POST")
def show_resource_deps():
    #resource = request.GET.resource.strip()
    resource = request.cookies.SVGObject
    results = s.getControlFileDependentScheds(db, resource)
    error_thrown , msg = draw(results) #Outputs an svg file to be picked up by javascript in the web page
    if error_thrown: err = 'True' #Bottle seems to have trouble returning a logical
    else: err = 'False'
    return json.dumps({"error" : err, 'message' : msg}) #convert to JSON for easier reading in browser

@maestro.route('/show_resource_deps', method="POST")
def show_resource_deps():
    #resource = request.GET.resource.strip()
    resource = request.cookies.SVGObject
    results = s.get_resource_dependent_scheds(db, resource)
    error_thrown, msg = draw(results)
    if error_thrown: err = 'True' #Bottle seems to have trouble returning a logical
    else: err = 'False'
    return json.dumps({"error" : err, 'message' : msg}) #convert to JSON for easier reading in browser

@maestro.route('/upload_schedule_files', method="GET")
def find_schedule_files():
    """returns a form to allow selection of the schedule files for upload to server"""
    return template('upload_schedule_files')

@maestro.route('/store_schedule_data', method='POST')
def load_file_locs():
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
    set_file_info(sf_name, jf_name, cf_name)
    #Get rid of any old files of same name hanging around
    try:
        os.remove(sf_name)
        os.remove(jf_name)
        os.remove(cf_name)
    except (IOError): pass
    sched_file.save(os.getcwd())
    job_file.save(os.getcwd())
    cal_file.save(os.getcwd())
    #Populate sql database from uploaded flat files
    s.read_runbook_files(sqlite_ini_name, db)
    msg = 'Files uploaded and database update complete.'
    return template ("application_messages", message=msg)

@maestro.route('/show_file_locs', method='GET')
def show_file_locs():
    locs = get_file_info()
    return template('show_file_locs', locations=locs)

@maestro.route('/display_jobs', method='GET')
def display_jobs():
    job = request.GET.job.strip()
    job_lines = s.getFullJob(job, db)
    return template('display_jobs', result_lines=job_lines)

@maestro.route('/get_text', method="POST")
def get_text():
    """
    In response to a click on SVG schedule graph use schedule id to return the schedule text
    """
    schedule = request.cookies.graph_click_schedule
    #schedule = request.cookies.schedule
    text = s.getSchedName(schedule, db)
    return text

@maestro.route("/visjs_dependency_map")
def visjs_dependency_map():
    """Only purpose of this method is to display an empty form in response to menu click
    on display_schedule.html. Method dependency_map will populate the form in response
    to an AJAX call
    """
    return template('visjs_dependency_map')

@maestro.route("/visjs_get_map_text", method="POST")
def visjs_get_map_text():
    """Experimental: Try to use vis.js in browser to render the map
    Display dependency map from chosen schedule.
     schedule is returned by AJAX call from server"""
    schedule = request.cookies.schedule
    #schedule = list(request.forms.keys())[0]
    results = s.getGraphvizPart(schedule, 'Y', db)
    f = open(graphvizTxtFile, 'w')
    for line in results:
        f.write(line + '\n')
    f.close()
    return template('visjs_dependency_map')

# Initialisations
datadir = getDataDir()  # os.getcwd() + os.sep
db = datadir + os.sep + 'schedule.db'
sqlite_ini_name = 'ini.db'
graphviz_svg_file = "Graphviz.svg"
graphvizTxtFile = datadir + os.sep + "Graphviz.txt"
graphvizSvgFile = datadir + os.sep + graphviz_svg_file
s = Schedule()
#schedule -> text is a Global variable used to persist the current schedule
#Note having such a global variable at the server is problematic since it means there can
#only be one current schedu
# le across all users. Need to replace with cookies on client side.
#schedule = ''

run(maestro, host='localhost', port=8080, debug=True, reloader=True)

#TODO How to send a message from the server
