(function () {

var status_el = document.getElementById('status');
var events_el = document.getElementById('events');

function status() {
    var request = new XMLHttpRequest();
    request.open('GET', '/status', true)
    request.onload = function() {
        if (this.status >= 200 && this.status < 400) {
            var data = JSON.parse(this.response);
            var text = JSON.stringify(data, null, 2);
            status_el.textContent = text;
        }
    }
    request.send()
}

function connect() {
    var ws = new WebSocket('wss://' + window.location.host + '/ws');
    
    ws.onmessage = function(event) {
        console.log(event.data);
        var data = JSON.parse(event.data)
        var text = JSON.stringify(data, null, 2);
        events_el.textContent += text + '\n\n';
        status();
    }
    
    ws.onclose = function(event) {
        setTimeout(connect, 5000);
    }
}

status();
connect();

}());