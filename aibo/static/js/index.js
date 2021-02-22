(function () {
    const status_el = document.getElementById('status');
    const events_el = document.getElementById('events');

    function status() {
        const request = new XMLHttpRequest();
        request.open('GET', '/status', true);
        request.onload = function () {
            if (this.status >= 200 && this.status < 400) {
                const data = JSON.parse(this.response);
                const text = JSON.stringify(data, null, 2);
                status_el.textContent = text;
            }
        };
        request.send();
    }

    function connect() {
        const ws = new WebSocket(`wss://${window.location.host}/ws`);

        ws.onmessage = function (event) {
            console.log(event.data);
            const data = JSON.parse(event.data);
            const text = JSON.stringify(data, null, 2);
            events_el.textContent += `${text}\n\n`;
            status();
        };

        ws.onclose = function (event) {
            setTimeout(connect, 5000);
        };
    }

    status();
    connect();
}());
