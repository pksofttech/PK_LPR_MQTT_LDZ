from http.client import HTTPResponse
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
from sqlmodel import delete, func, or_
from app.core.database import get_async_session
from app.core.auth import access_cookie_token, allowed_permissions, get_jwt_access, get_user, get_user_by_id
from app.core.utility import get_password_hash, verify_password
from app.module.account import calculate_services_fee

from ..stdio import *
from app.core import config
from app.core.database import System_User
from sqlalchemy import select
from fastapi import status, HTTPException
from PIL import Image
from io import BytesIO

from app.core.models import GateWay, Log, Parking_Lot, Service_Fees, System_User, Service_Fees_Format


def validate_condition_type(condition_type, condition: str) -> bool:
    def validate_time_range(_condition):
        print(f"validate_time_range :{_condition}")
        if re.match("^([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]-([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", _condition):
            _c_t0, _c_t1 = condition.split("-")
            if _c_t0 >= _c_t1:
                return False
            return True
        return False

    match condition_type:
        case "PARKED_RANGE":
            return validate_time_range(condition)
        case "IN_RANGE":
            return validate_time_range(condition)
        case "OUT_RANGE":
            return validate_time_range(condition)
        case _:
            return False


router_api_data_service_fees_format = APIRouter(prefix="/api/data/service_fees_format", tags=["API_DATABASE_Service_Fees_Format"])
router_api_data_service_fees = APIRouter(prefix="/api/service_fees", tags=["API_DATABASE_Service_Fees"])


@router_api_data_service_fees_format.get("/")
async def path_service_fees_format_get(
    id: int = None,
    name: str = None,
    service_fees_id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    _sql = select(Service_Fees_Format)
    if id:
        _sql = _sql.where(Service_Fees_Format.id == id)
    if name:
        _sql = _sql.where(Service_Fees_Format.name == name)

    if service_fees_id:
        _sql = _sql.where(Service_Fees_Format.service_fees_id == service_fees_id).order_by(Service_Fees_Format.priority)

    _row = (await db.execute(_sql)).all()
    # print(_row)
    return {"success": True, "data": _row}


@router_api_data_service_fees_format.post("/")
async def path_service_fees_format_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    name: str = Form(...),
    condition_type: str = Form(...),
    priority: int = Form(...),
    condition: str = Form(...),
    status: str = Form(...),
    service_fees_id: int = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    if priority == 0:
        priority = 1
    try:
        if not validate_condition_type(condition_type, condition):
            return {"success": False, "msg": "การตั้งค่าเงื่อนไขต้องอยู่ในรูปแบบเวลา(XX:XX-XX:XX)"}
        if id:
            _sql = select(Service_Fees_Format).where(Service_Fees_Format.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if not _row:
                return {"success": False, "msg": "ไม่พบรายการข้อมูล"}
            _Service_Fees_Format: Service_Fees_Format = _row[0]
            if _Service_Fees_Format.primary:
                return {"success": False, "msg": "ข้อมูลนี้เป็นรายการ Default ไม่สามารถดำเนินการได้"}

            _Service_Fees_Format.name = name
            _Service_Fees_Format.condition_type = condition_type
            _Service_Fees_Format.priority = priority
            _Service_Fees_Format.condition = condition
            _Service_Fees_Format.status = status

        else:
            _sql = select(Service_Fees_Format).where(
                Service_Fees_Format.name == name,
                Service_Fees_Format.service_fees_id == service_fees_id,
            )
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
            _sql = select(Service_Fees_Format).where(
                Service_Fees_Format.service_fees_id == service_fees_id,
            )
            _row = (await db.execute(_sql)).all()

            _Service_Fees_Format = Service_Fees_Format(
                primary=0,
                name=name,
                condition_type=condition_type,
                condition=condition,
                status=status,
                service_fees_id=service_fees_id,
            )
            db.add(_Service_Fees_Format)

        await db.commit()
        await db.refresh(_Service_Fees_Format)
        return {"success": True, "data": (_Service_Fees_Format,)}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api_data_service_fees_format.get("/calculate_list_test")
async def path_service_fees_format_calculate_list_test(
    id: int,
    parked: str,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id:
            _sql = (
                select(Service_Fees_Format, Service_Fees)
                .where(Service_Fees_Format.id == id)
                .outerjoin(
                    Service_Fees,
                    (Service_Fees_Format.service_fees_id == Service_Fees.id),
                )
            )
            _row = (await db.execute(_sql)).one_or_none()
            if not _row:
                return {"success": False, "msg": "ไม่พบรายการข้อมูล"}

            _Service_Fees_Format: Service_Fees_Format = _row[0]
            _Service_Fees: Service_Fees = _row[1]
            _round = _Service_Fees.round

            calculate_list_str = _Service_Fees_Format.calculate_list
            h, m = parked.split(":")
            parked_time = timedelta(hours=int(h), minutes=int(m))
            _, amount, log = calculate_services_fee(
                calculate_list=calculate_list_str,
                in_time=_now,
                out_time=_now + parked_time,
                round=_round,
            )

            if amount is None:
                return {"success": False, "msg": "ผิดพลาดไม่สามารถคิคค่าบริการได้"}
            return {"success": True, "msg": log}
        return {"success": False, "msg": "ไม่พบรายการข้อมูล"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api_data_service_fees_format.post("/calculate_list")
async def path_service_fees_format_calculate_list_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    key: str = Form(...),
    value: str = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id:
            if not (re.match("^[0-9][0-9]:[0-5][0-9]$", key)):
                return {"success": False, "msg": "รูปแบบข้อมูลไม่ถูกต้อง  formatted(xx:xx)"}

            _sql = select(Service_Fees_Format).where(Service_Fees_Format.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if not _row:
                return {"success": False, "msg": "ไม่พบรายการข้อมูล"}
            _Service_Fees_Format: Service_Fees_Format = _row[0]
            calculate_list_str = _Service_Fees_Format.calculate_list
            calculate_list = []
            if not calculate_list_str:
                calculate_list.append(f"{key}={value}")
                _Service_Fees_Format.calculate_list = ",".join(calculate_list)
            else:
                calculate_list = calculate_list_str.split(",")
                success = False
                for index, _c in enumerate(calculate_list):
                    k, v = _c.split("=")
                    if key == k:
                        calculate_list[index] = f"{key}={value}"
                        success = True
                        break
                    if k > key:
                        calculate_list.insert(index, f"{key}={value}")
                        success = True
                        break
                if not success:
                    calculate_list.append(f"{key}={value}")
                _Service_Fees_Format.calculate_list = ",".join(calculate_list)
            await db.commit()
            await db.refresh(_Service_Fees_Format)
            print(_Service_Fees_Format.calculate_list)

            return {"success": True, "data": (_Service_Fees_Format,)}
        return {"success": False, "msg": "ไม่พบรายการข้อมูล"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api_data_service_fees_format.delete("/calculate_list")
async def path_service_fees_format_calculate_list_delete(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    key: str = Form(...),
    value: str = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id:
            _sql = select(Service_Fees_Format).where(Service_Fees_Format.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if not _row:
                return {"success": False, "msg": "ไม่พบรายการข้อมูล"}
            _Service_Fees_Format: Service_Fees_Format = _row[0]
            calculate_list_str = _Service_Fees_Format.calculate_list
            calculate_list = calculate_list_str.split(",")
            calculate_list.remove(f"{key}={value}")
            _Service_Fees_Format.calculate_list = ",".join(calculate_list)

            await db.commit()
            await db.refresh(_Service_Fees_Format)
            print(_Service_Fees_Format.calculate_list)

            return {"success": True, "data": (_Service_Fees_Format,)}
        return {"success": False, "msg": "ไม่พบรายการข้อมูล"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api_data_service_fees_format.delete("/")
async def path_service_fees_format_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(Service_Fees_Format).where(Service_Fees_Format.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Service_Fees_Format: Service_Fees_Format = _row[0]
            await db.delete(_Service_Fees_Format)
            await db.commit()
            return {"success": True, "msg": f"Service_Fees is deleted successfully"}

        else:
            return {"success": False, "msg": f"Service_Fees is not available"}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


# ? *NOTE - Services Fees Info


@router_api_data_service_fees.get("/")
async def path_service_fees_get(
    id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = select(Service_Fees)
    if id:
        _sql = _sql.where(Service_Fees.id == id)
    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}

    else:
        return {"success": False, "msg": f"Service_Fees is not available"}


@router_api_data_service_fees.post("/")
async def path_service_fees_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    round: int = Form(...),
    status: str = Form(...),
    remark: str = Form(""),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id == 0:
            _sql = select(Service_Fees).where(Service_Fees.name == name)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": f"Service_Fees is duplicated"}
            _Service_Fees = Service_Fees(
                name=name,
                type=type,
                round=round,
                status=status,
                remark=remark,
                create_id=user.id,
            )
            db.add(_Service_Fees)
            await db.commit()
            await db.refresh(_Service_Fees)

            _services_fees_format = Service_Fees_Format(
                service_fees_id=_Service_Fees.id,
                name="ค่าบริการตั้งต้น",
                condition_type="default",
                primary=1,
                priority=1,
            )
            db.add(_services_fees_format)
            await db.commit()
            await db.refresh(_services_fees_format)

            return {"success": True, "data": _Service_Fees}

        _sql = select(Service_Fees).where(Service_Fees.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Service_Fees: Service_Fees = _row[0]
            _Service_Fees.name = name
            _Service_Fees.type = type
            _Service_Fees.round = round
            _Service_Fees.status = status
            _Service_Fees.remark = remark
            await db.commit()
            await db.refresh(_Service_Fees)
            print(_Service_Fees)
            return {"success": True, "data": _Service_Fees}
        return {"success": False, "msg": f"Service_Fees is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api_data_service_fees.delete("/")
async def path_service_fees_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(Service_Fees).where(Service_Fees.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Service_Fees: Service_Fees = _row[0]
            print(_Service_Fees)

            _sql = delete(Service_Fees_Format).where(Service_Fees_Format.service_fees_id == _Service_Fees.id)
            _row = await db.execute(_sql)
            await db.delete(_Service_Fees)
            await db.commit()
            return {"success": True, "msg": f"Service_Fees is deleted successfully"}

        else:
            return {"success": False, "msg": f"Service_Fees is not available"}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}
