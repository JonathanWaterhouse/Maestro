function onDisplaySVGLoad(){
    //Get the SVG data (created by python server) via AJAX request
    xhr = new XMLHttpRequest();
    xhr.open("GET","Graphviz.svg",false);
    // Following line is just to be on the safe side;
    // not needed if your server delivers SVG with correct MIME type
    xhr.overrideMimeType("image/svg+xml");
    xhr.send("");
    //Add svg content into appropriate place in HTML
    document.getElementById("svgContainer")
        .appendChild(xhr.responseXML.documentElement);
    //Add an event listener to each node in the svg graph
    document.getElementsByTagName("g")[0]
    .addEventListener("click",onSVGClick,
    false)
}

function onSVGClick(evt){
    var x = evt.target.innerHTML; //The schedule name
    //Ask for text name of schedule
    var xhr_text = new XMLHttpRequest();
    xhr_text.onreadystatechange = function(){
        if (this.readyState == 4 && this.status == 200) {
            var sched_text = this.responseText;
            conf = confirm(sched_text + '\n\n' + "Do you want to display the schedule?");
            if (conf){
                //Submit request to display the selected schedule
                document.getElementById('hidden_schedule_id').value = x;
                document.getElementById('hidden_schedule').submit();
            }
        }
    }
    xhr_text.open("POST","/get_text",false);
    xhr_text.send(x);
    }

