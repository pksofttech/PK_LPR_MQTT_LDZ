import base64
from http.client import HTTPResponse
from io import BytesIO
import json
import os
import pprint
import time
from typing import Union
from unittest import result
import httpx
from fastapi import APIRouter, Depends, Form, Request, Header

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
from sqlmodel import delete, func
from app.core.database import get_async_session
from app.core.auth import access_cookie_token, allowed_permissions, get_jwt_access, get_user_by_id
from app.core.utility import save_image_file
from app.module.transection_proseecss import check_in_get, check_in_post, check_out_get, check_out_post
from ..stdio import *
from app.core import config
from app.core.models import (
    GateWay,
    Log_Transaction,
    Lpr_Camera,
    Member,
    Member_Type,
    Member_User,
    Parking_Lot,
    Lpr_Log,
    Service_Fees,
    System_User,
    Transaction_Record,
)
from sqlalchemy import select

from app.core import models
from app.routes.websocket import WebSockets

from app.core.mqtt import fast_mqtt, PUBLISH, lzd_vender_send

DIR_PATH = config.DIR_PATH

templates = Jinja2Templates(directory="templates")
router_api = APIRouter(tags=["LPR"], prefix="/lpr")


def plate_num_check(plate_num) -> bool:
    return True


from PIL import Image, ImageFont, ImageOps, ImageDraw


async def generate_plate(plate_num):
    def draw_text(img, text, py, font, align="center"):
        text = str(text)
        _w, _h = img.textsize(text, font=font)
        if align == "left":
            img.text((0, py), text, font=font, fill="white")
        elif align == "right":
            img.text((slip_size_W - _w, py), text, font=font, fill="white")
        else:
            img.text((int((slip_size_W - _w) / 2), py), text, font=font, fill="white")

        return _h

    offset_py = 0
    slip_size_W = 400
    slip_size_max_h = 400
    print_success("Creating image logo...")
    logo_img = Image.open("./static/image/system.png")  # open in a PIL Image object
    logo_size = int(slip_size_W * 0.5)
    logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    logo_print = Image.new("RGB", logo_img.size, (255, 255, 255))
    logo_print.paste(logo_img, mask=logo_img.split()[3])

    font_title = ImageFont.truetype("./static/font/Kodchasan-Regular.ttf", 48)
    slip_image = Image.new(mode="RGB", size=(slip_size_W, slip_size_max_h), color=(0, 0, 0))
    _w, _h = logo_img.size
    slip_image.paste(logo_img, (int((slip_size_W - _w) / 2), offset_py))
    slip_draw = ImageDraw.Draw(slip_image)
    offset_py += _h
    _h = draw_text(slip_draw, plate_num, offset_py, font_title, "center")
    offset_py += 60
    slip_size = (0, 0, slip_size_W, offset_py)
    slip_ing_file = slip_image.crop(slip_size)
    return slip_ing_file


"""
FormData([('type', 'online'), ('mode', '5'), ('plate_num', '2à¸\x81à¸¨7118'), ('car_logo', 'unknown'), ('car_sublogo', 'unknown'), ('plate_val', 'true'), ('confidence', '27'), ('plate_color', 'unknown'), ('car_color', 'gray'), ('vehicle_type', 'car'), ('start_time', '1676197516'), ('park_id', '0'), ('cam_id', '180300121847'), ('cam_ip', '192.168.8.205'), ('vdc_type', 'in'), ('is_whitelist', 'false'), ('triger_type', 'video'), ('picture', ''), 
('closeup_pic', '_9j_4AAQSkZJRgABAQAAAQABAAD_2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL_2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL_wAARCAAgAEADASIAAhEBAxEB_8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL_8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4-Tl5ufo6erx8vP09fb3-Pn6_8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL_8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3-Pn6_9oADAMBAAIRAxEAPwDat9T1a5iWSLWr8B8hFAQk-h-71NWA_idhhb_WHzyCI4h_NKreGA8moWagciNjgjoTG1S2bTaZLr17b30l1HZafIskuOGuFbIK_Qhh3_WkmD0LKr4nON914hyf7v2Vf5wmmk60ky27T6xJL1KzXcStj3C7Kz47GXw5I32C6uHlfw1PcTPLIz77gFMP8xPO7ccf0o8MwTW2uQyTW6W_2nSpJgASxcM0W1mJJyxGSfTJFGvQhuxZktLyaf7Obu4Fzz-5fXJUY-vypNn9Krr4dunnkG-LeAN4k1K4lC59QzMOx96044LSbxjPNHAIzp9ujyFcDzppCxyfpk_rS6NER4r1-F2ZoGe1WPcexVt388fhRqO66GEPCVpBbSXTS6HBFC-x3Nlvw2QNoyOTkgY65qWZG0ye1Vb21uobiNJYbi1gESncSBwCfaoVCL4I-aZYIxrE0puXbiMCRuueORxzjqe9MuWQWuiu5_dxwq5Zed6hid4-uM_jTcmJXuaHhPIk0472WSWz3s2OQTGxyK0bHw_ZaZaXNtDcXrW9wpWRZ7nKjOM46AHgDPtWd4Pf7WNPvbRTNGsCqAoBGQpVlP0B5x7VsajfJCognKIQwc7QB07ZLH1rNySehcrvYmls7eVvNkMJ2QG3y0w-WM8kHn_OTVYXui20iB9W0qGSOIRKGvUyF44-9z0FYs1_pKvmWVUC_MpW8jTHGOpNUj4j8PLbp5VwhSN9wBvVzk4yemf4f5-pzaMnc6kXulRyySJfWhkm2lyhLFsA45APqfzpPt-no7E3MSyMQCAPmOBxx16HvXKReMvDttIrm9s8qCVDzzPj_vk4J96rz-O_DLuZTdQxuAAfKhlJI-pNAcsjuraaC5jlW0G6NH2yIYdoJPOSvfOe9c54w8691qKxjRpZZbJYFAIU7nDcAkgDr6j8K59PH-ghmKT30gYjd5NqMnjA6mqWp-KDq0c32Cwu45WUrC8wUCPIPPyknOTRZ3Kimnc__9k.')])
"""
#  IN 180300121847
# OUT 180300121754


HOST_NAME = os.uname()[1]


@router_api.post("/")
async def post_lpr_log(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    on_test=Form(None),
    type: str = Form("online"),
    plate_num: str = Form("2à¸\x81à¸¨7118"),
    cam_ip: str = Form("192.168.8.205"),
    start_time: str = Form("1676197516"),
    closeup_pic: str = Form(
        "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"
    ),
    picture: str = Form(
        "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"
    ),
    cam_id: str = Form(...),
):
    if cam_id == "in":
        cam_id = "180300121847"
    if cam_id == "out":
        cam_id = "180300121754"
    print(type, cam_ip, cam_id, start_time)
    _now = time_now()
    _GateWay: GateWay = None
    _Lpr_Camera = None
    _sql = select(Lpr_Camera, GateWay).where(Lpr_Camera.device_id == cam_id).outerjoin(GateWay, (GateWay.id == Lpr_Camera.gateway_id))
    _row = (await db.execute(_sql)).one_or_none()

    if _row:
        _Lpr_Camera: Lpr_Camera = _row[0]
        _GateWay: GateWay = _row[1]
        print(_Lpr_Camera)

    if type == "heartbeat":
        pass
        # print_success("heartbeat")
    elif type == "online":
        try:
            plate_num = plate_num.encode("Latin-1").decode("utf-8")
        except:
            plate_num = plate_num

        print_success(f"online snapshot {plate_num} : IP:{cam_ip} >> ID {cam_id}")
        if not closeup_pic:
            print_warning("LPR is not plate_num")
            return {
                "error_num": 0,
                "error_str": "No plate_num",
            }
        image_data = closeup_pic
        image_data = image_data.replace(".", "=")
        image_data = image_data.replace("_", "/")
        image_data = image_data.replace("-", "+")
        closeup_pic_img = Image.open(BytesIO(base64.b64decode(image_data)))

        picture_img = None
        if picture:
            image_data = picture
            image_data = image_data.replace(".", "=")
            image_data = image_data.replace("_", "/")
            image_data = image_data.replace("-", "+")
            picture_img = Image.open(BytesIO(base64.b64decode(image_data)))
            if picture_img.format == "PNG":
                picture_img = picture_img.convert("RGB")

        if on_test:
            closeup_pic_img = await generate_plate(plate_num)
            picture_img = closeup_pic_img

        _Lpr_Log = Lpr_Log(
            create_id=1,
            type=type,
            plate_num=plate_num,
            cam_ip=cam_ip,
            start_time=start_time,
            date_time=_now,
        )

        db.add(_Lpr_Log)
        await db.commit()
        await db.refresh(_Lpr_Log)
        images_path_list = []
        file_path = f"./static/data_base/image/Lpr_Log/{_Lpr_Log.id//1000}"
        file_name = f"{_Lpr_Log.id}_01"
        img_success = save_image_file(closeup_pic_img, file_path, file_name)
        # print(img_success)
        if img_success:
            images_path_list.append(img_success[1:])

        # **NOTE - Proseecss Transaction **************************************************************
        lpr_msg_type = "CAR MQTT"
        if _GateWay:
            _Log_Transaction = Log_Transaction(
                card_id=plate_num,
                date_time=_now,
                license=plate_num,
                create_id=_Lpr_Camera.system_user_id,
                gateway_id=_GateWay.id,
                images_path=_Lpr_Log.images_path,
            )

            if _GateWay.type == "IN":
                print("Proseecss Transaction Lpr Gateway IN Transaction")

            elif _GateWay.type == "OUT":
                print("Proseecss Transaction Lpr Gateway OUT Transaction")
                pass

        images_path = ""
        if images_path_list:
            images_path = ",".join(images_path_list)
            _Lpr_Log.images_path = images_path

        await db.commit()
        await db.refresh(_Lpr_Log)
        # print(_Lpr_Log)

        lpr_msg = {}
        lpr_msg["lpr_msg_type"] = lpr_msg_type
        lpr_msg["type"] = _Lpr_Log.status
        lpr_msg["status"] = _Lpr_Log.status
        lpr_msg["tag"] = _Lpr_Log.tag

        lpr_msg["transaction_record_id"] = _Lpr_Log.transaction_record_id

        lpr_msg["device_id"] = cam_id
        lpr_msg["device_ip"] = cam_ip
        lpr_msg["plate_num"] = plate_num
        _date_time_str = str(_Lpr_Log.date_time).split(".")[0]
        lpr_msg["date_time"] = _date_time_str
        lpr_msg["date"] = _date_time_str.split(" ")[0]
        lpr_msg["time"] = _date_time_str.split(" ")[1]
        lpr_msg["images_path"] = _Lpr_Log.images_path
        lpr_msg["images_path_01"] = _Lpr_Log.images_path
        lpr_msg["images_path_02"] = _Lpr_Log.images_path

        if _Lpr_Camera:
            lpr_msg["device_name"] = _Lpr_Camera.device_name

        if _GateWay:
            lpr_msg["gate_name"] = _GateWay.name

        await lzd_vender_send(plate_num, _GateWay.type)

        ws_json = {"func": "lpr_event", "params": lpr_msg}
        # print(ws_json)
        await WebSockets.broadcast(ws_json, sendMode="json")
        # return {
        #     "error_num": 0,
        #     "error_str": "noerror",
        #     "gpio_data": [{"ionum": "io1", "action": "on"}],
        # }

        _ret = {
            "error_num": 0,
            "error_str": "noerror",
            "rs485_data": [
                {"encodetype": "hex2string", "data": "AA55016400260009010002004343434343C5F0AF"},
                {"encodetype": "hex2string", "data": "AA551F6400220009D4C1423132333435012AA6AF"},
                # {"encodetype": "base64", "data": "qlUBZAAmAAkBAAIAQ0NDQ0PF8K8="},
            ],
            "gpio_data": [{"ionum": "io1", "action": "on"}, {"ionum": "io2", "action": "on"}],
        }

        return _ret
    else:
        print_success(f"Type : {type}")
        data_body = await request.form()
        print(data_body)
        for k, v in data_body.items():
            pass
            print(k)

    return {"error_num": 0, "error_str": "noerror"}


@router_api.get("/")
async def get_lpr_log(
    id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    sql = (
        select(Lpr_Log, Lpr_Camera, GateWay)
        .limit(10)
        .order_by(Lpr_Log.id.desc())
        .outerjoin(Lpr_Camera, (Lpr_Camera.id == Lpr_Log.lpr_camera_id))
        .outerjoin(GateWay, (GateWay.id == Lpr_Camera.gateway_id))
    )
    lpr_logs = (await db.execute(sql)).all()

    return {"success": True, "data": lpr_logs}


router_api_devices_lpr = APIRouter(tags=["LPR"], prefix="/api/devices/lpr_camera")


@router_api_devices_lpr.get("/")
async def path_devices_lpr_get(
    id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = (
        select(Lpr_Camera, GateWay, System_User, Service_Fees)
        .outerjoin(GateWay, (GateWay.id == Lpr_Camera.gateway_id))
        .outerjoin(System_User, (System_User.id == Lpr_Camera.system_user_id))
        .outerjoin(Service_Fees, (Service_Fees.id == Lpr_Camera.service_fees_id))
    )
    if id:
        _sql = _sql.where(Lpr_Camera.id == id)
    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}
    else:
        return {"success": False, "msg": f"Lpr_Camera is not available"}


@router_api_devices_lpr.post("/")
async def path_devices_lpr_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    device_name: str = Form(...),
    device_id: str = Form(...),
    device_ip: str = Form(...),
    type: str = Form(...),
    direction: str = Form(...),
    mode: str = Form(...),
    device_model: str = Form(...),
    remark: str = Form(None),
    device_gate_name: str = Form(...),
    device_system_user: str = Form(...),
    device_services_fee: str = Form(None),
    device_send_data_path: str = Form(None),
    device_send_heartbeat_path: str = Form(None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id:
            _sql = select(Lpr_Camera).where(Lpr_Camera.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                _Lpr_Camera: Lpr_Camera = _row[0]

                _Lpr_Camera.device_name = device_name
                _Lpr_Camera.device_id = device_id
                _Lpr_Camera.device_ip = device_ip
                _Lpr_Camera.type = type
                _Lpr_Camera.direction = direction
                _Lpr_Camera.device_model = device_model
                _Lpr_Camera.mode = mode
                _Lpr_Camera.remark = remark
                _Lpr_Camera.device_send_data_path = device_send_data_path
                _Lpr_Camera.device_send_heartbeat_path = device_send_heartbeat_path

                _sql = select(GateWay.id).where(GateWay.name == device_gate_name)
                _row = (await db.execute(_sql)).one_or_none()
                if not _row:
                    return {"success": False, "msg": "ไม่พบข้อมูล ช่องทาง"}
                _Lpr_Camera.gateway_id = _row[0]

                _sql = select(System_User.id).where(System_User.name == device_system_user)
                _row = (await db.execute(_sql)).one_or_none()
                if not _row:
                    return {"success": False, "msg": "ไม่พบข้อมูล System User"}
                _Lpr_Camera.system_user_id = _row[0]

                Service_Fees_id = None
                _sql = select(Service_Fees.id).where(Service_Fees.name == device_services_fee)
                _row = (await db.execute(_sql)).one_or_none()
                if _row:
                    Service_Fees_id = _row[0]
                _Lpr_Camera.service_fees_id = Service_Fees_id

                await db.commit()
                await db.refresh(_Lpr_Camera)

                return {"success": True, "data": _Lpr_Camera}
            return {"success": False, "msg": "ไม่พบข้อมูล"}
        else:
            _Lpr_Camera = Lpr_Camera()
            _Lpr_Camera.create_id = user.id
            _Lpr_Camera.device_name = device_name
            _Lpr_Camera.device_id = device_id
            _Lpr_Camera.device_ip = device_ip
            _Lpr_Camera.type = type
            _Lpr_Camera.direction = direction
            _Lpr_Camera.device_model = device_model
            _Lpr_Camera.mode = mode
            _Lpr_Camera.remark = remark
            _Lpr_Camera.device_send_data_path = device_send_data_path
            _Lpr_Camera.device_send_heartbeat_path = device_send_heartbeat_path

            _sql = select(GateWay.id).where(GateWay.name == device_gate_name)
            _row = (await db.execute(_sql)).one_or_none()
            if not _row:
                return {"success": False, "msg": "ไม่พบข้อมูล ช่องทาง"}
            _Lpr_Camera.gateway_id = _row[0]

            _sql = select(System_User.id).where(System_User.name == device_system_user)
            _row = (await db.execute(_sql)).one_or_none()
            if not _row:
                return {"success": False, "msg": "ไม่พบข้อมูล System User"}
            _Lpr_Camera.system_user_id = _row[0]

            Service_Fees_id = None
            _sql = select(Service_Fees.id).where(Service_Fees.name == device_services_fee)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                Service_Fees_id = _row[0]
            _Lpr_Camera.service_fees_id = Service_Fees_id

            db.add(_Lpr_Camera)
            await db.commit()
            await db.refresh(_Lpr_Camera)
            return {"success": True, "data": _Lpr_Camera}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api_devices_lpr.delete("/")
async def path_devices_lpr_del(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: str = (None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = delete(Lpr_Camera).where(Lpr_Camera.id == id)

        result = await db.execute(_sql)
        await db.commit()
        print_success(f"delete rows is successful :{result.rowcount}")
        return {"success": True, "data": result.rowcount}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}
