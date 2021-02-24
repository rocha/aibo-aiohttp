(function run() {
    const statusElement = document.getElementById('status');
    const eventsElement = document.getElementById('events');

    async function status() {
        const response = await fetch('/status', { method: 'GET' });
        const data = await response.json();
        const text = JSON.stringify(data, null, 2);
        statusElement.textContent = text;
    }

    function connect() {
        const ws = new WebSocket(`wss://${window.location.host}/ws`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const text = JSON.stringify(data, null, 2);
            eventsElement.textContent += `${text}\n\n`;
            status();
        };

        ws.onclose = () => {
            setTimeout(connect, 5000);
        };
    }

    status();
    connect();
}());
