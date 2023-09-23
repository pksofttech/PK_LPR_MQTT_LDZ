import os
import re
import time
from typing import Union
from unittest import result

from fastapi import APIRouter, Depends, File, Form, Request, Header, UploadFile

from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, func, or_, update
from app.core.database import get_async_session
from app.core.auth import access_cookie_token, allowed_permissions, get_jwt_access, get_user, get_user_by_id
from app.core.utility import get_password_hash, verify_password
from app.routes.websocket import WebSockets

from ..stdio import *
from app.core import config

from sqlalchemy import select
from fastapi import status, HTTPException
from PIL import Image
from io import BytesIO
from app.module.transection_proseecss import check_in_get, check_in_post, check_out_get, check_out_post

# from datetime import datetime, timedelta

from app.core.models import (
    Account_Record,
    App_Configurations,
    GateWay,
    Log,
    Log_Transaction,
    Member,
    Member_Type,
    Member_User,
    Member_User_Permission,
    Parking_Lot,
    Permission_Role,
    Service_Fees,
    Service_Fees_Format,
    System_User,
    Transaction_Record,
)


def check_permission_str(permission_allow):
    _new = time_now(0)
    permission_allow_list = permission_allow.split(",")
    WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for l in permission_allow_list:
        k, v = l.split("@")
        d, t = v.split("(")
        t = t[:-1]
        d0, d1 = d.split("-")
        t0, t1 = t.split("-")

        d = _new.weekday()
        d0 = WEEKDAYS.index(d0)
        d1 = WEEKDAYS.index(d1)
        t = _new.strftime("%H:%M")

        print(d0, d, d1)
        print(t0, t, t1)
        if d0 <= d <= d1:
            if t0 <= t <= t1:
                return True

    return False


router_api = APIRouter(prefix="/api/function", tags=["API_Function"])

# ? *NOTE - Check_In *****


@router_api.get("/check_in")
async def path_check_in_get(
    card_id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    return await check_in_get(
        db=db,
        card_id=card_id,
    )


@router_api.post("/check_in")
async def path_check_in_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    card_id: str = Form(...),
    license: str = Form(default=None),
    time: str = Form(...),
    service_fees_id: int = Form(...),
    image_upload_01: UploadFile = File(None),
    image_upload_02: UploadFile = File(None),
    gateway_id: int = Form(...),
    remark: str = Form(default=None),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    if image_upload_01:
        try:
            image_content = await image_upload_01.read()
            image_upload_01 = Image.open(BytesIO(image_content))
        except Exception as e:
            print_error(e)
            image_upload_01 = None

    if image_upload_02:
        try:
            image_content = await image_upload_02.read()
            image_upload_02 = Image.open(BytesIO(image_content))
        except Exception as e:
            print_error(e)
            image_upload_02 = None

    result = await check_in_post(
        db=db,
        user=user,
        card_id=card_id,
        time=time,
        gateway_id=gateway_id,
        service_fees_id=service_fees_id,
        image_upload_01=image_upload_01,
        image_upload_02=image_upload_02,
        license=license,
        remark=remark,
    )
    return result


@router_api.get("/check_out")
async def path_check_out_get(
    card_id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    return await check_out_get(
        db=db,
        card_id=card_id,
    )


@router_api.post("/check_out")
async def path_check_out_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    transaction_records_id: str = Form(...),
    amount: int = Form(...),
    pay: int = Form(...),
    turn_amount: int = Form(...),
    gateway_id: int = Form(...),
    card_id: str = Form(...),
    license: str = Form(""),
    image_upload_01: UploadFile = File(None),
    image_upload_02: UploadFile = File(None),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    if image_upload_01:
        try:
            image_content = await image_upload_01.read()
            image_upload_01 = Image.open(BytesIO(image_content))
        except Exception as e:
            print_error(e)
            image_upload_01 = None

    if image_upload_02:
        try:
            image_content = await image_upload_02.read()
            image_upload_02 = Image.open(BytesIO(image_content))
        except Exception as e:
            print_error(e)
            image_upload_02 = None

    sql = select(Transaction_Record).where(Transaction_Record.id == transaction_records_id)
    t = (await db.execute(sql)).one_or_none()
    # ! For Testing purposes
    # return {"success": False, "data": t, "msg": f"Test"}
    result = await check_out_post(
        db=db,
        user=user,
        transaction_records_id=transaction_records_id,
        amount=amount,
        pay=pay,
        turn_amount=turn_amount,
        gateway_id=gateway_id,
        card_id=card_id,
        license=license,
        image_upload_01=image_upload_01,
        image_upload_02=image_upload_02,
    )
    return result


# ? *NOTE - Gateway Info


@router_api.get("/gateway_list/")
async def path_gateway_list_get(
    id: str = None,
    parking_id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = select(GateWay, Parking_Lot, System_User)
    if id:
        print(f"gateway_list : with gateway_id : {id}")
        _sql = _sql.where(GateWay.id == id)

    if parking_id:
        print(f"gateway_list : with parking_id : {parking_id}")
        _sql = _sql.where(GateWay.parking_id == parking_id)

    _sql = _sql.join(Parking_Lot, Parking_Lot.id == GateWay.parking_id).join(System_User, System_User.id == GateWay.create_id)
    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}

    else:
        return {"success": False, "msg": f"Gateway is not available"}


@router_api.post("/gateway")
async def path_gateway_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(None),
    name: str = Form(...),
    parking_id: int = Form(...),
    type: str = Form(...),
    status: str = Form(...),
    remark: str = Form(""),
    ip_cameras: str = Form(""),
    image_upload: UploadFile = File(None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    print(f"GateWay ID: {id}")
    try:
        if id:
            _sql = select(GateWay).where(GateWay.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                _gateway: GateWay = _row[0]
                _gateway.name = name
                _gateway.parking_id = parking_id
                _gateway.type = type
                _gateway.status = status
                _gateway.date_created = _now
                _gateway.create_id = user.id
                _gateway.remark = remark
                _gateway.ip_cameras = ip_cameras

                await db.commit()
                await db.refresh(_gateway)
                print(_gateway)
            else:
                return {"success": False, "msg": f"GateWay is not available"}

        else:
            _sql = select(GateWay).where(GateWay.name == name)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": f"GateWay is duplicated"}
            _gateway = GateWay(
                name=name,
                parking_id=parking_id,
                type=type,
                status=status,
                date_created=_now,
                create_id=user.id,
                remark=remark,
                ip_cameras=ip_cameras,
            )
            db.add(_gateway)
            await db.commit()
            await db.refresh(_gateway)
        if image_upload:
            try:
                image_content = await image_upload.read()
                image_upload = Image.open(BytesIO(image_content))

                if image_upload.format == "PNG":
                    image_upload = image_upload.convert("RGB")
                _path = f"/static/data_base/image/gateway/{_gateway.id}.jpg"
                image_upload.save(f".{_path}")
                time_stamp = int(time_now().timestamp())
                _gateway.images_path = _path + f"?time_stamp={time_stamp}"
                await db.commit()

            except Exception as e:
                print_error(e)

        return {"success": True, "data": _gateway}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/gateway")
async def path_gateway_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(GateWay).where(GateWay.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _gateway: GateWay = _row[0]
            print(_gateway)
            await db.delete(_gateway)
            await db.commit()
            return {"success": True, "msg": f"Gateway is deleted successfully"}

        else:
            return {"success": False, "msg": f"Gateway is not available"}

    except Exception as e:
        err = str(e).lower()
        print(e)
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


# ? *NOTE - Parking Lot Info


@router_api.get("/parking_lot_list")
async def path_parking_lot_list_get(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = select(Parking_Lot).order_by(Parking_Lot.id)
    _row = (await db.execute(_sql)).all()
    return {"success": True, "data": _row}


@router_api.post("/parking_lot")
async def path_parking_lot_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    name: str = Form(...),
    detail: str = Form(""),
    limit: int = Form(...),
    value: int = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id == 0:
            _sql = select(Parking_Lot).where(Parking_Lot.name == name)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": f"Parking_Lot is duplicated"}
            _parking_lot = Parking_Lot(
                name=name,
                detail=detail,
                limit=limit,
                value=value,
                create_id=user.id,
            )
            db.add(_parking_lot)
            await db.commit()
            await db.refresh(_parking_lot)
            return {"success": True, "data": _parking_lot}

        _sql = select(Parking_Lot).where(Parking_Lot.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _parking_lot: Parking_Lot = _row[0]
            _parking_lot.name = name
            _parking_lot.detail = detail
            _parking_lot.limit = limit
            _parking_lot.value = value
            await db.commit()
            await db.refresh(_parking_lot)
            print(_parking_lot)
            return {"success": True, "data": _parking_lot}
        return {"success": False, "msg": f"Parking_Lot is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/parking_lot")
async def path_parking_lot_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(Parking_Lot).where(Parking_Lot.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _parking_lot: Parking_Lot = _row[0]
            print(_parking_lot)
            await db.delete(_parking_lot)
            await db.commit()
            return {"success": True, "msg": f"Parking_Lot is deleted successfully"}

        else:
            return {"success": False, "msg": f"Parking_Lot is not available"}

    except Exception as e:
        err = str(e).lower()
        print(e)
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


# ? *NOTE - App_Config Info


@router_api.get("/app_config_owner")
async def path_app_config_owner_get(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = select(App_Configurations)
    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}
    else:
        return {"success": False, "msg": f"App_Configurations is not available"}


@router_api.post("/app_config_owner")
async def path_app_config_owner_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    app_configurations_name: str = Form(...),
    app_configurations_address: str = Form(...),
    app_configurations_phone: str = Form(...),
    app_configurations_vat_no: str = Form(...),
    app_configurations_remark: str = Form(...),
    image_upload: UploadFile = File(None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(App_Configurations)
        rows = (await db.execute(_sql)).all()
        if app_configurations_name:
            _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_name")
            _row = (await db.execute(_sql)).one_or_none()
            _a: App_Configurations = _row[0]
            _a.value = app_configurations_name
            await db.commit()
            await db.refresh(_a)

        if app_configurations_address:
            _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_address")
            _row = (await db.execute(_sql)).one_or_none()
            _a: App_Configurations = _row[0]
            _a.value = app_configurations_address
            await db.commit()
            await db.refresh(_a)

        if app_configurations_phone:
            _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_phone")
            _row = (await db.execute(_sql)).one_or_none()
            _a: App_Configurations = _row[0]
            _a.value = app_configurations_phone
            await db.commit()
            await db.refresh(_a)

        if app_configurations_vat_no:
            _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_vat_no")
            _row = (await db.execute(_sql)).one_or_none()
            _a: App_Configurations = _row[0]
            _a.value = app_configurations_vat_no
            await db.commit()
            await db.refresh(_a)

        if app_configurations_remark:
            _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_remark")
            _row = (await db.execute(_sql)).one_or_none()
            _a: App_Configurations = _row[0]
            _a.value = app_configurations_remark
            await db.commit()
            await db.refresh(_a)

        if image_upload:
            try:
                image_content = await image_upload.read()
                image_upload = Image.open(BytesIO(image_content))

                if image_upload.format == "PNG":
                    image_upload = image_upload.convert("RGB")
                _path = f"/static/data_base/image/app_configurations/app_configurations_image.jpg"
                image_upload.save(f".{_path}")
                time_stamp = int(time_now().timestamp())
                _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_image")
                _row = (await db.execute(_sql)).one_or_none()
                _a: App_Configurations = _row[0]
                _a.value = _path + f"?time_stamp={time_stamp}"

                await db.commit()

            except Exception as e:
                print_error(e)
                return {"success": True, "msg": str(e)}

        return {"success": True, "msg": f"App_Configurations is updated successfully"}
    except Exception as e:
        print_error(e)
        return {"success": False, "msg": str(e)}
