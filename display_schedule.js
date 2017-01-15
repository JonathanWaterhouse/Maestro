function getJobId(i,j){
    var id = 'key_' + i + j;
    var key = document.getElementById(id).innerHTML;

    if (document.getElementsByName('display_type')[1].checked |
            document.getElementsByName('display_type')[2].checked){
    //Display schedule
        document.getElementById('schedule_combo').value = key;
        document.getElementById('main_screen').submit();
    }
    else {
    //Display Job
        document.getElementById('hidden_job_name').value = key;
        document.getElementById('hidden_job').submit();
    }
}
function submitMainForm(){
    //store cookie
    var s = document.getElementById("schedule_combo").value
    document.cookie = "schedule=" + s + "; path=/"
    //submit form
    document.getElementById('main_screen').submit()
}
function search(){
    document.getElementById('search_box').submit()
}
function setCookie(){
    var s = document.getElementById("schedule_combo").value
    document.cookie = "schedule=" + s + "; path=/"
}
