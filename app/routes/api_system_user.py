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

from ..core.models import Log, System_User, System_User_Type

router_api = APIRouter(prefix="/api/systems_user", tags=["API_System_User"])


@router_api.get("/datatable")
async def path_systems_user_get_datatable(
    req_para: Request,
    user_jwt=Depends(get_jwt_access),
    # user=Depends(access_cookie_token),
    db: AsyncSession = Depends(get_async_session),
):
    params = dict(req_para.query_params)
    select_columns = set()
    print_success(params)
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

    _table = System_User
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
                _table.username.like(f"%{search}%"),
            )
        else:
            condition = or_(
                _table.username.like(f"%{search}%"),
            )
    print_success(condition)
    _order_by = _order_columns.asc() if order_dir == "asc" else _order_columns.desc()

    # ? ----------------------- select ---------------------------------------!SECTION
    sql = select(_table, System_User_Type)
    sql = sql.join(System_User_Type, (System_User.system_user_type_id == System_User_Type.id))
    recordsTotal = (await db.execute(select([func.count()]).select_from(sql))).one()[0]
    if search:
        _sql = sql.where(condition)
        recordsFiltered = (await db.execute(select([func.count()]).select_from(_sql))).one()[0]
    else:
        recordsFiltered = recordsTotal

    rows = (await db.execute(sql.where(condition).order_by(_order_by).offset(skip).limit(limit))).all()

    result = {"draw": params["draw"], "recordsTotal": recordsTotal, "recordsFiltered": recordsFiltered, "data": rows}
    # print(result)
    # time.sleep(3)

    return result


@router_api.get("/")
async def path_systems_user_get(
    id: int = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    _sql = select(System_User)
    if id:
        _sql = _sql.where(System_User.id == id)
        # _sql = _sql.join(System_User_Type, (System_User.system_user_type_id == System_User_Type.id))
        _system_user: System_User = (await db.execute(_sql)).one_or_none()
        print(_system_user)
        return _system_user
    else:
        data: System_User = (await db.execute(_sql)).all()
        return {"success": True, "data": data}


@router_api.get("/me")
async def path_systems_user_me_get(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    me: System_User = await get_user_by_id(db, user_jwt)

    if me:
        return {"success": True, "data": me}
    else:
        return {"success": False, "msg": "how are you?"}


@router_api.post("/me_change_password")
async def path_systems_user_me_change_pass_post(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    old_password: str = Form(...),
    new_password: str = Form(...),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    print(user.password)
    print(old_password)
    if not verify_password(old_password, user.password):
        return {"success": False, "msg": "password is incorrect"}

    user.password = get_password_hash(new_password)

    await db.commit()
    await db.refresh(user)

    return {"success": True, "msg": "successfully"}


@router_api.post("/me")
async def path_systems_user_me_post(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    username: str = Form(...),
    name: str = Form(None),
    image_upload: UploadFile = File(None),
):
    user: System_User = await get_user_by_id(db, user_jwt)

    if username == user.username and name == user.name and not image_upload:
        return {"success": True, "msg": "successfully not changed"}

    if username != user.username:
        _sql = select(System_User.id).where(System_User.username == username)
        _system_user = (await db.execute(_sql)).one_or_none()
        if _system_user:
            return {"success": False, "msg": "item is not already in database"}

        if user.username in ["ROOT", "root"]:
            return {"success": False, "msg": "root (user already to system state can be changed)"}
        user.username = username

    if name:
        user.name = name

    await db.commit()
    await db.refresh(user)

    if image_upload:
        try:
            image_content = await image_upload.read()
            image_upload = Image.open(BytesIO(image_content))

            if image_upload.format == "PNG":
                image_upload = image_upload.convert("RGB")
            _path = f"/static/data_base/image/system_user/{user.id}.jpg"
            image_upload.save(f".{_path}")
            time_stamp = int(time_now().timestamp())
            user.pictureUrl = _path + f"?time_stamp={time_stamp}"
            await db.commit()

        except Exception as e:
            print_error(e)
            return {"success": True, "msg": str(e)}

    return {"success": True, "msg": "successfully"}


@router_api.post("/")
async def path_systems_user_post(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    username: str = Form(...),
    name: str = Form(None),
    password: str = Form(default=None),
    status: str = Form(default=None),
    system_user_type_id: int = Form(...),
    image_upload: UploadFile = File(None),
    remark: str = Form(default=None),
    id: str = Form(default=None),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    if not (await allowed_permissions(db, user, "management_system_user")):
        return {"success": False, "msg": "not permission_allowed"}
    if id:
        try:
            id = int(id)
        except ValueError as e:
            return {"success": False, "msg": e}

        _sql = select(System_User).where(System_User.id == id)
        _row = (await db.execute(_sql)).one_or_none()
        if not _row:
            return {"success": False, "msg": "item is not already in database"}

        _system_user: System_User = _row[0]
        if username.lower() == "root" and user != _system_user:
            return {"success": False, "msg": f"root not already in use please other name !?@#@$)(**&*&^%&(()^&%^$#$#$$^^&^*^"}

        if user.username == "root" and username != "root" and _system_user.username == "root":
            return {"success": False, "msg": f"root not chang other name !?@#@$)(**&*&^%&(()^&%^$#$#$$^^&^*^"}

        if username == "root":
            system_user_type_id = None
            status = None

        if username:
            _system_user.username = username

        if name:
            _system_user.name = name
        if password:
            _system_user.password = get_password_hash(password)
        if status:
            _system_user.status = status
        if system_user_type_id:
            _system_user.system_user_type_id = system_user_type_id
        if remark:
            _system_user.remark = remark

        await db.commit()
        await db.refresh(_system_user)
    else:
        _sql = select(System_User).where(System_User.username == username)
        _system_user = (await db.execute(_sql)).one_or_none()
        if _system_user:
            return {"success": False, "msg": "item is already in database"}

        _system_user = System_User(
            username=username,
            name=name if name else username,
            password=get_password_hash(password),
            system_user_type_id=system_user_type_id,
            remark=remark,
            create_by=user.username,
            status="created",
        )
        print(_system_user)
        db.add(_system_user)
        await db.commit()
        await db.refresh(_system_user)

    if image_upload:
        try:
            image_content = await image_upload.read()
            image_upload = Image.open(BytesIO(image_content))

            if image_upload.format == "PNG":
                image_upload = image_upload.convert("RGB")
            _path = f"/static/data_base/image/system_user/{_system_user.id}.jpg"
            image_upload.save(f".{_path}")
            time_stamp = int(time_now().timestamp())
            _system_user.pictureUrl = _path + f"?time_stamp={time_stamp}"
            await db.commit()

        except Exception as e:
            print_error(e)
            return {"success": True, "msg": str(e)}

    return {"success": True, "msg": "successfully"}


@router_api.delete("/{id}")
async def path_systems_user_delete(
    id: int = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    if not allowed_permissions(db, user_jwt, "management_system_user"):
        return {"success": False, "msg": "user not allowed_permissions"}
    if id:
        try:
            _sql = select(System_User).where(System_User.id == id)
            # _sql = _sql.join(System_User_Type, (System_User.system_user_type_id == System_User_Type.id))
            _row: System_User = (await db.execute(_sql)).one_or_none()
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


@router_api.get("/system_user_type")
async def router_system_user_type(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    sql = select(System_User_Type)
    result = (await db.execute(sql)).all()
    return result


# ! ********************************************************
@router_api.get("/header")
async def router_api_test(request: Request):
    print_warning(time_now())
    # request_json = await request.json()
    print(request.headers)
    return request.headers


@router_api.post("/log", status_code=status.HTTP_201_CREATED)
async def router_api_test(
    log: Log,
    db: AsyncSession = Depends(get_async_session),
    user_id=Depends(get_jwt_access),
):
    log.id = None
    log.time = time_now(0)
    # user: models.System_User = await get_user_by_id(db,user_id)
    # print_success(user)
    log.log_owner = user_id
    try:
        db.add(log)
        await db.commit()
        # db.refresh(log)
        sql = select(Log, System_User).join(Log, Log.log_owner == System_User.id)
        result = await db.execute(sql)
        return result.all()
    except Exception as e:
        print_error(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}")


@router_api.get("/log/{id}")
async def router_api_test_get(id: int, db: AsyncSession = Depends(get_async_session), user=Depends(get_jwt_access)):
    try:
        _query = select(Log, System_User).join(Log, Log.log_owner == System_User.id)

        return db.execute(_query).all()
    except Exception as e:
        print_error(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}")
