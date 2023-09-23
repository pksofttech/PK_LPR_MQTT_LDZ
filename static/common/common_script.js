"use strict";
// Update 08:59

const DEBUG_MODE = true;
const HOME_ROUTE = "/home";

var token = "";
var current_content = "";
var previous_content = "";
// var page_index = 0;

let TOKEN_EXP = 0;

const debug = console.log;
const print_debug = console.log;
const print_info = console.info;
const print_warn = console.warn;
const print_error = console.error;
const success_text = (msg) => {
    return `\u001b[32m${msg}`;
};
const info_text = (msg) => {
    return `\u001b[36m${msg}`;
};
const warn_text = (msg) => {
    return `\u001b[33m${msg}`;
};
// function print_error(msg) {
//     console.log(`%cError: %c ${msg}`, "color:DarkRed;", "color:DarkCyan;");
// }

if (DEBUG_MODE) {
    print_warn("Debug Mode Enable!!!");
}

function dateTimeToStr(dateTime, format = "YYYY/MM/DD HH:mm:ss", _day = 0) {
    if (dateTime == null) {
        return "";
    }
    if (_day > 0) {
        return moment(dateTime).add(_day, "d").format(format);
    }
    return moment(dateTime).format(format);
}
function dateTimeDiff(dateTime_start, dateTime_end, format = "YYYY/MM/DD HH:mm:ss") {
    if (dateTime_start == null) {
        return "";
    }
    if (dateTime_end == null) {
        return moment.utc(moment().diff(moment(dateTime_start, format))).format("HH:mm:ss");
    } else {
        return moment.utc(moment(dateTime_end, format).diff(moment(dateTime_start, format))).format("HH:mm:ss");
    }
}

function time_ref(dateTime_start, dateTime_end, format = "YYYY/MM/DD HH:mm:ss") {
    let t0;
    let t1;

    if (dateTime_start == null) {
        t0 = moment();
    } else {
        t0 = moment(dateTime_start);
    }
    if (dateTime_end == null) {
        t1 = moment();
        return t1.to(t0);
    } else {
        t1 = moment(dateTime_end);
        return t0.to(t1, true);
    }
}

function sec_to_duration(s) {
    const d = parseInt(s / (24 * 3600));
    const h = String(Math.floor(Math.floor((s % 86400) / 3600))).padStart(2, "0");
    const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
    let duration = `${h}:${m}`;
    if (d) {
        duration = `${d} day ` + duration;
    }
    return duration;
}

function sec_to_duration_local(s) {
    const d = parseInt(s / (24 * 3600));
    const h = parseInt((s % (24 * 3600)) / 3600);
    const m = parseInt((s % 3600) / 60);
    let duration = `${h} ชั่วโมง ${m} นาที`;
    if (d) {
        duration = `${d} วัน ` + duration;
    }
    return duration;
}

// var bg_mode_theme = "#19191a";
const toastMixin = Swal.mixin({
    toast: true,
    icon: "success",
    title: "General Title",
    // text: "false",
    position: "center",
    showConfirmButton: false,
    timer: 1500,
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener("mouseenter", Swal.stopTimer);
        toast.addEventListener("mouseleave", Swal.resumeTimer);
    },
});

function isASCII(str) {
    return /^[\x00-\x7F]*$/.test(str);
}

function setCookie(cname, value, expire = 0) {
    if (isASCII(value)) {
        let _expires = "0";
        if (expire != 0) {
            const d = new Date();
            d.setTime(d.getTime() + expire * 1000);
            _expires = d.toGMTString();
        }

        let expires = "expires=" + _expires;
        const _cookie = cname + "=" + value + ";" + expires + ";path=/";
        document.cookie = _cookie;
        debug("Set Cookie:" + _cookie);
    } else {
        debug("Not set Cookie " + value);
    }
}

function getCookie(cname) {
    let name = cname + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(";");
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == " ") {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

async function get_user_session() {
    const user_session = await fetchApi("/login_session", "get", null, "json");
    const ss_user = user_session.username;
    const ss_user_level = user_session.user_level;
    //setCookie("ss_user", ss_user, 0);
    setCookie("ss_user_level", ss_user_level, 0);
    debug(user_session);
    // await Swal.fire(ss_user_level, ss_user, 'success')
    // window.location.href = HOME_ROUTE;
    window.location.reload();
}

async function checkCookie() {
    let _token = getCookie("Authorization");
    if (_token != "") {
        token = _token;
        debug("load by token Auto login by cookie");
        debug(token);

        await get_user_session();
        // window.location.href = HOME_ROUTE
    } else {
        // toastMixin.fire({
        //     title: "สวัดดี\nยินดีต้อนรับ",
        //     icon: "info",
        // });
        debug("ไม่พบการลงชื่อเข้าระบบ");
    }
}

function logout() {
    Swal.fire({
        icon: "info",
        title: "Logout",
        text: "Thankyou",
        footer: "***",
    });
    Swal.fire({
        // background: bg_mode_theme,
        icon: "info",
        title: "Do you want to Logout system?",
        showCancelButton: true,
        confirmButtonText: "OK",
        confirmButtonColor: "LightSeaGreen",
        denyButtonText: `Don't Logout`,
    }).then((result) => {
        /* Read more about isConfirmed, isDenied below */
        if (result.isConfirmed) {
            // Swal.fire("Logout!", "", "success");
            document.cookie = "Authorization=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";

            location.reload();
        }
    });
}

async function login(_user, _password, _remember_check, _app_mode) {
    debug("Login :" + _user + "@" + _password + ":" + String(_remember_check));

    const params_oauth = new URLSearchParams();
    params_oauth.append("username", _user);
    params_oauth.append("password", _password);

    const response = await fetch("oauth", {
        method: "POST",
        body: params_oauth,
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
        },
    });
    const responseData = await response.json();
    debug(responseData);
    if (responseData.access_token != null) {
        token = `${responseData.token_type} ${responseData.access_token}`;
        console.log(_remember_check);
        if (_remember_check) {
            setCookie("Authorization", token, TOKEN_EXP);
            debug("Remember user :" + TOKEN_EXP);
        } else {
            setCookie("Authorization", token, 0);
        }
        setCookie("app_mode", _app_mode, TOKEN_EXP);
        console.log(getCookie("Authorization"));
        await get_user_session();
        // window.location.href = HOME_ROUTE
    } else {
        console.log(responseData);
        Swal.fire("ข้อผิดพลาด", String(responseData.detail), "error").then((result) => {
            return;
        });
    }
}

async function get_headers() {
    const _token = getCookie("Authorization");
    const headers_json = {
        accept: "application/json",
        Authorization: _token,
        "Content-Type": "application/json",
    };
    return headers_json;
}

async function fetchApi(path = "", method = "get", body = null, returnType = "text", header = true) {
    // debug(String(typeof body));
    const _token = getCookie("Authorization");
    const headers_json = {
        accept: "application/json",
        Authorization: _token,
        "Content-Type": "application/json",
    };
    const headers_form = {
        accept: "application/json",
        Authorization: _token,
        // 'Content-Type': 'multipart/form-data',
    };

    let headers = headers_json;
    if (typeof body == "object") {
        // debug("multipart/form-data")
        headers = headers_form;
    }

    let response = null;
    try {
        if (header) {
            response = await fetch(path, {
                method: method,
                headers: headers,
                body: body,
            });
        } else {
            response = await fetch(path, {
                method: method,
                mode: "no-cors",
                //body: body,
            });
        }
    } catch (err) {
        print_warn("fetchApi not response or error: ");
        return null;
    } finally {
        //swal.close();
    }

    switch (response.status) {
        case 401:
            debug(response.status);
            document.cookie = "Authorization=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            Swal.fire("session expires", "กรุณาลงชื่อเข้าใช้งานระบบ", "error").then((result) => {
                location.reload();
            });

            break;
        case 200:
            if (returnType === "text") {
                let _t = await response.text();
                return _t;
            }
            if (returnType === "json") {
                let data = await response.json();
                //debug(data);
                data.status = response.status;
                return data;
            }
            break;
        case 422:
            debug(response);
            await Swal.fire({
                icon: "error",
                title: "422",
                text: response.statusText,
                footer: "ข้อผิดพลาด ระบบทำงานพกพร่องโปรดแจ้งเจ้าหน้าที่ให้แก้ไขครับ....!",
            });
            break;
        case 500:
            await Swal.fire({
                icon: "error",
                title: "Status 500 !",
                text: "ข้อผิดพลาด...ระบบ!",
                footer: "ข้อผิดพลาด ระบบทำงานพกพร่องโปรดแจ้งเจ้าหน้าที่ให้แก้ไขครับ....!",
            });
            break;

        default:
            // debug(response)
            const msg_resp = await response.text();
            toastMixin.fire({
                // background: bg_mode_theme,
                title: `${response.statusText}\n${msg_resp}`,
                icon: "error",
            });
            break;
    }
    return response;
}

function getLocation(href) {
    var match = href.match(/^(https?\:)\/\/(([^:\/?#]*)(?:\:([0-9]+))?)([\/]{0,1}[^?#]*)(\?[^#]*|)(#.*|)$/);
    return (
        match && {
            href: href,
            protocol: match[1],
            host: match[2],
            hostname: match[3],
            port: match[4],
            pathname: match[5],
            search: match[6],
            hash: match[7],
        }
    );
}

async function dialog_confirm({ text = "การทำการลบข้อมูล", title = "คุณแน่ใจใช่ไหม?" } = {}) {
    try {
        const alert = await Swal.fire({
            title: title,
            text: text,
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#FF7E00",
            confirmButtonText: "ใช่ แน่ใจ!",
            cancelButtonText: "ไม่ กลับไปตรวจสอบ",
        });
        return !!(alert.value && alert.value === true);
    } catch (e) {
        console.log("error:", e);
        return false;
    }
}
const English = /^[A-Za-z0-9]*$/;

function debug_form(formData) {
    for (const pair of formData.entries()) {
        console.log(`${pair[0]}, ${pair[1]}`);
    }
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
