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
from sqlmodel import and_, asc, desc, func, or_, update

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

from ..core.models import Account_Record, GateWay, Log, Log_Transaction, Service_Fees, System_User, System_User_Type, Transaction_Record

router_api = APIRouter(prefix="/api/transaction_record", tags=["API_Transaction_Record"])


@router_api.get("/table")
async def path_transaction_record_table(
    date_range: str = "2023/01/01 00:00 - 2023/04/31 00:00",
    data_filter: str = None,
    length: int = 1000,
    user_jwt=Depends(get_jwt_access),
    # user=Depends(access_cookie_token),
    db: AsyncSession = Depends(get_async_session),
):
    rows = []
    in_log: Log_Transaction = aliased(Log_Transaction)
    in_log_system_user: System_User = aliased(System_User)
    out_log: Log_Transaction = aliased(Log_Transaction)
    out_log_system_user: System_User = aliased(System_User)
    in_gate: GateWay = aliased(GateWay)
    out_gate: GateWay = aliased(GateWay)

    # ? ----------------------- select ---------------------------------------!SECTION
    try:
        d_start, d_end = date_range.split(" - ")
        d_start = d_start.replace("/", "-")
        d_end = d_end.replace("/", "-")

    except Exception as e:
        return {"success": False, "msg": str(e)}

    # sql = select(_table, Service_Fees, Log_Transaction, GateWay, Account_Record)
    # sql = select(_table).where(_table.date_time.between(d_start, d_end))
    # sql = select(_table)

    # (in_log.date_time.between(d_start, d_end)),
    _data_filter = None
    print_success(date_range)
    match data_filter:
        case "in_time":
            _data_filter = or_(in_log.date_time.between(d_start, d_end))
        case "out_time":
            _data_filter = or_(out_log.date_time.between(d_start, d_end))
        case "in_park":
            _data_filter = and_(Transaction_Record.status == "CHECK_IN", in_log.date_time.between(d_start, d_end))
        case "out_park":
            _data_filter = and_(
                or_(
                    Transaction_Record.status == "SUCCESS",
                    Transaction_Record.status == "CLOSE",
                ),
                out_log.date_time.between(d_start, d_end),
                in_log.date_time.between(d_start, d_end),
            )
        case _:
            _data_filter = and_(in_log.date_time.between(d_start, d_end))

    sql = (
        select(
            Transaction_Record.id.label("TransactionID,INTEGER"),
            Service_Fees.name.label("Service_Fees_name"),
            in_gate.name.label("in_gate_name"),
            in_log.license.label("in_log_license"),
            in_log.date_time.label("in_date_time,DATETIME"),
            in_log.images_path.label("in_images_path,IMG"),
            in_log_system_user.name.label("in_log_system_user"),
            out_gate.name.label("out_gate_name"),
            out_log.date_time.label("out_date_time,DATETIME"),
            out_log_system_user.name.label("out_log_system_user"),
            Account_Record.amount.label("amount,INTEGER"),
        )
        .where(_data_filter)
        .join(
            Service_Fees,
            (Transaction_Record.service_fees_id == Service_Fees.id),
        )
        .outerjoin(
            in_log,
            (Transaction_Record.log_in == in_log.id),
        )
        .outerjoin(
            out_log,
            (Transaction_Record.log_out == out_log.id),
        )
        .outerjoin(
            in_gate,
            (in_log.gateway_id == in_gate.id),
        )
        .outerjoin(
            out_gate,
            (out_log.gateway_id == out_gate.id),
        )
        .outerjoin(
            in_log_system_user,
            (in_log_system_user.id == in_log.create_id),
        )
        .outerjoin(
            out_log_system_user,
            (out_log_system_user.id == out_log.create_id),
        )
        .outerjoin(
            Account_Record,
            (Account_Record.transaction_record_id == Transaction_Record.id),
        )
    )

    rows = (await db.execute(sql.offset(0).limit(length))).all()
    print(len(rows))
    # if len(rows):
    #     print(rows[0])

    result = {"data": rows}

    # time.sleep(1)
    return result


@router_api.get("/datatable")
async def path_transaction_record_get_datatable(
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

    in_log: Log_Transaction = aliased(Log_Transaction)
    in_log_system_user: System_User = aliased(System_User)
    out_log: Log_Transaction = aliased(Log_Transaction)
    out_log_system_user: System_User = aliased(System_User)
    in_gate: GateWay = aliased(GateWay)
    out_gate: GateWay = aliased(GateWay)

    condition = True
    search = search.strip()
    if search:
        if search.isdecimal():
            condition = or_(
                Transaction_Record.id == int(search),
                Transaction_Record.card_id.like(f"%{search}%"),
                in_log.license.like(f"%{search}%"),
            )
        else:
            condition = or_(
                Transaction_Record.card_id.like(f"%{search}%"),
                in_log.license.like(f"%{search}%"),
                out_log_system_user.name.like(f"%{search}%"),
                in_log_system_user.name.like(f"%{search}%"),
            )
    print_success(condition)

    _table = Transaction_Record
    _order_columns = _table.id
    # if order_by_column:
    #     _order_columns = getattr(_table, order_by_column, _table.id)

    match order_by_column:
        case "Transaction_Record.card_id":
            _order_columns = Transaction_Record.card_id
        case "in_log_license":
            _order_columns = in_log.license
        case "in_date_time":
            _order_columns = in_log.date_time
        case "in_gate_name":
            _order_columns = in_gate.name
        case "in_log_system_user":
            _order_columns = in_log_system_user.name
        case "out_date_time":
            _order_columns = out_log.date_time
        case "out_gate_name":
            _order_columns = out_gate.name
        case "out_log_system_user":
            _order_columns = out_log_system_user.name
        case "Transaction_Record.status":
            _order_columns = Transaction_Record.status
        case "Transaction_Record.type":
            _order_columns = Transaction_Record.type
        case "Service_Fees_name":
            _order_columns = Service_Fees.name
        case "amount":
            _order_columns = Account_Record.amount
        case "Transaction_Record.parked":
            _order_columns = Transaction_Record.parked
        case _:
            pass

    print(f"order_by_column : {_order_columns}")
    _order_by = _order_columns.asc() if order_dir == "asc" else _order_columns.desc()
    print_success(_order_by)

    # ? ----------------------- select ---------------------------------------!SECTION
    try:
        d_start, d_end = date_range.split(" - ")
        d_start = d_start.replace("/", "-")
        d_end = d_end.replace("/", "-")

    except Exception as e:
        return {"success": False, "msg": str(e)}

    # sql = select(_table, Service_Fees, Log_Transaction, GateWay, Account_Record)
    # sql = select(_table).where(_table.date_time.between(d_start, d_end))
    # sql = select(_table)

    # (in_log.date_time.between(d_start, d_end)),
    _data_filter = None
    print(data_filter)
    match data_filter:
        case "in_time":
            _data_filter = or_(in_log.date_time.between(d_start, d_end))
        case "out_time":
            _data_filter = or_(out_log.date_time.between(d_start, d_end))
        case "in_park":
            _data_filter = and_(Transaction_Record.status == "CHECK_IN", in_log.date_time.between(d_start, d_end))
        case "out_park":
            _data_filter = and_(
                or_(
                    Transaction_Record.status == "SUCCESS",
                    Transaction_Record.status == "CLOSE",
                ),
                out_log.date_time.between(d_start, d_end),
                in_log.date_time.between(d_start, d_end),
            )
        case _:
            _data_filter = and_(in_log.date_time.between(d_start, d_end))

    sql = (
        select(
            Transaction_Record,
            Service_Fees.name.label("Service_Fees_name"),
            in_gate.name.label("in_gate_name"),
            in_log.license.label("in_log_license"),
            in_log.date_time.label("in_date_time"),
            in_log.images_path.label("in_images_path"),
            in_log_system_user.name.label("in_log_system_user"),
            out_gate.name.label("out_gate_name"),
            out_log.date_time.label("out_date_time"),
            out_log_system_user.name.label("out_log_system_user"),
            Account_Record.amount.label("amount"),
        )
        .where(_data_filter)
        .join(
            Service_Fees,
            (Transaction_Record.service_fees_id == Service_Fees.id),
        )
        .outerjoin(
            in_log,
            (Transaction_Record.log_in == in_log.id),
        )
        .outerjoin(
            out_log,
            (Transaction_Record.log_out == out_log.id),
        )
        .outerjoin(
            in_gate,
            (in_log.gateway_id == in_gate.id),
        )
        .outerjoin(
            out_gate,
            (out_log.gateway_id == out_gate.id),
        )
        .outerjoin(
            in_log_system_user,
            (in_log_system_user.id == in_log.create_id),
        )
        .outerjoin(
            out_log_system_user,
            (out_log_system_user.id == out_log.create_id),
        )
        .outerjoin(
            Account_Record,
            (Account_Record.transaction_record_id == Transaction_Record.id),
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


@router_api.get("/report/datatable")
async def path_transaction_record_report_get_datatable(
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

    in_log: Log_Transaction = aliased(Log_Transaction)
    in_log_system_user: System_User = aliased(System_User)
    out_log: Log_Transaction = aliased(Log_Transaction)
    out_log_system_user: System_User = aliased(System_User)
    in_gate: GateWay = aliased(GateWay)
    out_gate: GateWay = aliased(GateWay)

    condition = True
    if search:
        if search.isdecimal():
            condition = or_(
                Transaction_Record.card_id.like(f"%{search}%"),
                in_log.license.like(f"%{search}%"),
            )
        else:
            condition = or_(
                in_gate.name.like(f"%{search}%"),
                out_gate.name.like(f"%{search}%"),
            )
    print_success(condition)

    _order_by = asc(order_by_column) if order_dir == "asc" else desc(order_by_column)

    print_success(_order_by)

    # ? ----------------------- select ---------------------------------------!SECTION
    try:
        d_start, d_end = date_range.split(" - ")
        d_start = d_start.replace("/", "-")
        d_end = d_end.replace("/", "-")

    except ValueError as e:
        return {"success": False, "msg": str(e)}

    _date_range = or_(in_log.date_time.between(d_start, d_end), out_log.date_time.between(d_start, d_end))
    match data_filter:
        case "by_gate_in":
            _date_range = in_log.date_time.between(d_start, d_end)
        case "by_gate_out":
            _date_range = out_log.date_time.between(d_start, d_end)
        # case _:
        #     pass

    print(data_filter)
    group_name_in = in_gate.name.label("group_in")
    group_name_out = out_gate.name.label("group_out")
    sql = (
        select(
            func.count(Transaction_Record.id).label("count_transaction"),
            func.count(out_log.id).label("count_out_log"),
            func.count(Account_Record.id).label("count_acc_log"),
            func.sum(Account_Record.amount).label("total_amount"),
            group_name_in,
            group_name_out,
        )
        .where(_date_range)
        .join(
            in_log,
            (Transaction_Record.log_in == in_log.id),
        )
        .join(
            in_gate,
            (in_log.gateway_id == in_gate.id),
        )
        .outerjoin(
            out_log,
            (out_log.id == Transaction_Record.log_out),
        )
        .outerjoin(
            out_gate,
            (out_log.gateway_id == out_gate.id),
        )
        .outerjoin(
            Account_Record,
            (Account_Record.transaction_record_id == Transaction_Record.id),
        )
    )

    match data_filter:
        case "by_gate_in":
            sql = sql.group_by(in_gate.id)
        case "by_gate_out":
            sql = sql.group_by(out_gate.id)
        case "by_system_user":
            sql = sql.group_by(out_gate.id)
        case _:
            sql = sql.group_by(in_gate.id, out_gate.id)

    # recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    if search:
        _sql = sql.where(condition)
        recordsFiltered = (await db.execute(select([func.count()]).select_from(_sql))).one()[0]
    else:
        recordsFiltered = recordsTotal

    rows = (await db.execute(sql.where(condition).order_by(_order_by).offset(skip).limit(limit))).all()

    # print(rows)
    result = {"draw": params["draw"], "recordsTotal": recordsTotal, "recordsFiltered": recordsFiltered, "data": rows}

    # time.sleep(1)
    return result


@router_api.get("/report_system_user/datatable")
async def path_transaction_record_report_system_user_get_datatable(
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

    in_log: Log_Transaction = aliased(Log_Transaction)
    in_log_system_user: System_User = aliased(System_User)
    out_log: Log_Transaction = aliased(Log_Transaction)
    out_log_system_user: System_User = aliased(System_User)
    in_gate: GateWay = aliased(GateWay)
    out_gate: GateWay = aliased(GateWay)

    condition = True
    if search:
        if search.isdecimal():
            condition = or_(
                Transaction_Record.card_id.like(f"%{search}%"),
            )
        else:
            match data_filter:
                case "by_system_user_in":
                    condition = or_(
                        in_log_system_user.name.like(f"%{search}%"),
                    )
                case "by_system_user_out":
                    condition = or_(
                        out_log_system_user.name.like(f"%{search}%"),
                    )
                case _:
                    condition = or_(
                        in_log_system_user.name.like(f"%{search}%"),
                        out_log_system_user.name.like(f"%{search}%"),
                    )
    print_success(condition)

    _order_by = asc(order_by_column) if order_dir == "asc" else desc(order_by_column)

    print_success(_order_by)

    # ? ----------------------- select ---------------------------------------!SECTION
    try:
        d_start, d_end = date_range.split(" - ")
        d_start = d_start.replace("/", "-")
        d_end = d_end.replace("/", "-")

    except ValueError as e:
        return {"success": False, "msg": str(e)}

    _date_range = or_(in_log.date_time.between(d_start, d_end), out_log.date_time.between(d_start, d_end))
    # match data_filter:
    #     case "by_gate_in":
    #         _date_range = in_log.date_time.between(d_start, d_end)
    #     case "by_gate_out":
    #         _date_range = out_log.date_time.between(d_start, d_end)
    #     # case _:
    #     #     pass

    print(data_filter)
    group_name_in = in_log_system_user.name.label("group_in")
    group_name_out = out_log_system_user.name.label("group_out")
    sql = (
        select(
            func.count(Transaction_Record.id).label("count_transaction"),
            func.count(out_log.id).label("count_out_log"),
            func.count(Account_Record.id).label("count_acc_log"),
            func.sum(Account_Record.amount).label("total_amount"),
            group_name_in,
            group_name_out,
        )
        .where(_date_range)
        .join(
            in_log,
            (Transaction_Record.log_in == in_log.id),
        )
        .join(
            in_log_system_user,
            (in_log.create_id == in_log_system_user.id),
        )
        .outerjoin(
            out_log,
            (out_log.id == Transaction_Record.log_out),
        )
        .outerjoin(
            out_log_system_user,
            (out_log.create_id == out_log_system_user.id),
        )
        .outerjoin(
            Account_Record,
            (Account_Record.transaction_record_id == Transaction_Record.id),
        )
    )

    match data_filter:
        case "by_system_user_in":
            sql = sql.group_by(in_log.create_id)
        case "by_system_user_out":
            sql = sql.group_by(out_log.create_id)
        case "by_system_user":
            sql = sql.group_by(out_log.create_id, in_log.create_id)
        case _:
            sql = sql.group_by(out_log.create_id)

    # recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    if search:
        _sql = sql.where(condition)
        recordsFiltered = (await db.execute(select([func.count()]).select_from(_sql))).one()[0]
    else:
        recordsFiltered = recordsTotal

    rows = (await db.execute(sql.where(condition).order_by(_order_by).offset(skip).limit(limit))).all()

    # print(rows)
    result = {"draw": params["draw"], "recordsTotal": recordsTotal, "recordsFiltered": recordsFiltered, "data": rows}

    # time.sleep(1)
    return result


@router_api.get("/")
async def path_transaction_record_get(
    id: int = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    if id:
        in_log: Log_Transaction = aliased(Log_Transaction, name="In_Log")
        in_system_user: System_User = aliased(System_User, name="In_System_User")
        out_log: Log_Transaction = aliased(Log_Transaction, name="Out_Log")
        out_system_user: System_User = aliased(System_User, name="Out_System_User")
        in_gate: GateWay = aliased(GateWay, name="In_Gateway")
        out_gate: GateWay = aliased(GateWay, name="Out_Gateway")
        _sql = (
            select(
                Transaction_Record,
                Service_Fees,
                in_log,
                in_system_user,
                out_log,
                out_system_user,
                in_gate,
                out_gate,
                Account_Record,
            )
            .where(Transaction_Record.id == id)
            .join(
                Service_Fees,
                (Transaction_Record.service_fees_id == Service_Fees.id),
            )
            .outerjoin(
                in_log,
                (Transaction_Record.log_in == in_log.id),
            )
            .outerjoin(
                in_system_user,
                (in_system_user.id == in_log.create_id),
            )
            .outerjoin(
                out_log,
                (Transaction_Record.log_out == out_log.id),
            )
            .outerjoin(
                out_system_user,
                (out_system_user.id == out_log.create_id),
            )
            .outerjoin(
                in_gate,
                (in_log.gateway_id == in_gate.id),
            )
            .outerjoin(
                out_gate,
                (out_log.gateway_id == out_gate.id),
            )
            .outerjoin(
                Account_Record,
                (Account_Record.transaction_record_id == Transaction_Record.id),
            )
        )
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _tran = _row
            return {"success": True, "data": _tran}
    return {"success": False, "msg": "not id in Query"}


@router_api.post("/set")
async def path_transaction_record_set_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    value: str = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        k, v = value.split("=")
        if k == "close":
            remark = f"{v} โดย {user.name}"
            _sql = update(Transaction_Record).where(Transaction_Record.id == id).values(status="CLOSE", remark=remark)
        else:
            return {"success": False, "msg": "column not found"}
        result = await db.execute(_sql)
        await db.commit()
        print_success(f"update rows is successful :{result.rowcount}")
        return {"success": True, "data": result.rowcount}
    except Exception as e:
        print_error(e)
        return {"success": False, "msg": str(e)}
