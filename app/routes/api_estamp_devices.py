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
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, or_
from app.core.database import get_async_session
from app.core.auth import access_cookie_token, allowed_permissions, get_jwt_access, get_user, get_user_by_id
from app.core.utility import get_password_hash, verify_password

from ..stdio import *
from app.core import config
from app.core.database import System_User
from sqlalchemy import select
from fastapi import status, HTTPException
from PIL import Image
from io import BytesIO

from ..core.models import Estamp_Device, Estamp_Record_Log, Log, Service_Fees, System_User, System_User_Type, Transaction_Record

router_api = APIRouter(prefix="/api/estamp_device", tags=["API_Estamp_Devices"])


@router_api.get("/datatable")
async def path_estamp_log_get_datatable(
    req_para: Request,
    date_range: str = None,
    data_filter: str = None,
    user_jwt=Depends(get_jwt_access),
    # user=Depends(access_cookie_token),
    db: AsyncSession = Depends(get_async_session),
):
    params = dict(req_para.query_params)
    select_columns = set()
    for k in params:
        # print(f"{k}:{params[k]}")
        match = re.search(r"^columns\[.*\]\[data\]", k)
        if match:
            select_columns.add(f"{params[k]}")
    # print(select_columns)
    order_by_col = params["order[0][column]"]

    order_by_column = params.get(f"columns[{order_by_col}][data]")
    order_dir = params["order[0][dir]"]

    print(order_by_col, order_by_column, order_dir)
    limit = params["length"]
    skip = params["start"]
    condition = ""
    search = params["search[value]"]

    rows = []

    Service_Fees_0: Service_Fees = aliased(Service_Fees)
    Service_Fees_1: Service_Fees = aliased(Service_Fees)

    _table = Estamp_Record_Log
    _order_columns = _table.id
    # if order_by_column:
    #     _order_columns = getattr(_table, order_by_column, _table.id)

    match order_by_column:
        case "Transaction_Record.card_id":
            _order_columns = Transaction_Record.card_id
        case _:
            pass

    print(f"order_by_column : {_order_columns}")

    condition = True
    if search:
        if search.isdecimal():
            condition = or_(
                _table.id == int(search),
                _table.transaction_record_id.like(f"%{search}%"),
                Transaction_Record.card_id.like(f"%{search}%"),
            )
        else:
            condition = or_(
                _table.status.like(f"%{search}%"),
                System_User.name.like(f"%{search}%"),
                Estamp_Device.device_name.like(f"%{search}%"),
                Service_Fees_0.name.like(f"%{search}%"),
                Service_Fees_1.name.like(f"%{search}%"),
            )
    print_success(condition)
    _order_by = _order_columns.asc() if order_dir == "asc" else _order_columns.desc()
    print_success(_order_by)

    # ? ----------------------- select ---------------------------------------!SECTION
    try:
        d_start, d_end = date_range.split(" - ")
        d_start = d_start.replace("/", "-")
        d_end = d_end.replace("/", "-")

    except ValueError as e:
        return {"success": False, "msg": str(e)}

    # sql = select(_table, Service_Fees, Log_Transaction, GateWay, Account_Record)
    # sql = select(_table).where(_table.date_time.between(d_start, d_end))
    # sql = select(_table)

    # (in_log.date_time.between(d_start, d_end)),
    _data_filter = None
    # print(data_filter)
    _data_filter = _table.date_time.between(d_start, d_end)

    sql = (
        select(
            _table,
            System_User,
            Estamp_Device,
            Transaction_Record,
            Service_Fees_0.name.label("Service_Fees_0"),
            Service_Fees_1.name.label("Service_Fees_1"),
        )
        .where(_data_filter)
        .join(
            System_User,
            (_table.system_user_id == System_User.id),
        )
        .join(
            Estamp_Device,
            (_table.estamp_device_id == Estamp_Device.id),
        )
        .join(
            Transaction_Record,
            (_table.transaction_record_id == Transaction_Record.id),
        )
        .join(
            Service_Fees_0,
            (_table.before_service_fees_id == Service_Fees_0.id),
        )
        .join(
            Service_Fees_1,
            (_table.service_fees_id == Service_Fees_1.id),
        )
    )

    # recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    if search:
        _sql = sql.where(condition)
        recordsFiltered = (await db.execute(select([func.count()]).select_from(_sql))).one()[0]
    else:
        recordsFiltered = recordsTotal

    rows = (await db.execute(sql.where(condition).order_by(_order_by).offset(skip).limit(limit))).all()

    # print(rows[0])
    result = {"draw": params["draw"], "recordsTotal": recordsTotal, "recordsFiltered": recordsFiltered, "data": rows}

    # time.sleep(1)
    return result


@router_api.get("/")
async def path_estamp_device_get(
    id: int = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    _sql = select(Estamp_Device)
    if id:
        _sql = _sql.where(Estamp_Device.id == id)
        _Estamp_Devices: Estamp_Device = (await db.execute(_sql)).one_or_none()
        return {"success": True, "data": _Estamp_Devices}
    else:
        data = (await db.execute(_sql)).all()
        return {"success": True, "data": data}


@router_api.get("/stamp/")
async def path_estamp_device_stamp_get(
    device_name: str,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    _sql = select(Estamp_Device)
    if device_name:
        _sql = _sql.where(Estamp_Device.device_name == device_name)
        rows = (await db.execute(_sql)).one_or_none()
        if rows:
            _Estamp_Devices: Estamp_Device = rows[0]
            list_service_fee = _Estamp_Devices.service_fees_ids.split(",")
            if list_service_fee:
                sql = select(Service_Fees).where(Service_Fees.id.in_(list_service_fee))
                list_service_fee = (await db.execute(sql)).all()
                return {"success": True, "data": list_service_fee}

    return {"success": False, "msg": "Not id Estamp_Device"}


@router_api.get("/stamp_transection/")
async def path_stamp_transection_get(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    before_service_fees: Service_Fees = aliased(Service_Fees)
    after_service_fees: Service_Fees = aliased(Service_Fees)
    _sql = (
        select(
            Estamp_Record_Log,
            System_User,
            before_service_fees.name.label("before_service_fees"),
            after_service_fees.name.label("after_service_fees"),
            Estamp_Device,
        )
        .where(Estamp_Record_Log.transaction_record_id == id)
        .join(System_User, (Estamp_Record_Log.system_user_id == System_User.id))
        .join(before_service_fees, (Estamp_Record_Log.before_service_fees_id == before_service_fees.id))
        .join(after_service_fees, (Estamp_Record_Log.service_fees_id == after_service_fees.id))
        .join(Estamp_Device, (Estamp_Record_Log.estamp_device_id == Estamp_Device.id))
    )
    rows = (await db.execute(_sql)).all()
    if rows is not None:
        return {"success": True, "data": rows}

    return {"success": False, "msg": "Not id Estamp_Device"}


@router_api.post("/stamp_transection/")
async def path_stamp_transection_post(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    transaction_record_id: int = Form(...),
    service_fees_id: int = Form(...),
    estamp_device_name: str = Form(...),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(Estamp_Device).where(Estamp_Device.device_name == estamp_device_name)
        _row = (await db.execute(_sql)).one_or_none()
        if not _row:
            return {"success": False, "msg": "ไม่พบข้อมูล estamp_device_name"}
        _Estamp_Device: Estamp_Device = _row[0]

        _sql = select(Transaction_Record).where(Transaction_Record.id == transaction_record_id)
        _row = (await db.execute(_sql)).one_or_none()
        if not _row:
            return {"success": False, "msg": "ไม่พบข้อมูล Transaction_Record"}
        _Transaction_Record: Transaction_Record = _row[0]

        _sql = select(Service_Fees).where(Service_Fees.id == service_fees_id)
        _row = (await db.execute(_sql)).one_or_none()
        if not _row:
            return {"success": False, "msg": "ไม่พบข้อมูล Service_Fees"}
        _Service_Fees: Service_Fees = _row[0]

        _Estamp_Record_Log = Estamp_Record_Log(
            estamp_device_id=_Estamp_Device.id,
            transaction_record_id=_Transaction_Record.id,
            system_user_id=user.id,
            date_time=time_now(),
            before_service_fees_id=_Transaction_Record.service_fees_id,
            service_fees_id=service_fees_id,
            status="success",
            log="",
        )
        db.add(_Estamp_Record_Log)
        await db.commit()
        await db.refresh(_Estamp_Record_Log)
        _Transaction_Record.service_fees_id = _Service_Fees.id
        await db.commit()
        await db.refresh(_Transaction_Record)
        return {"success": True, "data": _Estamp_Record_Log}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        return {"success": False, "msg": str(e)}


@router_api.post("/")
async def path_estamp_device_post(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    device_name: str = Form(...),
    device_id: str = Form(...),
    type: str = Form("WEB"),
    status: str = Form(...),
    system_user_ids: str = Form(""),
    service_fees_ids: str = Form(""),
    remark: str = Form(default=""),
    id: int = Form(...),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id == 0:
            print("Add new Estamp_Device")
            _sql = select(Estamp_Device).where(Estamp_Device.device_name == device_name)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": f"Estamp_Device is duplicated"}
            _Estamp_Device = Estamp_Device(
                create_id=user.id,
                device_name=device_name,
                device_id=device_id,
                type=type,
                status=status,
                system_user_ids=system_user_ids,
                service_fees_ids=service_fees_ids,
                remark=remark,
            )
            db.add(_Estamp_Device)
            await db.commit()
            await db.refresh(_Estamp_Device)
            return {"success": True, "data": _Estamp_Device}

        _sql = select(Estamp_Device).where(Estamp_Device.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Estamp_Device: Estamp_Device = _row[0]
            _Estamp_Device.device_name = device_name
            _Estamp_Device.device_id = device_id
            _Estamp_Device.type = type
            _Estamp_Device.status = status
            _Estamp_Device.system_user_ids = system_user_ids
            _Estamp_Device.service_fees_ids = service_fees_ids
            _Estamp_Device.remark = remark
            await db.commit()
            await db.refresh(_Estamp_Device)
            print(_Estamp_Device)
            return {"success": True, "data": _Estamp_Device}
        return {"success": False, "msg": f"Estamp_Device is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/")
async def path_estamp_device_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    if id:
        try:
            _sql = select(Estamp_Device).where(Estamp_Device.id == id)
            # _sql = _sql.join(System_User_Type, (System_User.system_user_type_id == System_User_Type.id))
            _row: Estamp_Device = (await db.execute(_sql)).one_or_none()
            if _row:
                await db.delete(_row[0])
                await db.commit()
            return {"success": True, "msg": "successfully"}
        except Exception as e:
            print_error(e)
            err = str(e).lower()
            if "foreign key constraint" in err:
                return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
            return {"success": False, "msg": str(e)}
    return {"success": False, "msg": f"Data is not available"}
