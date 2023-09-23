"use strict";
// create and show the notification

let granted = false;

function showNotification(title, msg) {
    navigator.serviceWorker.register("/static/common/service-worker.js").then(function (registration) {
        // print_debug(success_text("Registering service worker successfully"));
        webNotification.showNotification(
            title,
            {
                serviceWorkerRegistration: registration,
                body: msg,
                // data: "I like peas.",
                icon: "/static/image/pk_logo.jpg",
                // vibrate: [200, 100, 200],
                // actions: [
                //     {
                //         action: "Start",
                //         title: "Start",
                //     },
                //     {
                //         action: "Stop",
                //         title: "Stop",
                //     },
                // ],
                // autoClose: 5000, //auto close the notification after 4 seconds (you can manually close it via hide function)
            },
            function onShow(error, hide) {
                if (error) {
                    window.alert("Unable to show notification: " + error.message);
                } else {
                    console.log("Notification Shown.");

                    setTimeout(function hideNotification() {
                        console.log("Hiding notification....");
                        hide(); //manually close the notification (you can skip this if you use the autoClose option)
                    }, 5000);
                }
            }
        );
    });
}

async function set_notifications() {
    // navigator.serviceWorker.ready.then(function (serviceWorker) {
    //     serviceWorker.showNotification(title, options);
    // });
    if (Notification.permission === "granted") {
        granted = true;
    } else if (Notification.permission !== "denied") {
        let permission = await Notification.requestPermission();
        granted = permission === "granted" ? true : false;
    }

    try {
        const notification_info_box = document.getElementById("notification_info_box");
        if (notification_info_box) {
            if (granted) {
                notification_info_box.innerHTML = "You allow the notifications";

                // showNotification("Notification");
            } else {
                notification_info_box.innerHTML = "You blocked the notifications";
            }
        }
    } catch (error) {
        console.error(error);
    }
}

set_notifications();

// webNotification.showNotification(
//     "Example Notification",
//     {
//         body: "Notification Text...",
//         icon: "my-icon.ico",
//         onClick: function onNotificationClicked() {
//             console.log("Notification clicked.");
//         },
//         autoClose: 4000, //auto close the notification after 4 seconds (you can manually close it via hide function)
//     },
//     function onShow(error, hide) {
//         if (error) {
//             window.alert("Unable to show notification: " + error.message);
//         } else {
//             console.log("Notification Shown.");

//             setTimeout(function hideNotification() {
//                 console.log("Hiding notification....");
//                 hide(); //manually close the notification (you can skip this if you use the autoClose option)
//             }, 5000);
//         }
//     }
// );
