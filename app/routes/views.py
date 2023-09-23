import base64
from http.client import HTTPResponse
from io import BytesIO
import os
import random
import time
from time import sleep
from typing import Union
from unittest import result

from fastapi import APIRouter, Cookie, Depends, Request, Header, Response

from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    StreamingResponse,
)
import httpx
from pydantic import BaseModel

# from requests.auth import HTTPDigestAuth, HTTPBasicAuth
from PIL import Image

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func
from app.core.database import get_async_session
from app.core.auth import access_cookie_token, allowed_permissions, get_jwt_access, get_user_by_id

from ..stdio import *
from app.core import config
from app.core.models import Estamp_Device, GateWay, Lpr_Camera, Member, Member_Type, Parking_Lot, Lpr_Log, Service_Fees, System_User
from sqlalchemy import select

from app.core import models
from app.routes.websocket import WebSockets


DIR_PATH = config.DIR_PATH

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["Public"])


@router.get("/page_404")
async def page_404(url: str = ""):
    _now = time_now()
    print_error(f"page_404 : {url}")
    return templates.TemplateResponse(
        "404.html",
        {"request": {}, "now": _now, "app_title": config.APP_TITLE, "url": url},
    )


@router.get("/")
async def main_path(
    app_mode: str | None = Cookie(default="SYSTEM"),
    db: AsyncSession = Depends(get_async_session),
    user=Depends(access_cookie_token),
):
    _now = time_now()
    # for check_login user
    print("request from user", user)
    # Check login user
    if user:
        match app_mode:
            case "LPR_AUTO_GATE":
                return RedirectResponse(url="/gate_way_lpr")
            case "ESTAMP":
                return RedirectResponse(url="/estamp")
            case "SYSTEM":
                return RedirectResponse(url="/system_config")
            case _:
                return RedirectResponse(url="/home")
    else:
        return templates.TemplateResponse(
            "login.html",
            {"request": {}, "now": _now, "app_title": config.APP_TITLE},
        )


@router.get("/about")
async def about_path(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    _now = time_now()
    # for check_login user
    print("request from user", user)
    # Check login user
    return templates.TemplateResponse(
        "about.html",
        {"request": {}, "now": _now, "app_title": config.APP_TITLE},
    )


@router.get("/ping")
async def ping(request: Request):
    _now = time_now()
    _header = request.headers
    for k, v in _header.items():
        print(k, v)
    return f"Time process : {time_now() - _now}"


@router.get("/proxy")
async def proxy(
    request: Request,
    url: str = None,
):
    _now = time_now()
    if url:
        print(url)
        _index = url.rfind("@")
        if _index > 0:
            _url = f"http://{url[_index+1:]}"
            _temp = url[:_index]
            _temp = _temp.split("://")[1]
            _user, _pass = _temp.split(":")
            print_warning(_url)

            # response = requests.get(_url, auth=HTTPDigestAuth(str(_user), str(_pass)), timeout=5)
            try:
                auth = httpx.DigestAuth(_user, _pass)
                with httpx.Client(auth=auth) as client:
                    response = client.get(_url, timeout=3)
            except httpx.HTTPError as e:
                print_error(e)
                return None
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                # buf = BytesIO()
                # img = img.resize((240, 320), Image.Resampling.LANCZOS)
                # img.save(buf, format="JPEG")
                print("capture.. Successfully")
                # return img
                # _file_name = "buffer.jpg"
                # img.save(_file_name)
                # print(img)
                # return FileResponse(_file_name)
                buf = BytesIO(response.content)
                return StreamingResponse(buf, media_type="image/jpeg")

            return None
        else:
            try:
                with httpx.Client() as client:
                    response = client.get(url, timeout=3)
            except httpx.HTTPError as e:
                print_error(e)
                return None

            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                # buf = BytesIO()
                # img = img.resize((240, 320), Image.Resampling.LANCZOS)
                # img.save(buf, format="JPEG")
                print("image.. Successfully")
                # return img
                # _file_name = "buffer.jpg"
                # img.save(_file_name)
                # print(img)
                # return FileResponse(_file_name)
                buf = BytesIO(response.content)
                return StreamingResponse(buf, media_type="image/jpeg")
            else:
                print(response)
                return None
    return None


@router.get("/home")
async def router_home(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}
    sql = select(Parking_Lot)
    parking_lots = (await db.execute(sql)).all()
    return templates.TemplateResponse(
        "home.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
            "parking_lots": parking_lots,
        },
    )


@router.get("/estamp")
async def router_estamp(
    db: AsyncSession = Depends(get_async_session),
    user=Depends(access_cookie_token),
):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}
    sql = select(Estamp_Device)
    _Estamp_Devices = (await db.execute(sql)).all()
    estamp_list = []
    for e in _Estamp_Devices:
        e: Estamp_Device = e[0]
        system_user_ids = e.system_user_ids.split(",")
        if str(user["id"]) in system_user_ids:
            estamp_list.append(e.device_name)
    return templates.TemplateResponse(
        "estamp.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
            "estamp_list": estamp_list,
        },
    )


@router.get("/lpr_view")
async def router_lpr_view(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}

    # print(lpr_logs)
    return templates.TemplateResponse(
        "lpr.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/get_lpr_log/closeup_pic")
async def router_get_lpr_log_closeup_pic(
    id: int,
    db: AsyncSession = Depends(get_async_session),
    user=Depends(access_cookie_token),
):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    sql = select(Lpr_Log.closeup_pic).where(Lpr_Log.id == id)
    lpr_logs = (await db.execute(sql)).one_or_none()

    if lpr_logs:
        img64 = lpr_logs[0]
        return Response(content=base64.b64decode(img64), media_type="image/jpeg")
    return ""


@router.get("/station_config")
async def router_station_config(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    if not (await allowed_permissions(db, user, "station_config")):
        # return {"success": False, "msg": "not permission_allowed"}
        return templates.TemplateResponse(
            "403.html",
            {
                "request": {},
                "user": user,
            },
        )
    _now = time_now()
    # print(user)
    datas = {}
    return templates.TemplateResponse(
        "station_config.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/dashboard_document")
async def route_dashboard_gateway(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}
    return templates.TemplateResponse(
        "dashboard_document.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/dashboard_gateway")
async def route_dashboard_gateway(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}
    return templates.TemplateResponse(
        "dashboard_gateway.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/dashboard_service_fee")
async def route_dashboard_service_fee(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}
    return templates.TemplateResponse(
        "dashboard_service_fee.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/dashboard_gate_control_devices")
async def route_dashboard_gate_control_devices(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}
    return templates.TemplateResponse(
        "dashboard_gate_control_devices.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/dashboard_estamp_devices")
async def route_dashboard_gate_control_devices(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    sql = select(Service_Fees.id, Service_Fees.name)
    _Service_Fees = (await db.execute(sql)).all()
    sql = select(System_User.id, System_User.username)

    _System_User = (await db.execute(sql)).all()
    datas = {}
    print(_Service_Fees)
    return templates.TemplateResponse(
        "dashboard_estamp_devices.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
            "Service_Fees": _Service_Fees,
            "System_User": _System_User,
        },
    )


@router.get("/transection_report")
async def route_dashboard_transection_report(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    print(user)
    datas = {}
    return templates.TemplateResponse(
        "transection_report.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/member_manager")
async def route_member_manager(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    _sql = select(Member_Type).order_by(
        Member_Type.name,
    )
    member_types = (await db.execute(_sql)).all()
    print(member_types)
    datas = {}
    return templates.TemplateResponse(
        "member_manager.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "member_types": member_types,
            "now": _now,
        },
    )


@router.get("/log")
async def router_gate_way(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    # print(user)
    datas = {}
    return templates.TemplateResponse(
        "log.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/gate_way_lpr")
async def router_gate_way_lpr(db: AsyncSession = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    _now = time_now()
    # print(user)
    datas = {}
    return templates.TemplateResponse(
        "gate_way_lpr.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/system_config")
async def router_system_config(db: Session = Depends(get_async_session), user=Depends(access_cookie_token)):
    if not user:
        return RedirectResponse(url="/")
    if not (await allowed_permissions(db, user, "system_config")):
        # return {"success": False, "msg": "not permission_allowed"}
        return templates.TemplateResponse(
            "403.html",
            {
                "request": {},
                "user": user,
            },
        )
    _now = time_now()
    print(user)
    datas = {}

    return templates.TemplateResponse(
        "system_config.html",
        {
            "request": {},
            "user": user,
            "datas": datas,
            "now": _now,
        },
    )


@router.get("/api/publish")
async def router_publish(request: Request, subscribe: str = "A001", data: str = "Subscribe/subscription"):
    _now = time_now()
    print_warning(data)
    success = await WebSockets.send_notification(subscribe, data)
    return f"Successfully : {success}"


@router.get("/cmd")
async def router_test_cmd(response: Response, open_gate: str):
    # response.headers["allow_origins"] = "*"
    # response.headers["allow_credentials"] = "*"
    # response.headers["allow_methods"] = "*"
    # response.headers["allow_headers"] = "*"

    _now = time_now()
    print_warning(open_gate)

    return f"Successfully : {open_gate}"


@router.get("/service-worker.js")
async def router_pwa_sw():
    return FileResponse("static/common/service-worker.js")


@router.get("/qa/mcardsea.cgi")
async def mcardsea(
    response: Response,
    cardid: str,
    mjihao: str,
    cjihao: str,
    status: str,
    time: str,
):
    print(cardid)

    # sleep(1)
    o = random.randint(0, 1)
    success = {
        "data": [{"cardid": cardid, "cjihao": 1, "mjihao": 1, "status": o, "time": time, "output": o}],
        "code": 1,
        "message": cardid,
    }
    print_success(success)
    return success
