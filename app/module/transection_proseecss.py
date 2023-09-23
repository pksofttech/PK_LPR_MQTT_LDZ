import os
import sys

from sqlmodel import func, select, update
from app.core import config
from app.core.models import (
    Account_Record,
    GateWay,
    Log_Transaction,
    Member,
    Member_Type,
    Member_User,
    Member_User_Permission,
    Parking_Lot,
    Permission_Role,
    Service_Fees,
    Service_Fees_Format,
    System_User,
    Transaction_Record,
)
from app.core.utility import save_image_file
from app.module.account import calculate_services_fee
from app.routes.websocket import WebSockets
from ..stdio import *
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image


def check_permission_str(permission_allow):
    _new = time_now(0)
    permission_allow_list = permission_allow.split(",")
    WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for l in permission_allow_list:
        k, v = l.split("@")
        d, t = v.split("(")
        t = t[:-1]
        d0, d1 = d.split("-")
        t0, t1 = t.split("-")

        d = _new.weekday()
        d0 = WEEKDAYS.index(d0)
        d1 = WEEKDAYS.index(d1)
        t = _new.strftime("%H:%M")

        print(d0, d, d1)
        print(t0, t, t1)
        if d0 <= d <= d1:
            if t0 <= t <= t1:
                return True

    return False


async def check_in_get(
    db: AsyncSession,
    card_id: str,
):
    now = time_now().replace(tzinfo=None)
    _sql = (
        select(Member, Member_Type, Service_Fees, Permission_Role, Member_User, Member_User_Permission)
        .where(Member.card_id == card_id)
        .outerjoin(
            Member_Type,
            (Member.member_type_id == Member_Type.id),
        )
        .outerjoin(
            Service_Fees,
            (Member_Type.service_fees_id == Service_Fees.id),
        )
        .outerjoin(
            Permission_Role,
            (Member_Type.permission_role_id == Permission_Role.id),
        )
        .outerjoin(
            Member_User,
            (Member.member_user_id == Member_User.id),
        )
        .outerjoin(
            Member_User_Permission,
            (Member_User.member_user_permission_id == Member_User_Permission.id),
        )
    )
    data = (await db.execute(_sql)).one_or_none()
    _Member_User_Permission_limit = None
    if data:
        _Member: Member = data[0]
        if _Member.status == "DISABLE":
            return {"success": False, "msg": f"บัตรถูกระงับการใช้งาน !", "data": None}
        print(_Member.start_date_time, now, _Member.expire_date_time)
        if _Member.start_date_time > now:
            return {"success": False, "msg": f"บัตรยังไม่ถึงกำหนดวันใช้งาน {_Member.start_date_time} !", "data": None}
        if _Member.expire_date_time < now:
            return {"success": False, "msg": f"บัตรหมดอายุการใช้งาน {_Member.expire_date_time} !", "data": None}
        _Permission_Role: Permission_Role = data[3]
        if _Permission_Role:
            if not _Permission_Role.type in ("IN", "IN-OUT"):
                if not _Permission_Role.permission_allow:
                    # Permission_Role.permission Locked
                    return {"success": False, "msg": f"บัตรถูกกำหนดค่าการใช้งาน Permission_Role!", "data": None}
                else:
                    if not check_permission_str(_Permission_Role.permission_allow):
                        return {"success": False, "msg": f"บัตรถูกกำหนดค่าการใช้งาน Permission_Role!", "data": None}

        _Member_User_Permission: Member_User_Permission = data[5]
        if _Member_User_Permission:
            print(_Member_User_Permission)
            _Member_User_Permission_limit = _Member_User_Permission.limit
    else:
        if not config.app_configurations_allow_not_register_member:
            return {"success": False, "msg": f"ไม่พบรายการลงทะเบียนบัตรในระบบ !", "data": None}
        else:
            print_warning("ทำรายการ app_configurations_allow_not_register_member")
            # data = {"Member_Type": {"name": "บัตรไม่ลงทะเบียนในระบบ"}}
            _Member_Type = Member_Type(name="บัตรไม่ลงทะเบียนในระบบ")
            data = {"Member_Type": _Member_Type}

    _sql = (
        select(Transaction_Record, Log_Transaction, Service_Fees, GateWay, Member, Member_Type)
        .where(Transaction_Record.card_id == card_id, Transaction_Record.status == "CHECK_IN")
        .join(Log_Transaction, Transaction_Record.log_in == Log_Transaction.id)
        .join(Service_Fees, Transaction_Record.service_fees_id == Service_Fees.id)
        .join(GateWay, Log_Transaction.gateway_id == GateWay.id)
        .outerjoin(Member, Member.card_id == card_id)
        .outerjoin(Member_Type, (Member.member_type_id == Member_Type.id))
    )
    _rows = (await db.execute(_sql)).all()

    if len(_rows) > 1:
        print_warning("warning for Transaction_Record")
        print(_rows)
        pass

    if _rows:
        _row = _rows[0]
        _Log_Transaction: Log_Transaction = _row[1]
        _start = _Log_Transaction.date_time.timestamp()
        _end = time_now(0).timestamp()
        parked = str(timedelta(seconds=int(_end - _start)))
        return {"success": True, "data": _row, "parked": str(parked)}

    if _Member_User_Permission_limit:
        _Member_User: Member_User = data[4]
        _sql = (
            select(func.count(Transaction_Record.id))
            .where(Transaction_Record.status == "CHECK_IN")
            .join(Member, Member.card_id == Transaction_Record.card_id)
            .join(Member_User, Member_User.id == Member.member_user_id)
            .where(Member_User.id == _Member_User.id)
        )
        _count = (await db.execute(_sql)).one_or_none()
        if _count:
            _count = _count[0]
            if _count >= _Member_User_Permission_limit:
                return {
                    "success": False,
                    "msg": f"สิทธิ์สมาชิก จำกัดการใช้บัตร {_Member_User_Permission_limit} รายการ!\n{_Member_User_Permission.detail}",
                    "data": None,
                }

    return {"success": False, "msg": f"successfully:card not found", "data": data}


async def check_in_post(
    db: AsyncSession,
    user: System_User,
    card_id: str,
    time: str,
    gateway_id: int,
    service_fees_id: int,
    image_upload_01: Image = None,
    image_upload_02: Image = None,
    license: str = None,
    remark: str = None,
):
    _now = time_now(0)
    # print_success(user)
    # if not (await allowed_permissions(db, user, "management_system_user")):
    #     return {"success": False, "msg": "not permission_allowed"}

    _sql = select(Service_Fees).where(Service_Fees.id == service_fees_id)
    _row = (await db.execute(_sql)).one_or_none()
    if not _row:
        return {"success": False, "msg": f"Service_Fees is invalid ID:{service_fees_id}"}
    _service_frees: Service_Fees = _row[0]

    _Log_Transaction = Log_Transaction(
        card_id=card_id,
        license=license,
        create_id=user.id,
        gateway_id=gateway_id,
        type="IN",
        date_time=_now,
    )
    db.add(_Log_Transaction)
    await db.commit()
    await db.refresh(_Log_Transaction)

    _trans = Transaction_Record(
        card_id=card_id,
        service_fees_id=_service_frees.id,
        create_id=user.id,
        date_time=_now,
        log_in=_Log_Transaction.id,
    )
    db.add(_trans)
    await db.commit()
    await db.refresh(_trans)

    images_path_list = []
    if image_upload_01:
        try:
            file_path = f"./static/data_base/image/Log_Transaction/{_Log_Transaction.id//1000}"
            file_name = f"{_Log_Transaction.id}_01"
            img_success = save_image_file(image_upload_01, file_path, file_name)
            if img_success:
                images_path_list.append(img_success[1:])
        except Exception as e:
            print_error(e)

    if image_upload_02:
        try:
            file_path = f"./static/data_base/image/Log_Transaction/{_Log_Transaction.id//1000}"
            file_name = f"{_Log_Transaction.id}_02"
            img_success = save_image_file(image_upload_02, file_path, file_name)
            if img_success:
                images_path_list.append(img_success[1:])
        except Exception as e:
            print_error(e)

    images_path = ",".join(images_path_list)
    _Log_Transaction.images_path = images_path
    await db.commit()
    await db.refresh(_Log_Transaction)
    _sql = (
        select(GateWay, Parking_Lot)
        .where(GateWay.id == gateway_id)
        .join(
            Parking_Lot,
            Parking_Lot.id == GateWay.parking_id,
        )
    )
    _row = (await db.execute(_sql)).one_or_none()

    _Parking_Lot: Parking_Lot = _row[1]
    print(_Parking_Lot)
    value = _Parking_Lot.value + 1
    if _Parking_Lot.limit <= value:
        value = _Parking_Lot.limit
    _Parking_Lot.value = value
    await db.commit()

    ws_json = {"func": "parking_lot_info", "params": f"{_Parking_Lot.name},{_Parking_Lot.value}/{_Parking_Lot.limit}"}
    await WebSockets.broadcast(ws_json, sendMode="json")

    return {"success": True, "msg": f"successfully:{_Log_Transaction.id}", "data": _trans}


async def check_out_get(
    db: AsyncSession,
    card_id: str,
):
    _sql = (
        select(Member, Member_Type, Permission_Role)
        .where(Member.card_id == card_id)
        .outerjoin(
            Member_Type,
            (Member.member_type_id == Member_Type.id),
        )
        .outerjoin(
            Permission_Role,
            (Member_Type.permission_role_id == Permission_Role.id),
        )
    )
    data = (await db.execute(_sql)).one_or_none()
    print(data)
    if data:
        _Member: Member = data[0]
        if _Member.status == "DISABLE":
            return {"success": False, "msg": f"บัตรถูกระงับการใช้งาน !", "data": None}

        _Permission_Role: Permission_Role = data[2]
        if _Permission_Role:
            if not _Permission_Role.type in ("OUT", "IN-OUT"):
                if not _Permission_Role.permission_allow:
                    # Permission_Role.permission Locked
                    return {"success": False, "msg": f"บัตรถูกกำหนดค่าการใช้งาน Permission_Role!", "data": None}
                else:
                    if not check_permission_str(_Permission_Role.permission_allow):
                        return {"success": False, "msg": f"บัตรถูกกำหนดค่าการใช้งาน Permission_Role!", "data": None}
    else:
        if not config.app_configurations_allow_not_register_member:
            return {"success": False, "msg": f"ไม่พบรายการลงทะเบียนบัตรในระบบ !", "data": None}
        else:
            print_warning("ทำรายการ app_configurations_allow_not_register_member")

    _sql = (
        select(Transaction_Record, Log_Transaction, Service_Fees, GateWay)
        .where(Transaction_Record.card_id == card_id, Transaction_Record.status == "CHECK_IN")
        .join(Log_Transaction, Transaction_Record.log_in == Log_Transaction.id)
        .join(Service_Fees, Transaction_Record.service_fees_id == Service_Fees.id)
        .join(GateWay, Log_Transaction.gateway_id == GateWay.id)
        .order_by(Transaction_Record.id)
    )
    _rows = (await db.execute(_sql)).all()
    if _rows:
        msg = "รายการปกติ"
        if len(_rows) > 0:
            msg = "รายการมีการเข้ามากกว่า 1 ครั้ง"
        _row = _rows[0]
        _Transaction_Record: Transaction_Record = _row[0]
        _Log_Transaction: Log_Transaction = _row[1]
        _Service_Fees: Service_Fees = _row[2]
        _GateWay: GateWay = _row[3]
        _sql = (
            select(Service_Fees_Format)
            .where(Service_Fees_Format.service_fees_id == _Service_Fees.id)
            .order_by(
                Service_Fees_Format.priority,
            )
        )
        _row_service_fees_format = (await db.execute(_sql)).all()
        if not _row_service_fees_format:
            return {"success": False, "msg": f"Service_Fees_Format not found"}

        in_time = _Log_Transaction.date_time
        out_time = time_now()

        # print(_row_service_fees_format)
        # ? Check match acse
        service_fees_format = None
        _t_in = in_time.strftime("%H:%M")
        _t_out = out_time.strftime("%H:%M")
        print_success(f"time_in: {_t_in} <<>> Time_out : {_t_out}")
        for row in _row_service_fees_format:
            _s: Service_Fees_Format = row[0]
            if _s.condition_type == "default":
                service_fees_format = _s
                continue
            if _s.status.lower() == "disable":
                print("Service_Fee is disabled")
                continue
            _c_t0, _c_t1 = _s.condition.split("-")

            match _s.condition_type:
                case "PARKED_RANGE":
                    # **REVIEW - Check in time
                    if _c_t0 <= _t_in and _t_out <= _c_t1:
                        print(_c_t0, _c_t1)
                        print_success("Transaction_Record PARKED_RANGE")
                        service_fees_format = _s
                        break

                case "IN_RANGE":
                    # **REVIEW - Check in time
                    if _c_t0 <= _t_in and _t_in <= _c_t1:
                        print(_c_t0, _c_t1)
                        print_success("Transaction_Record IN_RANGE")
                        service_fees_format = _s
                        break

                case "OUT_RANGE":
                    # **REVIEW - Check in time
                    if _c_t0 <= _t_out and _t_out <= _c_t1:
                        print(_c_t0, _c_t1)
                        print_success("Transaction_Record OUT_RANGE")
                        service_fees_format = _s
                        break

                case _:
                    print_error(f"{_s.condition_type} not matching")
            if not service_fees_format:
                return {"success": False, "msg": f"service_fees_format:card not found"}

        round = _Service_Fees.round
        parked, amount, log = calculate_services_fee(
            calculate_list=service_fees_format.calculate_list,
            in_time=in_time,
            out_time=out_time,
            round=round,
        )

        _acc = {"amount": amount, "parked": parked, "service_fees_format": service_fees_format.name}
        _data = {"transactions": _row, "acc": _acc}
        # print(_data)

        return {"success": True, "data": _data, "msg": msg}

    else:
        return {"success": False, "msg": f"ไม่พบการทำรายการเข้า !"}


async def check_out_post(
    db: AsyncSession,
    user: System_User,
    transaction_records_id: str,
    amount: int,
    pay: int,
    turn_amount: int,
    gateway_id: int,
    card_id: str,
    license: str = "",
    pay_type: str = "CASH",
    image_upload_01: Image = None,
    image_upload_02: Image = None,
):
    _now = time_now()

    _sql = (
        select(Transaction_Record, Log_Transaction)
        .where(Transaction_Record.id == transaction_records_id)
        .join(Log_Transaction, (Log_Transaction.id == Transaction_Record.log_in))
    )
    _row = (await db.execute(_sql)).one_or_none()
    if _row:
        _Transaction_Record: Transaction_Record = _row[0]
        _Log_Transaction_in: Log_Transaction = _row[1]
        _Log_Transaction = Log_Transaction(
            card_id=_Transaction_Record.card_id,
            license=license,
            create_id=user.id,
            gateway_id=gateway_id,
            type="OUT",
            date_time=_now,
        )
        db.add(_Log_Transaction)
        await db.commit()
        await db.refresh(_Log_Transaction)

        # **SECTION - มีค่าบริการ
        if amount:
            print(transaction_records_id, amount, pay, turn_amount)
            tex_date = _now.strftime("%Y%m%d")
            tex_no = f"EXT{tex_date}-{_Transaction_Record.id}"
            _Account_Record = Account_Record(
                create_id=user.id,
                transaction_record_id=_Transaction_Record.id,
                date_time=_now,
                amount=amount,
                pay=pay,
                no=tex_no,
                type=pay_type,
            )
            db.add(_Account_Record)
            await db.commit()
            await db.refresh(_Account_Record)

        images_path_list = []
        if image_upload_01:
            try:
                file_path = f"./static/data_base/image/Log_Transaction/{_Log_Transaction.id//1000}"
                file_name = f"{_Log_Transaction.id}_01"
                img_success = save_image_file(image_upload_01, file_path, file_name)
                if img_success:
                    images_path_list.append(img_success[1:])
            except Exception as e:
                print_error(e)

        if image_upload_02:
            try:
                file_path = f"./static/data_base/image/Log_Transaction/{_Log_Transaction.id//1000}"
                file_name = f"{_Log_Transaction.id}_02"
                img_success = save_image_file(image_upload_02, file_path, file_name)
                if img_success:
                    images_path_list.append(img_success[1:])
            except Exception as e:
                print_error(e)

        images_path = ",".join(images_path_list)
        _Log_Transaction.images_path = images_path
        _Transaction_Record.log_out = _Log_Transaction.id
        _now_tz = _now.replace(tzinfo=None)
        parked: timedelta = _now_tz - _Log_Transaction_in.date_time
        _Transaction_Record.parked = parked.total_seconds()
        _Transaction_Record.status = "SUCCESS"
        await db.commit()
        await db.refresh(_Log_Transaction)

        _sql = (
            select(GateWay, Parking_Lot)
            .where(GateWay.id == gateway_id)
            .join(
                Parking_Lot,
                Parking_Lot.id == GateWay.parking_id,
            )
        )
        _row = (await db.execute(_sql)).one_or_none()
        _Parking_Lot: Parking_Lot = _row[1]
        print(_Parking_Lot)
        value = _Parking_Lot.value - 1
        if value <= 0:
            value = 0
        _Parking_Lot.value = value
        await db.commit()

        ws_json = {"func": "parking_lot_info", "params": f"{_Parking_Lot.name},{_Parking_Lot.value}/{_Parking_Lot.limit}"}
        await WebSockets.broadcast(ws_json, sendMode="json")

        sql = select(Transaction_Record).where(Transaction_Record.card_id == _Transaction_Record.card_id, Transaction_Record.log_out == None)
        rows = (await db.execute(_sql)).all()

        if rows:
            sql = (
                update(Transaction_Record)
                .where(Transaction_Record.card_id == _Transaction_Record.card_id, Transaction_Record.log_out == None)
                .values(
                    log_out=_Transaction_Record.log_out,
                    status=f"CLOSED (dupicated:{_Transaction_Record.id})",
                )
            )
            result = await db.execute(sql)
            await db.commit()
            print_success(f"update rows is dupicated :{result.rowcount}")

        return {"success": True, "data": (_Transaction_Record,)}

    else:
        return {"success": False, "msg": f"successfully:card not found"}
