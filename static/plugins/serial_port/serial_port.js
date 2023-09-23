/** ========================================================================
 *?                           Javascript
 *========================================================================**/
"use strict";
// ************************************ CONST VARIABLE ************************************//

let keepReading = false;

let reader;
let writer;
let port;
const filters = [
    { usbVendorId: 0x2341, usbProductId: 0x0043 },
    { usbVendorId: 0x2341, usbProductId: 0x0001 },
    { usbVendorId: 0x1a86, usbProductId: 0x7523 },
    { usbVendorId: 0x10c4, usbProductId: 0xea60 },
];
const utf8decoder = new TextDecoder();
const uint8Encoder = new TextEncoder();

let closedPromise;

async function connect_serial() {
    if (!keepReading) {
        keepReading = true;
        // connect_serial_open();
        port = null;
        try {
            port = await navigator.serial.requestPort({ filters: filters });
            const baudRate = 115200;

            await port.open({ baudRate: baudRate });
            debug(port);
        } catch (error) {
            print_error(warn_text(error));
            keepReading = false;
            return 0;
        }
        closedPromise = readUntilClosed();

        setTimeout(() => {
            send_serial("READY\r\n");
        }, 1000);
        return 1;
    } else {
        keepReading = false;
        writer.releaseLock();
        reader.cancel();
        await closedPromise;
        // await port.close();
    }
}

async function readUntilClosed() {
    let msg = "";
    while (port.readable && keepReading) {
        reader = port.readable.getReader();
        writer = port.writable.getWriter();
        try {
            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    // reader.cancel() has been called.
                    reader.releaseLock();
                    break;
                }
                // value is a Uint8Array.
                msg += utf8decoder.decode(value);
                const lines = msg.split("\n");
                for (let index = 0; index < lines.length - 1; index++) {
                    const e = lines[index].trim();
                    if (e != "") {
                        executive_cmd(e);
                    }
                }
                msg = lines.pop();
            }
        } catch (error) {
            // Handle error...
        } finally {
            // Allow the serial port to be closed later.
            reader.releaseLock();
        }
    }
    try {
        reader.releaseLock();
        // writer.releaseLock();
    } catch (error) {
        // Handle error...
        debug(error);
    } finally {
        await port.close();
    }

    // await port.forget();
    port = null;
    toastMixin.fire({
        icon: "info",
        title: "info",
        text: "The serial port is close",
    });
}

async function send_serial(msg) {
    if (port) {
        const buffer = uint8Encoder.encode(msg);
        last_recv = null;
        await writer.write(buffer);
        let _time_out = true;
        debug(last_recv);
        for (let index = 0; index < 100; index++) {
            await sleep(1);
            if (last_recv) {
                // debug(last_recv);
                _time_out = false;
                break;
            }
        }
        if (!_time_out) {
            return last_recv;
        } else {
            print_error(`>> ${msg}`);
            print_error("************************** serial not respond *****************************");
            return null;
        }
    } else {
        print_error("port is not open");
        return null;
    }
}

// setInterval(() => {
//     send_serial("ir#openwt1=1\r\n");
// }, 5000);
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
// ทดสอบ
async function flash_PGM(params) {
    let _TAGS_TEXT = JSON.stringify(TAGS_TEXT);

    const _tags_text = `TAGS_TEXT ${_TAGS_TEXT.replace(" ", "_")}`;
    debug(_tags_text);
    const _ld = await generator_ladder_ld();
    const ladder = _ld.split("\n");
    debug(await send_serial("PGM_START\r\n"));
    debug(await send_serial("PGM:" + _tags_text + "\r\n"));
    for (let index = 0; index < ladder.length; index++) {
        const e = ladder[index];
        const _pgr = "PGM:" + e.trim() + "\r\n";
        await send_serial(_pgr);
    }
    await send_serial("PGM_SUCCESS\r\n");
    // debug("send complete");
}

let last_recv = "";
let buffer_rev = "";
async function executive_cmd(cmd) {
    // debug(cmd);
    buffer_rev += "\r\n" + cmd;
    if (buffer_rev.length > 2048) {
        print_warn(buffer_rev);
        // Toast.fire({
        //     icon: "warning",
        //     title: "buffer_rev overflow",
        //     text: "buffer_rev overflow",
        // });
        buffer_rev = "";
    }
    last_recv = cmd;
    const msg = cmd.split(":");
    switch (msg[0]) {
        case "READY":
            // send_serial("ทดสอบ\r\n");
            toastMixin.fire({
                icon: "success",
                title: "success",
                text: "READY",
            });
            break;
        case "PGM_SUCCESS":
            // debug("PGM_SUCCESS");

            break;
        case "PGM_OK":
            // debug("PGM_OK");
            break;
        case "PGM_LENGTH":
            debug("PGM_SUCCESS");
            toastMixin.fire({
                icon: "success",
                title: "success",
                text: "upload complete : " + msg[1] + " bytes",
            });
            break;
        default:
            // debug("cmd not found : " + cmd);
            debug(cmd);
            break;
    }
}

async function upload() {
    Swal.fire({
        title: "Do you want to upload_program ?",
        showDenyButton: true,
        // showCancelButton: true,
        confirmButtonText: `Sure`,
        denyButtonText: `Cancel`,
        allowOutsideClick: false,
    }).then((result) => {
        /* Read more about isConfirmed, isDenied below */
        if (result.isConfirmed) {
            // Swal.fire("Saved!", "", "success");
            upload_program();
        } else if (result.isDenied) {
            // Swal.fire("Changes are not saved", "", "info");
        }
    });
}
async function upload_program() {
    if (port) {
        await flash_PGM();
        // Toast.fire({
        //     icon: "success",
        //     title: "success",
        //     text: "upload complete : " + all_b + " bytes",
        // });
    } else {
        toastMixin.fire({
            icon: "error",
            title: "error",
            text: "The serial port is not connect",
        });
    }
}

async function load_program_device() {
    if (port) {
        buffer_rev = "";
        debug(await send_serial("PGM_READ\r\n"));
        let _time_out = true;
        for (let index = 0; index < 100; index++) {
            await sleep(1);
            if (buffer_rev.match("PGM_SUCCESS")) {
                // debug(last_recv);
                _time_out = false;
                break;
            }
        }
        if (_time_out) {
            print_error("_time_out");
            toastMixin.fire({
                icon: "error",
                title: "error",
                text: "load_program_device fail",
            });
        } else {
            // debug(buffer_rev);
            const _result = buffer_rev;
            buffer_rev = "";
            return _result;
        }
    } else {
        toastMixin.fire({
            icon: "error",
            title: "error",
            text: "The serial port is not connect",
        });
    }
    return "";
}
async function load_program() {
    Swal.fire({
        title: "Do you want to download_program ?",
        showDenyButton: true,
        // showCancelButton: true,
        confirmButtonText: `Sure`,
        denyButtonText: `Cancel`,
        allowOutsideClick: false,
    }).then(async (result) => {
        /* Read more about isConfirmed, isDenied below */
        if (result.isConfirmed) {
            // Swal.fire("Saved!", "", "success");
            const data = await load_program_device();
            debug(data);
            create_ladder(data);
        } else if (result.isDenied) {
            // Swal.fire("Changes are not saved", "", "info");
        }
    });
}

async function send_serial_test() {
    const _msg = $("#send_serial_test").val();
    debug("send_serial_test : " + _msg);
    await send_serial(_msg + "\r\n");
}
