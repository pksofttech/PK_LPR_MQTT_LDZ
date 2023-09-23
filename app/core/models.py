from sqlmodel import Relationship, SQLModel, Field
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from ..stdio import *


class App_Configurations(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, nullable=False)
    value: str = Field(default=None)


class System_User_Type(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_type: str
    permission_allowed: str = Field(default="")
    system_users: List["System_User"] = Relationship(back_populates="system_user_type")


class System_User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    name: str = Field(unique=True)
    password: str
    createDate: datetime = Field(default=time_now(0), nullable=False)
    create_by: str
    # last_login_Date = Column(DateTime)
    status: str
    pictureUrl: str = Field(default="/static/image/logo.png")
    remark: str = Field(default="")
    system_user_type_id: int = Field(foreign_key="system_user_type.id", nullable=False)
    system_user_type: Optional[System_User_Type] = Relationship(back_populates="system_users")


class Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    time: Optional[datetime]
    log_type: Optional[str] = Field(default="info")
    msg: str
    log_owner: int = Field(default=None, foreign_key="system_user.id")


class Parking_Lot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    create_id: int = Field(nullable=False, foreign_key="system_user.id")
    value: int = Field(default=0)
    limit: int = Field(default=9999)
    detail: str = Field(default="")


class GateWay(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    create_id: int = Field(nullable=False, foreign_key="system_user.id")
    parking_id: int = Field(nullable=False, foreign_key="parking_lot.id")
    date_created: datetime = Field(nullable=False)
    images_path: str = Field(default="")
    type: str = Field(default="IN")
    status: str = Field(default="Enable")
    remark: str = Field(default="")
    ip_cameras: str = Field(default="")


class Service_Fees(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    create_id: int = Field(default=None, foreign_key="system_user.id")
    type: str = Field(default="GENERAL", nullable=False)
    status: str = Field(default="Enable", nullable=False)
    round: int = Field(default=0)
    remark: str = Field(default="")


class Service_Fees_Format(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="default")
    primary: int = Field(default=0)
    priority: int = Field(default=1, nullable=False)
    condition_type: str = Field(nullable=False)
    condition: str = Field(default=None)
    status: str = Field(default="Enable", nullable=False)
    service_fees_id: int = Field(default=None, foreign_key="service_fees.id")
    calculate_list: str = Field("")


class Log_Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: str = Field(default=None)
    date_time: datetime = Field(nullable=False)
    license: str = Field(default=None)
    create_id: int = Field(foreign_key="system_user.id", nullable=False)
    gateway_id: int = Field(foreign_key="gateway.id", nullable=False)
    images_path: str = Field(default="")
    type: str = Field(default="")
    remark: str = Field(default="")


class Transaction_Record(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: str = Field(nullable=False)
    create_id: int = Field(default=None, foreign_key="system_user.id")
    log_in: int = Field(default=None, foreign_key="log_transaction.id")
    log_out: int = Field(default=None, foreign_key="log_transaction.id")
    parked: int = Field(default=None)
    service_fees_id: int = Field(default=None, foreign_key="service_fees.id")
    type: str = Field(default="NORMAL", max_length=16)
    status: str = Field(default="CHECK_IN", max_length=16)
    remark: str = Field(default="", max_length=32)


class Account_Record(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_record_id: int = Field(foreign_key="transaction_record.id", nullable=False)
    create_id: int = Field(foreign_key="system_user.id")
    date_time: datetime = Field(nullable=False)
    type: str = Field(default="CASH", max_length=16)
    amount: int = Field(default=0)
    pay: int = Field(default=0)
    discount: int = Field(default=0)
    ststus: str = Field(default="NORMAL", max_length=16)
    no: str = Field(default="TEX.", max_length=32)
    remark: str = Field(default="", max_length=32)


class Member_User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    create_id: int = Field(foreign_key="system_user.id")
    name: str = Field(nullable=False)
    address: str = Field(default=None, max_length=128)
    status: str = Field(default="NORMAL", max_length=16)
    remark: str = Field(default="", max_length=32)
    member_user_permission_id: int = Field(default=None, foreign_key="member_user_permission.id")


class Member_User_Permission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    create_id: int = Field(foreign_key="system_user.id")
    name: str = Field(nullable=False)
    detail: str = Field(default="", max_length=128)
    status: str = Field(default="NORMAL", max_length=16)
    limit: int = Field(nullable=False, default=1)
    permission_allow: str = Field(default=None)


class Permission_Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    create_id: int = Field(foreign_key="system_user.id")
    name: str = Field(nullable=False)
    type: str = Field(default="IN")
    permission_allow: str = Field(default=None)
    remark: str = Field(default="", max_length=32)


class Member_Type(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    create_id: int = Field(foreign_key="system_user.id")
    name: str = Field(nullable=False)
    permission_role_id: int = Field(default=None, foreign_key="permission_role.id")
    service_fees_id: int = Field(default=None, foreign_key="service_fees.id")
    amount: int = Field(default=0)
    expire_day: int = Field(default=0)
    remark: str = Field(default="", max_length=64)


class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: str = Field(max_length=32, unique=True)
    create_id: int = Field(foreign_key="system_user.id")
    member_user_id: int = Field(default=None, foreign_key="member_user.id")
    member_type_id: int = Field(nullable=False, foreign_key="member_type.id")
    create_date_time: datetime = Field(nullable=False)
    start_date_time: datetime = Field(nullable=False)
    expire_date_time: datetime = Field(nullable=False)
    status: str = Field(default="NORMAL", max_length=16)
    remark: str = Field(default="", max_length=32)


class Lpr_Camera(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    create_id: int = Field(foreign_key="system_user.id")
    device_name: str = Field(nullable=False, unique=True)
    device_id: str = Field(default=None, unique=True)
    device_ip: str = Field(default=None)
    type: str = Field(default="MODULE")
    direction: str = Field(default="AUTO")
    mode: str = Field(default="ALL")
    device_model: str = Field(default=None)
    gateway_id: int = Field(default=None, foreign_key="gateway.id")
    system_user_id: int = Field(default=None, foreign_key="system_user.id")
    service_fees_id: int = Field(default=None, foreign_key="service_fees.id")
    device_send_data_path: str = Field(default=None)
    device_send_heartbeat_path: str = Field(default=None)
    remark: str = Field(default=None, max_length=128)


class Lpr_Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plate_num: str = Field(default="")
    start_time: str = Field()
    date_time: datetime = Field(nullable=False)
    status: str = Field(default="LOG")
    tag: str = Field(default="warning")
    images_path: str = Field(default="")
    lpr_camera_id: int = Field(default=None, foreign_key="lpr_camera.id")
    log_transaction_id: int = Field(default=None, foreign_key="log_transaction.id")
    transaction_record_id: int = Field(default=None, foreign_key="transaction_record.id")


class Estamp_Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    create_id: int = Field(foreign_key="system_user.id")
    device_name: str = Field(nullable=False, unique=True)
    device_id: str = Field(default=None, unique=True)
    device_ip: str = Field(default=None)
    type: str = Field(default="ESTAMP")
    status: str = Field(default="ENABLE")
    mode: str = Field(default="ALL")
    device_model: str = Field(default=None)
    system_user_ids: str = Field(default="")
    service_fees_ids: str = Field(default="")
    images_path: str = Field(default="")
    remark: str = Field(default=None, max_length=128)


class Estamp_Record_Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    estamp_device_id: int = Field(default=None, foreign_key="estamp_device.id")
    transaction_record_id: int = Field(default=None, foreign_key="transaction_record.id")
    system_user_id: int = Field(default=None, foreign_key="system_user.id")
    date_time: datetime = Field(nullable=False)
    before_service_fees_id: int = Field(default=None, foreign_key="service_fees.id")
    service_fees_id: int = Field(default=None, foreign_key="service_fees.id")
    status: str = Field(default="LOG")
    log: str = Field(default=None, max_length=128)
