import os
import pprint
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
import sqlalchemy
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, delete, func, or_, update

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

from ..core.models import (
    Account_Record,
    App_Configurations,
    GateWay,
    Log,
    Log_Transaction,
    Member,
    Member_Type,
    Member_User,
    Member_User_Permission,
    Permission_Role,
    Service_Fees,
    System_User,
    System_User_Type,
    Transaction_Record,
)


def validate_permission_role(permission_role_str: str) -> bool:
    print(f"validate_time_range :{permission_role_str}")
    if re.match(
        "^((?:mon|tue|wed|thu|fri|sat|sun))-((?:mon|tue|wed|thu|fri|sat|sun))\(([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]-([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]\)$",
        permission_role_str,
    ):
        _c_t0, _c_t1 = permission_role_str.split("(")[1][:-1].split("-")
        if _c_t0 >= _c_t1:
            return False
        return True
    return False


router_api = APIRouter(prefix="/api/member", tags=["API_Member"])


@router_api.get("/")
async def path_member_get(
    id: str = (...),
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    if id:
        _sql = (
            select(
                Member,
                Member_Type,
                Member_User,
                System_User,
            )
            .where(Member.id == id)
            .outerjoin(
                Member_Type,
                (Member.member_type_id == Member_Type.id),
            )
            .outerjoin(
                Member_User,
                (Member.member_user_id == Member_User.id),
            )
            .outerjoin(
                System_User,
                (Member.create_id == System_User.id),
            )
        )

        _row = (await db.execute(_sql)).all()
        if _row:
            return {"success": True, "data": _row}

    return {"success": False, "msg": f"Member is not available"}


@router_api.get("/datatable")
async def path_member_get_datatable(
    req_para: Request,
    data_filter: int = 0,
    select_member_valid: int = 0,
    user_jwt=Depends(get_jwt_access),
    # user=Depends(access_cookie_token),
    db: AsyncSession = Depends(get_async_session),
):
    _new = time_now(0)
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

    _table = Member
    _order_columns = _table.id
    if order_by_column:
        _order_columns = getattr(_table, order_by_column, _table.id)

    print(f"order_by_column : {_order_columns}")
    rows = []
    condition = True
    if search:
        if search.isdecimal():
            condition = or_(
                _table.id == int(search),
                _table.card_id.like(f"%{search}%"),
            )
        else:
            condition = or_(
                _table.card_id.like(f"%{search}%"),
                _table.status.like(f"%{search}%"),
                Member_User.name.like(f"%{search}%"),
            )
    print_success(condition)
    _order_by = _order_columns.asc() if order_dir == "asc" else _order_columns.desc()

    # ? ----------------------- select ---------------------------------------!SECTION
    sql = select(_table, Member_Type, Member_User)
    if data_filter:
        sql = sql.where(_table.member_type_id == data_filter)

    if select_member_valid == 1:
        # ? For Not Expired Members
        sql = sql.where(_table.expire_date_time > _new)
    if select_member_valid == 2:
        # ? For Expired Members
        sql = sql.where(_table.expire_date_time < _new)
    if select_member_valid == 3:
        # ? For Not Start Members
        sql = sql.where(_table.start_date_time > _new)

    if select_member_valid == 4:
        # ? For DisableMembers
        sql = sql.where(_table.status == "DISABLE")

    sql = sql.outerjoin(
        Member_Type,
        (_table.member_type_id == Member_Type.id),
    ).outerjoin(Member_User, (_table.member_user_id == Member_User.id))

    recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    if search:
        _sql = sql.where(condition)
        recordsFiltered = (await db.execute(select([func.count()]).select_from(_sql))).one()[0]

    else:
        recordsFiltered = recordsTotal

    rows = (await db.execute(sql.where(condition).order_by(_order_by).offset(skip).limit(limit))).all()

    # print(rows[0])
    result = {"draw": params["draw"], "recordsTotal": recordsTotal, "recordsFiltered": recordsFiltered, "data": rows}

    # time.sleep(0.5)
    return result


@router_api.get("/type")
async def path_member_type_get(
    id: str = (None),
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)

    _sql = select(Member_Type, Service_Fees, Permission_Role)
    if id:
        _sql = _sql.where(Member_Type.id == id)

    _sql = _sql.outerjoin(
        Service_Fees,
        (Member_Type.service_fees_id == Service_Fees.id),
    ).outerjoin(Permission_Role, (Member_Type.permission_role_id == Permission_Role.id))

    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}

    return {"success": False, "msg": f"Member_Type is not available"}


@router_api.post("/type")
async def path_member_type_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    name: str = Form(...),
    expire_day: int = Form(...),
    amount: int = Form(...),
    service_fees_id: str = Form(None),
    permission_role_id: str = Form(None),
    remark: str = Form(None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id:
            # แก้ไข
            _sql = select(Member_Type).where(Member_Type.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                _Member_Type: Member_Type = _row[0]
                _Member_Type.create_id = user.id
                _Member_Type.name = name
                _Member_Type.expire_day = expire_day
                _Member_Type.amount = amount
                _Member_Type.service_fees_id = service_fees_id
                _Member_Type.permission_role_id = permission_role_id
                _Member_Type.remark = remark

                await db.commit()
                await db.refresh(_Member_Type)

                return {"success": True, "data": _Member_Type}
        else:
            # add Member_Type to database
            _sql = select(Member_Type).where(Member_Type.name == name, Member_Type.id != id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": "ข้อมูล ชื่อประเภท มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
            _Member_Type = Member_Type(create_id=user.id)
            _Member_Type.name = name
            _Member_Type.expire_day = expire_day
            _Member_Type.amount = amount
            _Member_Type.service_fees_id = service_fees_id
            _Member_Type.permission_role_id = permission_role_id
            _Member_Type.remark = remark
            db.add(_Member_Type)
            await db.commit()
            await db.refresh(_Member_Type)
            return {"success": True, "data": _Member_Type}

        return {"success": False, "msg": f"Member is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/type")
async def path_member_type_del_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: str = (None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = delete(Member_Type).where(Member_Type.id == id)

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


@router_api.get("/type/datatable")
async def path_member_type_get_datatable(
    req_para: Request,
    user_jwt=Depends(get_jwt_access),
    # user=Depends(access_cookie_token),
    db: AsyncSession = Depends(get_async_session),
):
    _new = time_now(0)
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

    _table = Member_Type
    _order_columns = _table.id
    if order_by_column:
        _order_columns = getattr(_table, order_by_column, _table.id)

    print(f"order_by_column : {_order_columns}")
    rows = []
    condition = True
    if search:
        if search.isdecimal():
            condition = or_(
                _table.id == int(search),
                # _table.card_id.like(f"%{search}%"),
            )
        else:
            condition = or_(
                _table.name.like(f"%{search}%"),
            )
    print_success(condition)
    _order_by = _order_columns.asc() if order_dir == "asc" else _order_columns.desc()

    # ? ----------------------- select ---------------------------------------!SECTION
    sql = (
        select(_table, Permission_Role, Service_Fees, func.count(Member.id))
        .outerjoin(
            Permission_Role,
            (_table.permission_role_id == Permission_Role.id),
        )
        .outerjoin(
            Service_Fees,
            (_table.service_fees_id == Service_Fees.id),
        )
        .outerjoin(Member, (Member.member_type_id == _table.id))
        .group_by(Member_Type.id)
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

    # time.sleep(0.5)
    return result


@router_api.get("/user/datatable")
async def path_member_user_get_datatable(
    req_para: Request,
    user_jwt=Depends(get_jwt_access),
    # user=Depends(access_cookie_token),
    db: AsyncSession = Depends(get_async_session),
):
    _new = time_now(0)
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

    _table = Member_User
    _order_columns = _table.id
    if order_by_column:
        _order_columns = getattr(_table, order_by_column, _table.id)

    print(f"order_by_column : {_order_columns}")
    rows = []
    condition = True
    if search:
        if search.isdecimal():
            condition = or_(
                _table.id == int(search),
                # _table.card_id.like(f"%{search}%"),
            )
        else:
            condition = or_(
                _table.name.like(f"%{search}%"),
            )
    print_success(condition)
    _order_by = _order_columns.asc() if order_dir == "asc" else _order_columns.desc()

    # ? ----------------------- select ---------------------------------------!SECTION
    sql = (
        select(_table, Member, func.count(Member.id), Member_User_Permission)
        .outerjoin(
            Member,
            (Member.member_user_id == _table.id),
        )
        .outerjoin(
            Member_User_Permission,
            (Member_User_Permission.id == _table.member_user_permission_id),
        )
        .group_by(Member_User.id)
    )

    recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    if search:
        _sql = sql.where(condition)
        recordsFiltered = (await db.execute(select([func.count()]).select_from(_sql))).one()[0]
    else:
        recordsFiltered = recordsTotal

    rows = (await db.execute(sql.where(condition).order_by(_order_by).offset(skip).limit(limit))).all()

    result = {"draw": params["draw"], "recordsTotal": recordsTotal, "recordsFiltered": recordsFiltered, "data": rows}

    # time.sleep(0.5)
    return result


@router_api.get("/user")
async def path_member_user_get(
    id: str = (None),
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)

    _sql = select(Member_User)
    if id:
        _sql = _sql.where(Member_User.id == id)

    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}

    return {"success": False, "msg": f"Member_User is not available"}


@router_api.post("/user")
async def path_member_user_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    name: str = Form(...),
    address: str = Form(None),
    status: str = Form(...),
    member_user_permission_name: str = Form(None),
    remark: str = Form(None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        member_user_permission_id = None
        if member_user_permission_name:
            sql = select(Member_User_Permission.id).where(Member_User_Permission.name == member_user_permission_name)
            member_user_permission_id = (await db.execute(sql)).one_or_none()
            if member_user_permission_id:
                member_user_permission_id = member_user_permission_id[0]
            else:
                return {"success": False, "msg": "ข้อมูล ผิดพลาด ไม่สามารถดำเนินการได้"}

        if id:
            # แก้ไข
            _sql = select(Member_User).where(Member_User.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                _Member_User: Member_User = _row[0]
                _Member_User.create_id = user.id
                _Member_User.name = name
                _Member_User.status = status
                _Member_User.member_user_permission_id = member_user_permission_id
                _Member_User.address = address
                _Member_User.remark = remark

                await db.commit()
                await db.refresh(_Member_User)

                return {"success": True, "data": _Member_User}
        else:
            # add Member_Type to database
            _sql = select(Member_User).where(Member_User.name == name, Member_User.id != id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": "ข้อมูล ชื่อประเภท มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
            _Member_User = Member_User(create_id=user.id)
            _Member_User.name = name
            _Member_User.member_user_permission_id = member_user_permission_id
            _Member_User.status = status
            _Member_User.address = address
            _Member_User.remark = remark
            db.add(_Member_User)
            await db.commit()
            await db.refresh(_Member_User)
            return {"success": True, "data": _Member_User}

        return {"success": False, "msg": f"Member is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/user")
async def path_member_user_del(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: str = (None),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = delete(Member_User).where(Member_User.id == id)

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


@router_api.get("/toggle_app_configurations_allow_not_register_member")
async def path_member_toggle_app_configurations_allow_not_register_member(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_allow_not_register_member")
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            app_configurations_allow_not_register_member: App_Configurations = _row[0]
            config.app_configurations_allow_not_register_member = True if app_configurations_allow_not_register_member.value == "Enable" else False
            return {
                "success": True,
                "msg": f"แก้ไขข้อมูลรายการอนุญาตใช้งานบัตร : {app_configurations_allow_not_register_member.value}",
                "data": config.app_configurations_allow_not_register_member,
            }

        return {"success": False, "msg": f"app_configurations_allow_not_register_member is not available"}
    except Exception as e:
        print_error(e)
        return {"success": False, "msg": str(e)}


@router_api.post("/toggle_app_configurations_allow_not_register_member")
async def path_member_toggle_app_configurations_allow_not_register_member_pos(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(App_Configurations).where(App_Configurations.key == "app_configurations_allow_not_register_member")
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            app_configurations_allow_not_register_member: App_Configurations = _row[0]
            if app_configurations_allow_not_register_member.value == "Enable":
                app_configurations_allow_not_register_member.value = "Disable"
            else:
                app_configurations_allow_not_register_member.value = "Enable"
            await db.commit()
            await db.refresh(app_configurations_allow_not_register_member)
            config.app_configurations_allow_not_register_member = True if app_configurations_allow_not_register_member.value == "Enable" else False
            return {
                "success": True,
                "msg": f"แก้ไขข้อมูลรายการอนุญาตใช้งานบัตร : {app_configurations_allow_not_register_member.value}",
                "data": config.app_configurations_allow_not_register_member,
            }

        return {"success": False, "msg": f"app_configurations_allow_not_register_member is not available"}
    except Exception as e:
        print_error(e)
        return {"success": False, "msg": str(e)}


@router_api.post("/")
async def path_member_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    card_ids: str = Form(None),
    card_id: str = Form(...),
    member_owner: str = Form(None),
    member_type_id: int = Form(None),
    start_date_time: str = Form(None),
    status: str = Form(...),
    remark: str = Form(""),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:

        if id:
            _sql = select(Member).where(Member.card_id == card_id, Member.id != id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": f"มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}

            _sql = select(Member).where(Member.id == id)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                _Member: Member = _row[0]
                _Member.card_id = card_id
                _Member.status = status
                _Member.remark = remark
                member_user_id = None
                _sql = select(Member_User.id).where(Member_User.name == member_owner)
                _row = (await db.execute(_sql)).one_or_none()
                if _row:
                    member_user_id = _row[0]
                _Member.member_user_id = member_user_id
                await db.commit()
                await db.refresh(_Member)

                return {"success": True, "data": _Member}
        else:
            if card_ids:
                # print(member_type_id)
                _Member_Type = None
                _sql = select(Member_Type).where(Member_Type.id == member_type_id)
                _row = (await db.execute(_sql)).one_or_none()
                # print(_row)
                if _row is not None:
                    _Member_Type: Member_Type = _row[0]
                else:
                    return {"success": False, "msg": f"Member_Type is not available"}

                ids_list = card_ids.split(":")
                member_user_id = None
                if member_owner:
                    _sql = select(Member_User.id).where(Member_User.name == member_owner)
                    _row = (await db.execute(_sql)).one_or_none()
                    print(_row)
                    if _row is not None:
                        member_user_id = _row[0]

                start_date_time = datetime.strptime(start_date_time, "%Y-%m-%d %H:%M")
                expire_date_time = start_date_time + timedelta(days=_Member_Type.expire_day)
                success_count = 0
                card_id_duplicate = ""
                for l in ids_list:
                    _sql = select(Member.id).where(Member.card_id == l)
                    _row = (await db.execute(_sql)).one_or_none()
                    if _row is not None:
                        card_id_duplicate += f"{l},"
                        continue
                    _m = Member(
                        card_id=l,
                        create_id=user.id,
                        member_user_id=member_user_id,
                        member_type_id=member_type_id,
                        status=status,
                        remark=remark,
                        create_date_time=_now,
                        start_date_time=start_date_time,
                        expire_date_time=expire_date_time,
                    )
                    db.add(_m)
                    success_count += 1
                await db.commit()
                print(ids_list)

                if success_count == len(ids_list):
                    return {"success": True, "data": success_count, "msg": "successfully"}
                else:
                    return {"success": True, "data": success_count, "msg": f"มีเลขซ้ำ :{card_id_duplicate}"}

            return {"success": False, "msg": f"Member add is not allowed"}

        return {"success": False, "msg": f"Member is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.post("/set")
async def path_member_set_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    ids: str = Form(...),
    value: str = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if ids.endswith(","):
            ids = ids[:-1]
        ids = ids.split(",")
        k, v = value.split("=")
        if k == "status":
            _sql = update(Member).where(Member.id.in_(ids)).values(status=v)
        elif k == "member_owner":
            _sql = select(Member_User.id).where(Member_User.name == v)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                member_user_id = _row[0]
                _sql = update(Member).where(Member.id.in_(ids)).values(member_user_id=member_user_id)
            else:
                return {"success": False, "msg": "member_owner not found"}
        else:
            return {"success": False, "msg": "column not found"}
        result = await db.execute(_sql)
        await db.commit()
        print_success(f"update rows is successful :{result.rowcount}")
        return {"success": True, "data": result.rowcount}
    except Exception as e:
        print_error(e)
        return {"success": False, "msg": str(e)}


@router_api.delete("/del")
async def path_member_del_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    ids: str = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if ids.endswith(","):
            ids = ids[:-1]
        ids = ids.split(",")
        _sql = delete(Member).where(Member.id.in_(ids))

        result = await db.execute(_sql)
        await db.commit()
        print_success(f"delete rows is successful :{result.rowcount}")
        return {"success": True, "data": result.rowcount}
    except Exception as e:
        print_error(e)
        return {"success": False, "msg": str(e)}


@router_api.delete("/")
async def path_member_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(Member).where(Member.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Member: Member = _row[0]

            await db.delete(_Member)
            await db.commit()
            return {"success": True, "msg": f"Member is deleted successfully"}

        else:
            return {"success": False, "msg": f"Member is not available"}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


# ? *NOTE - Member_User


@router_api.get("/user_list")
async def path_member_user_list_get(
    id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = select(Member_User.name).order_by(Member_User.name)
    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}
    else:
        return {"success": False, "msg": f"Permission_Role is not available"}


# ? *NOTE - Permission_Role


@router_api.get("/permission_role_list")
async def path_Permission_Role_list_get(
    id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = select(Permission_Role)
    if id:
        _sql = _sql.where(Permission_Role.id == id)
    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}

    else:
        return {"success": False, "msg": f"Permission_Role is not available"}


@router_api.post("/permission_role")
async def path_permission_role_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    remark: str = Form(""),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id == 0:
            _sql = select(Permission_Role).where(Permission_Role.name == name)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": f"Permission_Role is duplicated"}
            _Permission_Role = Permission_Role(
                name=name,
                type=type,
                remark=remark,
                create_id=user.id,
            )
            db.add(_Permission_Role)
            await db.commit()
            await db.refresh(_Permission_Role)

            return {"success": True, "data": _Permission_Role}

        _sql = select(Permission_Role).where(Permission_Role.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Permission_Role: Permission_Role = _row[0]
            _Permission_Role.name = name
            _Permission_Role.type = type
            _Permission_Role.remark = remark
            await db.commit()
            await db.refresh(_Permission_Role)

            return {"success": True, "data": _Permission_Role}
        return {"success": False, "msg": f"Permission_Role is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/permission_role")
async def path_permission_role_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(Permission_Role).where(Permission_Role.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Permission_Role: Permission_Role = _row[0]

            await db.delete(_Permission_Role)
            await db.commit()
            return {"success": True, "msg": f"Permission_Role is deleted successfully"}

        else:
            return {"success": False, "msg": f"Permission_Role is not available"}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.post("/permission_role/permission_allow")
async def path_permission_role_list_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    key: str = Form(...),
    value: str = Form(...),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    if not validate_permission_role(value):
        return {"success": False, "msg": "ข้อมูลนี้มีตั้งค่าไม่ถูกต้อง ไม่สามารถดำเนินการได้"}
    try:
        _sql = select(Permission_Role).where(Permission_Role.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Permission_Role: Permission_Role = _row[0]
            permission_allow = _Permission_Role.permission_allow
            if not permission_allow:
                permission_allow_list = []
            else:
                permission_allow_list = permission_allow.split(",")
            if key == "*":
                _data = f"{len(permission_allow_list)+1}@{value}"
                permission_allow_list.append(_data)
            else:
                success = False
                for index, d in enumerate(permission_allow_list):
                    k, v = d.split("@")
                    if key == k:
                        permission_allow_list[index] = f"{key}@{value}"
                        success = True
                        break
            _Permission_Role.permission_allow = ",".join(permission_allow_list)
            await db.commit()
            await db.refresh(_Permission_Role)
            return {"success": True, "data": _Permission_Role}

        return {"success": False, "msg": f"Permission_Role is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/permission_role/permission_allow")
async def path_permission_role_list_delete(
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
        _sql = select(Permission_Role).where(Permission_Role.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Permission_Role: Permission_Role = _row[0]
            permission_allow = _Permission_Role.permission_allow

            permission_allow_list = permission_allow.split(",")
            print(permission_allow_list)
            _data = f"{key}@{value}"
            print_warning(_data)
            if _data in permission_allow_list:
                permission_allow_list.remove(_data)

                for index, d in enumerate(permission_allow_list):
                    _, v = d.split("@")
                    permission_allow_list[index] = f"{index+1}@{v}"
            _Permission_Role.permission_allow = ",".join(permission_allow_list)
            await db.commit()
            await db.refresh(_Permission_Role)
            print(_Permission_Role.permission_allow)
            return {"success": True, "data": _Permission_Role}

        return {"success": False, "msg": f"Permission_Role is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


# ? *NOTE - Member User Permission


@router_api.get("/user_permission_list")
async def path_member_user_permission_list_get(
    id: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    _sql = select(Member_User_Permission)
    if id:
        _sql = _sql.where(Member_User_Permission.id == id)
    _row = (await db.execute(_sql)).all()
    if _row:
        return {"success": True, "data": _row}

    else:
        return {"success": False, "msg": f"Member_User_Permission is not available"}


@router_api.post("/user_permission")
async def path_user_permission_post(
    request: Request,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    id: int = Form(...),
    name: str = Form(...),
    limit: int = Form(...),
    status: str = Form(...),
    detail: str = Form(""),
):
    _now = time_now(0)
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        if id == 0:
            _sql = select(Member_User_Permission).where(Member_User_Permission.name == name)
            _row = (await db.execute(_sql)).one_or_none()
            if _row:
                return {"success": False, "msg": f"Member_User_Permission is duplicated"}
            _Member_User_Permission = Member_User_Permission(
                name=name,
                status=status,
                detail=detail,
                limit=limit,
                create_id=user.id,
            )
            db.add(_Member_User_Permission)
            await db.commit()
            await db.refresh(_Member_User_Permission)

            return {"success": True, "data": _Member_User_Permission}

        _sql = select(Member_User_Permission).where(Member_User_Permission.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Member_User_Permission: Member_User_Permission = _row[0]
            _Member_User_Permission.name = name
            _Member_User_Permission.status = status
            _Member_User_Permission.limit = limit
            _Member_User_Permission.detail = detail
            await db.commit()
            await db.refresh(_Member_User_Permission)

            return {"success": True, "data": _Member_User_Permission}
        return {"success": False, "msg": f"Member_User_Permission is not available"}
    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "unique" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการซ้ำกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}


@router_api.delete("/user_permission")
async def path_user_permission_delete(
    id: int,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        _sql = select(Member_User_Permission).where(Member_User_Permission.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if _row:
            _Member_User_Permission: Member_User_Permission = _row[0]

            await db.delete(_Member_User_Permission)
            await db.commit()
            return {"success": True, "msg": f"Member_User_Permission is deleted successfully"}

        else:
            return {"success": False, "msg": f"Member_User_Permission is not available"}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        if "foreign key constraint" in err:
            return {"success": False, "msg": "ข้อมูลนี้มีการเชื่อมโยงกับข้อมูลอื่นๆ ไม่สามารถดำเนินการได้"}
        return {"success": False, "msg": str(e)}
