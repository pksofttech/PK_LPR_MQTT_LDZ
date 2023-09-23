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
from sqlmodel import and_, func, or_

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

router_api = APIRouter(prefix="/api/account_record", tags=["API_Account_Record"])


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

    limit = params["length"]
    skip = params["start"]
    condition = ""
    search = params["search[value]"]

    _table = Account_Record
    _order_columns = _table.id
    # if order_by_column:
    #     _order_columns = getattr(_table, order_by_column, _table.id)

    match order_by_column:
        case "Account_Record.id":
            _order_columns = Account_Record.id
        case "Account_Record.no":
            _order_columns = Account_Record.no
        case "Account_Record.date_time":
            _order_columns = Account_Record.date_time
        case "Account_Record.type":
            _order_columns = Account_Record.type
        case "Transaction_Record.card_id":
            _order_columns = Transaction_Record.card_id
        case "Account_Record.amount":
            _order_columns = Account_Record.amount
        case _:
            pass

    print(f"order_by_column : {_order_columns}")
    rows = []
    _system_user: System_User = aliased(System_User)
    condition = True
    search = search.strip()
    if search:
        if search.isdecimal():
            condition = or_(
                _table.id == int(search),
                Transaction_Record.card_id.like(f"%{search}%"),
            )
        else:
            condition = or_(
                Account_Record.no.like(f"%{search}%"),
                Account_Record.type.like(f"%{search}%"),
                Service_Fees.name.like(f"%{search}%"),
                _system_user.name.like(f"%{search}%"),
            )
    print_success(condition)
    _order_by = _order_columns.asc() if order_dir == "asc" else _order_columns.desc()

    # ? ----------------------- select ---------------------------------------!SECTION
    try:
        d_start, d_end = date_range.split(" - ")
        d_start = d_start.replace("/", "-")
        d_end = d_end.replace("/", "-")

    except ValueError as e:
        return {"success": False, "msg": str(e)}

    # (in_log.date_time.between(d_start, d_end)),

    _data_filter = and_(_table.date_time.between(d_start, d_end))
    sql = (
        select(
            _table,
            Transaction_Record,
            Service_Fees,
            _system_user.name.label("system_user_by"),
        )
        .where(_data_filter)
        .join(
            _system_user,
            (_table.create_id == _system_user.id),
        )
        .outerjoin(
            Transaction_Record,
            (_table.transaction_record_id == Transaction_Record.id),
        )
        .outerjoin(
            Service_Fees,
            (Transaction_Record.service_fees_id == Service_Fees.id),
        )
    )

    recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    if search:
        _sql = sql.where(condition)
        recordsFiltered = (await db.execute(select([func.count()]).select_from(_sql))).one()[0]
    else:
        recordsFiltered = recordsTotal

    rows = (await db.execute(sql.where(condition).order_by(_order_by).offset(skip).limit(limit))).all()

    # print(rows[0])
    result = {"draw": params["draw"], "recordsTotal": recordsTotal, "recordsFiltered": recordsFiltered, "data": rows}

    time.sleep(0.5)
    return result


@router_api.get("/")
async def path_transaction_record_get(
    id: int = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    if id:
        _sql = select(Transaction_Record).where(Transaction_Record.id == id)
        _tran: Transaction_Record = (await db.execute(_sql)).one_or_none()
        print(_tran)
        return {"success": True, "data": _tran[0]}
    return {"success": False, "msg": "not id in Query"}
