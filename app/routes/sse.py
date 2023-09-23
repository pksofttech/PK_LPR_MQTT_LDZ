from http.client import HTTPResponse
import os
from typing import Union
from unittest import result

from fastapi import APIRouter, Depends, Request, Header

from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.auth import access_cookie_token, get_jwt_access, get_user_by_id

from ..stdio import *
from app.core import config
from app.core.database import System_User
from sqlalchemy import select

from app.core import models

DIR_PATH = config.DIR_PATH
from sse_starlette.sse import EventSourceResponse
import asyncio

router = APIRouter()

"""
Get status as an event generator
"""
status_stream_delay = 1  # second
status_stream_retry_timeout = 30000  # milisecond
last_event_data = "No data"
last_event_snap = "https://placeimg.com/640/480/people"
last_event_snap_id = 0
last_event_map_gps = "13.886171638687525,100.45820545600664"


async def status_event_generator(request, param1):
    global last_event_data, last_event_snap, last_event_map_gps
    print_warning(f"status_event_generator >> {param1}")
    previous_status = None
    previous_last_event_snap_id = -1
    previous_last_event_map_gps = ""
    try:
        while True:
            if await request.is_disconnected():
                print("Request disconnected")
                break

            if previous_status and 0:
                print("Request completed. Disconnecting now")
                yield {"event": "end", "data": ""}
                break

            # current_status = await compute_status(param1)
            # current_status = time_now().strftime("%Y-%m-%d %H:%M:%S")
            if previous_status != last_event_data:
                yield {"event": "update", "retry": status_stream_retry_timeout, "data": last_event_data}
                previous_status = last_event_data
                # print('Current status :%s', current_status)
            else:
                # print(f'No change in status... {param1}')
                pass

            if previous_last_event_snap_id != last_event_snap_id:
                yield {"event": "SanpPic", "retry": status_stream_retry_timeout, "data": last_event_snap}
                previous_last_event_snap_id = last_event_snap_id
                print(
                    "Current status :",
                )

            _lat, _lng = last_event_map_gps.split(",")
            _lat = float(_lat)

            _lng = float(_lng)

            # _lat += 0.1
            # print(_lat)

            # last_event_map_gps = f"{_lat},{_lng}"
            if previous_last_event_map_gps != last_event_map_gps:
                yield {"event": "map_gps", "retry": status_stream_retry_timeout, "data": last_event_map_gps}
                previous_last_event_map_gps = last_event_map_gps
                print(
                    "Current status :",
                )

            await asyncio.sleep(status_stream_delay)
            """https://maps.google.com/maps?width=100%25&amp;height=600&amp;hl=th&amp;q=13.886171638687525,100.45820545600664&amp;t=k&amp;z=19&amp;ie=UTF8&amp;iwloc=B&amp;output=embed"""
    except asyncio.CancelledError as e:
        print_success(f"status_event_generator CancelledError >> {param1}")


@router.get("/status/stream", tags=["stream"])
async def runStatus(param1: str, request: Request):
    event_generator = status_event_generator(request, param1)
    return EventSourceResponse(event_generator)
