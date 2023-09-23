import base64
from http.client import HTTPResponse
from io import BytesIO
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
    App_Configurations,
    GateWay,
    Log_Transaction,
    Lpr_Camera,
    Member,
    Member_Type,
    Parking_Lot,
    Lpr_Log,
    Service_Fees,
    System_User,
    Transaction_Record,
)
from sqlalchemy import select

from app.core import models
from app.routes.websocket import WebSockets


DIR_PATH = config.DIR_PATH

router_api = APIRouter(tags=["DOCUMENT"], prefix="/api/document")


@router_api.get("/")
async def get_document(
    document: str = None,
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
):
    k = "app_configurations_" + document.lower()
    sql = select(App_Configurations).where(App_Configurations.key == k)
    print(sql)
    row = (await db.execute(sql)).one_or_none()
    if row:
        return {"success": True, "data": row}
    else:
        return {"success": False, "msg": f"Document {document} is not available"}


@router_api.post("/")
async def post_document(
    user_jwt=Depends(get_jwt_access),
    db: AsyncSession = Depends(get_async_session),
    document: str = Form(...),
    data_document: str = Form(...),
):
    user: System_User = await get_user_by_id(db, user_jwt)
    try:
        k = "app_configurations_" + document.lower()
        sql = select(App_Configurations).where(App_Configurations.key == k)
        row = (await db.execute(sql)).one_or_none()
        if row:
            _App_Configurations: App_Configurations = row[0]
            _App_Configurations.value = data_document
            await db.commit()
            await db.refresh(_App_Configurations)
            return {"success": True, "data": _App_Configurations}
        else:
            _App_Configurations = App_Configurations(key=k, value=data_document)
            db.add(_App_Configurations)
            await db.commit()
            await db.refresh(_App_Configurations)
            return {"success": True, "data": _App_Configurations}

    except Exception as e:
        print_error(e)
        err = str(e).lower()
        return {"success": False, "msg": str(e)}
