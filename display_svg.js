function onDisplaySVGLoad(target_page){
    //Request creation of SVG file on server via AJAX
    var xhr_reqst_svg = new XMLHttpRequest();
    xhr_reqst_svg.onreadystatechange = function(){
        if (this.readyState == 4 && this.status == 200) {
            //Check out any error messages
            var error_obj = JSON.parse(this.responseText);
            if (error_obj['error'] == 'True'){
                alert("Server returned : \n\n'" + error_obj['message'] + "'\n\n" +
                    "Please check the Graphviz is installed from http://www.graphviz.org and that dot.exe is on your path." );
                window.close()
                return;
            }

            //Get the SVG data (created by python server) via AJAX request
            var xhr = new XMLHttpRequest();
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
    }
    //This places svg file in a local server folder. The onreadytstatechange function above
    //causes this svg file to be read into the browser
    if (target_page == 'dependency') {xhr_reqst_svg.open("POST","/get_svg_data",false);}
    else {xhr_reqst_svg.open("POST","/get_svg_data_full",false);}
    xhr_reqst_svg.send("");
}

function onSVGClick(evt){
    var x = evt.target.innerHTML; //The schedule name
    document.cookie = "graph_click_schedule=" + x + "; path=/"
    //Ask for text name of schedule
    var xhr_text = new XMLHttpRequest();
    xhr_text.onreadystatechange = function(){
        if (this.readyState == 4 && this.status == 200) {
            var sched_text = this.responseText;
            conf = confirm(x + "\n" + sched_text + '\n\n' + "Do you want to display the schedule?");
            if (conf){
                //Submit request to display the selected schedule
                document.getElementById('hidden_schedule_id').value = x;
                document.cookie = "schedule=" + x + "; path=/"
                document.getElementById('hidden_schedule').submit();
            }
        }
    }
    xhr_text.open("POST","/get_text",false);
    xhr_text.send();

    }

