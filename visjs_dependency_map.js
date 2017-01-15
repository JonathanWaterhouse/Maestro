function loadDotFile(){
    var oFrame = document.getElementById('dotFile');
    var strRawContents = oFrame.contentWindow.document.body.childNodes[0].innerHTML;
    var arrayLines = strRawContents.split('\n');
    var DOTstring = '';
    for (i = 0; i < arrayLines.length; i++){
        //The read file replaces the ">" symbol with "&gt". We need to put it back
        var line = arrayLines[i].replace('-&gt;' ,'->')
        /*My original dot file does not have ";" separating the nodes. visjs seems to require they are there.
        The first line of the incoming dot file and the last are not nodes and so don't need the ";"*/
        if (i == 0 || line == "}"){DOTstring = DOTstring.concat(line);}
        else if (line == '') continue;
        else {DOTstring = DOTstring.concat(line, ';');}
    }
    //Following code is copied straight out of visjs manual
    var parsedData = vis.network.convertDot(DOTstring);
    var data = {
          nodes: parsedData.nodes,
          edges: parsedData.edges
    }
    var options = parsedData.options;
    //options for vis.js layout engine.
    var options = {
      layout: {
        randomSeed: undefined,
        improvedLayout:true,
        hierarchical: {
          enabled: true,
          levelSeparation: 150,
          nodeSpacing: 900,
          treeSpacing: 900,
          blockShifting: true,
          edgeMinimization: false,
          parentCentralization: false,
          direction: 'UD',        // UD, DU, LR, RL
          sortMethod: 'directed'   // hubsize, directed
        }
      },
      physics:{
        enabled: true,
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.3,
          springLength: 95,
          springConstant: 0.04,
          damping: 0.09,
          avoidOverlap: 0
        },
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springConstant: 0.08,
          springLength: 100,
          damping: 0.4,
          avoidOverlap: 0
        },
        repulsion: {
          centralGravity: 0.2,
          springLength: 200,
          springConstant: 0.05,
          nodeDistance: 100,
          damping: 0.09
        },
        hierarchicalRepulsion: {
          centralGravity: 0.1,
          springLength: 410,
          springConstant: 0.01,
          nodeDistance: 150,
          damping: 0.12
        },
        maxVelocity: 50,
        minVelocity: 0.1,
        solver: 'hierarchicalRepulsion',
        stabilization: {
          enabled: true,
          iterations: 1000,
          updateInterval: 100,
          onlyDynamicEdges: false,
          fit: true
        },
        timestep: 0.5,
        adaptiveTimestep: true
      },
      edges:{
          smooth: {
              enabled: true,
              type: "cubicBezier",
              forceDirection: "vertical",
              roundness: 0.5
        }
      }
    }
    //Some code to place the visjs output in the html <div>
    var container = document.getElementById('graph');
    var network = new vis.Network(container, data, options);
    document.getElementsByTagName('canvas')[0].width = "999";
    document.getElementsByTagName('canvas')[0].height = "999";
    /*The following allows us to capture a click on a node, capture the text (which is a node id), pass it to the server
    and ask for a correspondin human readable text value to be displayed in a "conf" message. Depending on the
    response to the messag box from the user, we either remove the message or display the full schedule whose node
    the user clicked on */
    network.on("click", function (params) {
        params.event = "[original event]";
        x = params["nodes"][0]
        //Ask for text name of schedule
        var xhr_text = new XMLHttpRequest();
        xhr_text.onreadystatechange = function(){
            if (this.readyState == 4 && this.status == 200) {
                var sched_text = this.responseText;
                conf = confirm(x + '\n' + sched_text + '\n\n' + "Do you want to display the schedule?");
                if (conf){
                    //Submit request to display the selected schedule
                    document.getElementById('hidden_schedule_id').value = x;
                    document.getElementById('hidden_schedule').submit();
                }
            }
        }
        xhr_text.open("POST","/get_text",false);
        xhr_text.send(x);
    });
}
function createGraphvizFile(target_page){
    //Get the current schedule name from cookie
    cookieName = "schedule" + "=";
    var c = document.cookie;
    var cList = c.split(";");
    for (var i = 0; i < c.length; i++){
        var cEntry = cList[i];
        if (cEntry.indexOf(cookieName) == 0) {
            var s = cEntry.substring(cookieName.length, cEntry.length);
            break;
        }
    }
    //Request creation of text file on server via AJAX
    var xhr_reqst = new XMLHttpRequest();
    xhr_reqst.onreadystatechange = function(){
        if (this.readyState == 4 && this.status == 200) { //File created for another method
                }
    }
    if (target_page == 'dependency') {xhr_reqst.open("POST","/visjs_get_map_text",false);}
    else {xhr_reqst.open("POST","/get_svg_data_full",false);}
    xhr_reqst.send(s);
    //Try and refresh the iframe holding the data
    var oFrame = document.getElementById('dotFile');
    oFrame.contentWindow.location.reload(); //Make sure we got latest file
}