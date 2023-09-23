/** ========================================================================
 *?                           Javascript Class Definition
 * ?                            Serial Device
 *========================================================================**/
"use strict";
// ************************************ CONST VARIABLE ************************************//
class SerialDevice {
    constructor(options = {}) {
        // ? constructor
        this.options = options;
        this.onError = null;
        this.onConnect = null;
        this.onDisconnect = null;
        this.onReceive = null;
        this.port = null;
        this.keepReading = null;
        this.writer = null;
        this.reader = null;
        this.status = null;
        this.filters = [
            { usbVendorId: 0x2341, usbProductId: 0x0043 },
            { usbVendorId: 0x2341, usbProductId: 0x0001 },
            { usbVendorId: 0x1a86, usbProductId: 0x7523 },
            { usbVendorId: 0x10c4, usbProductId: 0xea60 },
        ];
        this.uint8Encoder = new TextEncoder();
        console.log("Construct");
    }
    getDevice() {
        return this.options;
    }

    async init(baudRate = 9600) {
        if (!this.keepReading) {
            this.keepReading = true;
            // connect_serial_open();
            try {
                this.port = await navigator.serial.requestPort({ filters: this.filters });
                await this.port.open({ baudRate: baudRate });
            } catch (error) {
                console.error(error);
                this.keepReading = false;
                if (this.onError) {
                    this.onError(error);
                }
                return 0;
            }
            this._readUntilClosed();
            console.log("Connect Port Success");
            this.status = "connected";
            if (this.onConnect) {
                this.onConnect("success");
            }
            return 1;
        } else {
            this.keepReading = false;
            this.writer.releaseLock();
            this.reader.cancel();
            await this._readUntilClosed();
            console.log("Closed port");
            this.status = "disconnect";

            await this.port.close();
        }
    }

    async _executive_cmd(cmd) {
        switch (cmd) {
            case "READY":
                toastMixin.fire({
                    icon: "success",
                    title: "success",
                    text: "READY",
                });
                break;

            default:
                // debug("cmd not found : " + cmd);
                console.log(cmd);
                break;
        }
    }

    async _readUntilClosed() {
        if (this.port == null) {
            return 0;
        }
        let msg = "";
        const utf8decoder = new TextDecoder();

        while (this.port.readable && this.keepReading) {
            this.reader = this.port.readable.getReader();
            this.writer = this.port.writable.getWriter();
            try {
                while (true) {
                    const { value, done } = await this.reader.read();
                    if (done) {
                        // reader.cancel() has been called.
                        this.reader.releaseLock();
                        break;
                    }
                    // value is a Uint8Array.
                    msg += utf8decoder.decode(value);
                    const lines = msg.split("\n");
                    for (let index = 0; index < lines.length - 1; index++) {
                        const e = lines[index].trim();
                        if (e != "") {
                            if (this.onReceive) {
                                this.onReceive(e);
                            } else {
                                this._executive_cmd(e);
                            }
                        }
                    }
                    msg = lines.pop();
                }
            } catch (error) {
                // Handle error...
            } finally {
                // Allow the serial port to be closed later.
                this.reader.releaseLock();
            }
        }
        try {
            this.reader.releaseLock();
            // writer.releaseLock();
        } catch (error) {
            // Handle error...
            debug(error);
        } finally {
            //await this.port.close();
        }

        // await port.forget();
        this.port = null;
        if (this.onDisconnect) {
            this.onDisconnect();
        }
    }

    async sendMsg(msg) {
        console.log("sendMsg >" + msg);
        if (this.port) {
            const buffer = this.uint8Encoder.encode(msg);
            try {
                await this.writer.write(buffer);
                return true;
            } catch (error) {
                console.error(error);
                return null;
            }
        } else {
            console.error("port is not open");
            return null;
        }
    }
}
