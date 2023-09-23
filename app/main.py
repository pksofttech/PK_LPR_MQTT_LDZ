# Python > 3.8
# Edit by Pksofttech for user
# ? main for set application
import logging
from urllib import response
from fastapi import FastAPI, Request

from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, JSONResponse, RedirectResponse, HTMLResponse
from pydantic import Json

# from fastapi_mqtt.fastmqtt import FastMQTT
# from fastapi_mqtt.config import MQTTConfig
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .stdio import *

from app.core import auth, database, mqtt

app = FastAPI(title="WEB-API", version="22.06.0")

mqtt.fast_mqtt.init_app(app)

app.mount("/static", StaticFiles(directory="./static"), name="static")
# app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

# Set all CORS enabled origins

# root_logger = logging.getLogger()
# root_logger.setLevel(logging.INFO)
# handler = logging.FileHandler("applog.log", "w", "utf-8")
# handler.setFormatter(logging.Formatter(f"%(levelname)s %(asctime)s  %(name)s %(threadName)s : %(message)s"))
# root_logger.addHandler(handler)
#
# root_logger.info(f"************************************************************")
# root_logger.info(f"Start Msg Logger at time {time_now()}")
# root_logger.info(f"************************************************************")

# origins = [
#     "http://localhost.tiangolo.com",
#     "https://localhost.tiangolo.com",
#     "http://localhost",
#     "http://192.168.1.152/",
# ]

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await database.init_db()
    print_success(f"Server Start Time : {time_now()}")


@app.on_event("shutdown")
async def shutdown_event():
    print_warning(f"Server shutdown Time : {time_now()}")


# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     start_time = time.time()
#     print("*************************************************")
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     response.headers["X-Process-Time"] = str(process_time)

#     return response

# ? Setting router path
from app.routes import (
    views,
    websocket,
    sse,
    api_system_user,
    api_function,
    api_data,
    api_transaction_record,
    api_account_record,
    api_member,
    api_lpr,
    api_estamp_devices,
    api_document,
)

app.include_router(auth.router)
app.include_router(websocket.router)
app.include_router(views.router)
# app.include_router(face_scan.router)

app.include_router(api_system_user.router_api)
app.include_router(api_function.router_api)
app.include_router(api_data.router_api_data_service_fees_format)
app.include_router(api_data.router_api_data_service_fees)
app.include_router(api_transaction_record.router_api)
app.include_router(api_account_record.router_api)
app.include_router(api_member.router_api)
app.include_router(api_lpr.router_api)
app.include_router(api_lpr.router_api_devices_lpr)
app.include_router(api_estamp_devices.router_api)
app.include_router(api_document.router_api)
# @app.exception_handler(HTTPException)
# async def app_exception_handler(request: Request, exception: HTTPException):
#     url_str = str(request.url).split("/")[-1]
#     # print_error(url_str)
#     if request.method == "GET":
#         print_error(exception.detail)
#         if exception.detail == "Not Found":
#             if "." in url_str:
#                 return HTMLResponse(str(exception.detail), status_code=exception.status_code)
#             return RedirectResponse(url=f"/page_404?url={request.url}")
#         return PlainTextResponse(str(exception.detail), status_code=exception.status_code)

#     else:
#         return JSONResponse(str(exception.detail), status_code=exception.status_code)
