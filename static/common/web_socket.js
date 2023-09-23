"use strict";
const UUID = crypto.randomUUID();
print_info(info_text(UUID));
let ws_event_subscription = null;
function connect() {
    print_warn("connect WebSocket in page");
    const host_server = location.host;
    let ws_str = "wss://";
    if (location.protocol !== "https:") {
        print_warn("http in WebSocket");
        ws_str = "ws://";
    }
    let ws = new WebSocket(ws_str + host_server + "/ws");
    ws.onopen = function () {
        // subscribe to some channels
        // ws.send(JSON.stringify({ subscribe: UUID }));
        // print_debug(info_text(`subscribe:${UUID}`));
        //ws.send(JSON.stringify({ subscribe: "A001" }));
    };

    ws.onclose = function (e) {
        console.log("Socket is closed. Reconnect will be attempted in 5 second.", e.reason);
        toastMixin.fire({
            title: `Server Reload`,
            text: "reload......",
            icon: "warning",
        });
        location.reload();
    };

    ws.onerror = function (err) {
        console.error("Socket encountered error: ", err.message, "Closing socket");
        ws.close();
    };

    ws.onmessage = function (event) {
        let msg_from_ws = event.data;
        let json_msg = null;
        // debug(event);
        try {
            json_msg = JSON.parse(event.data);
        } catch (error) {
            print_info(info_text(msg_from_ws));
            if (msg_from_ws == "Connect to Server Success") {
                debug("ON LINE");
            }
            if (msg_from_ws == "location.reload()") {
                location.reload();
            }
            if (msg_from_ws.startsWith("notification:")) {
                // print_info(info_text("notification"));
                showNotification("ข้อความแจ้งเตือน", msg_from_ws);
            }
        }
        if (json_msg) {
            // print_info(json_msg);
            if (ws_event_subscription) {
                ws_event_subscription(json_msg);
            }
        }
    };

    function sendMessage(event) {
        var input = document.getElementById("messageText");
        ws.send(input.value);
        input.value = "";
        event.preventDefault();
    }
}
connect();
