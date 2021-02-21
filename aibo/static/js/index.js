(function () {

var status_el = document.getElementById('status');
var events_el = document.getElementById('events');

function connect() {
    var ws = new WebSocket('wss://' + window.location.host + '/ws');
    
    ws.onmessage = function(event) {
        console.log(event.data);
        data = JSON.parse(event.data)

        if (data['type'] === 'status') {
            text = JSON.stringify(data['status'], null, 2);
            status_el.textContent = text;
            status_el.textContent += '\n\n[' + data['time'] + ']';
        }

        if (data['type'] === 'event') {
            text = JSON.stringify(data['event'], null, 2);
            events_el.textContent += text + '\n\n';
        }

    }
    
    ws.onclose = function(event) {
        setTimeout(connect, 5000);
    }
}

connect()

}());