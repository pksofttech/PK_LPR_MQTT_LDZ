import logging
import random
from typing import AsyncIterator
from typing import AsyncGenerator
from .utility import get_password_hash
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import aliased

from ..stdio import *
import urllib
import logging
import logging.handlers

from fastapi import Depends
from sqlmodel import SQLModel, delete, func, insert, text, update
from .models import *

# from app.core import models

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core import config


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///sqlacm.db"
# ? connect_args={"check_same_thread": False} For Sqlite เท่านั้น
async_engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

data_base_ip = "localhost"
data_base_name = "dpark_vms"
data_base_password = "dls@1234"

print("Connect DataBase")
_password = urllib.parse.quote_plus(data_base_password)
# SQLALCHEMY_DATABASE_URL = f"mssql+pymssql://sa:{_password}@{data_base_ip}/{data_base_name}?charset=utf8"
# engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=20, max_overflow=0)

# For postgres DB
postgres_server = "localhost"
postgres_database = "database"
_password = urllib.parse.quote_plus("#bunpotnumnak24")
# SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://root:{_password}@{postgres_server}/{postgres_database}"
# async_engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# ? MAIN LIB+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

_async_session_maker = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncSession:
    async with _async_session_maker() as session:
        yield session


async def set_databases(max=1000):
    # Generet database test
    from faker import Faker

    SLIP_OUT = """<div class="w-full max-w-md p-4 bg-white border border-black rounded-lg">
<div class="flex items-center justify-center gap-4">
<img class="w-16 h-16 rounded-full" src="/static/data_base/image/app_configurations/app_configurations_image.jpg">
    <h5 class="text-xl font-bold leading-none text-black">PKS@PARKING</h5>
    </div>
<div class="flow-root text-black">
<ul role="list" >

<li class="py-2"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">หมายเลขรายการ</p>
<p class="text-sm truncate">Transaction Number</p></div>
<div class="inline-flex items-center text-base font-semibold ">[transaction_id]</div></div></li>

<li class="py-2"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">หมายเลขบัตร</p>
<p class="text-sm truncate">card Number</p></div>
<div class="inline-flex items-center text-base font-semibold ">[card_id]</div></div></li>

<li class="py-2"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">เวลาเข้า</p></div>
<div class="inline-flex items-center text-base font-semibold ">[in_time]</div></div></li>

<li class="py-3 sm:py-4"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">เวลาออก</p></div>
<div class="inline-flex items-center text-base font-semibold ">[out_time]</div></div></li>

<li class="py-2"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">เวลาจอด</p></div>
<div class="inline-flex items-center text-base font-semibold ">[parked]</div></div></li>

<li class="py-2"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">รับเงิน</p></div>
<div class="inline-flex items-center text-base font-semibold ">[pay]</div></div></li>

<li class="py-2"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">ค่าบริการ</p></div>
<div class="inline-flex items-center text-base font-semibold ">[amount]</div></div></li>

<li class="py-2"> <div class="flex items-center space-x-4"> <div class="flex-1 min-w-0"> <p class="text-sm font-medium truncate">เงินทอน</p></div>
<div class="inline-flex items-center text-base font-semibold ">[trun]</div></div></li>

</ul>
<div class="font-bold text-center text-md ">[service_fee]</div>
<div class="font-bold text-center text-md ">***ขอบคุณ***</div>
</div>
</div>"""

    HEADER_REPORT = """<div class="flex justify-around">
  <div class="p-4 my-auto">  <img class="w-20 h-20" src="/static/data_base/image/app_configurations/app_configurations_image.jpg"></div>
  <div class="flex flex-col items-center justify-center w-full gap-4">
      <div class="text-lg">[title]</div>
     <div class="">[header]</div>
 <div class="">[sub_header]</div>
 <div class="">[date_time]</div>
</div>
</div>"""

    FOOTER_REPORT = """  <div class="flex items-center justify-center gap-4">
 <img class="w-20 h-20" src="/static/data_base/image/app_configurations/app_configurations_image.jpg">
  <h5 class="text-xl font-bold leading-none text-gray-900 dark:text-white">PKS@PARKING</h5>
   </div>
<div class="px-8">ออกรายงานโดย [name]</div>"""
    app_configurations_init = {
        "app_configurations_name": "Demo",
        "app_configurations_address": "Demo Address",
        "app_configurations_phone": "01-234-5678",
        "app_configurations_vat_no": "00-xxxxxxxx-00",
        "app_configurations_remark": "ตัวอย่าง",
        "app_configurations_image": "/static/image/logo.png",
        "app_configurations_allow_not_register_member": "Enable",
        "app_configurations_slip_out": SLIP_OUT,
        "app_configurations_header_report": HEADER_REPORT,
        "app_configurations_footer_report": FOOTER_REPORT,
    }

    print_success("********************************************************")
    print_success(f"Init_db config Time {time_now()}")

    async with async_engine.begin() as conn:
        pass

        await conn.run_sync(SQLModel.metadata.drop_all)

        await conn.run_sync(SQLModel.metadata.create_all)

    async with _async_session_maker() as db:
        fake = Faker(["th_TH"])
        for k, v in app_configurations_init.items():
            _item = App_Configurations(key=k, value=v)
            print_success(k)
            db.add(_item)
        await db.commit()

        for l in ["USER_02", "USER_01", "OPERATOR", "ADMIN", "ROOT"]:
            _system_user_type = System_User_Type(user_type=l)
            if l == "ROOT":
                _system_user_type.permission_allowed = "system_config,management_system_user,station_config"
            db.add(_system_user_type)
        await db.commit()
        sql = select(System_User).where(System_User.username == "root")
        _user = (await db.execute(sql)).one_or_none()
        if not _user:
            sql = select(System_User_Type.id).where(System_User_Type.user_type == "ROOT")
            _system_user_type_root: System_User_Type = (await db.execute(sql)).one_or_none()
            # print(_system_user_type_root.id)
            print_warning("DataBase is missing root user")
            print_warning("SystemUser root not found init_db() create new root")
            _password = get_password_hash("12341234")
            _root = System_User(
                name=fake.name(),
                username="root",
                password=_password,
                system_user_type_id=_system_user_type_root.id,
                create_by="init_db",
                status="Enable",
                pictureUrl="/static/data_base/image/default/system.png",
            )
            db.add(_root)

            sql = select(System_User_Type.id).where(System_User_Type.user_type == "ADMIN")
            _system_user_type_root: System_User_Type = (await db.execute(sql)).one_or_none()
            _admin = System_User(
                name=fake.name(),
                username="admin",
                password=_password,
                system_user_type_id=_system_user_type_root.id,
                create_by="init_db",
                status="Enable",
            )
            db.add(_admin)

            # fake = Faker(["th_TH", "en_US", "ja_JP"])

            temp_user_name = []
            for i in range(3):
                _n = fake.name()
                if _n not in temp_user_name:
                    temp_user_name.append(_n)
            for index, i in enumerate(temp_user_name):
                _user = System_User(
                    # username=f"user_0{index+1}",
                    username=f"{i}",
                    name=f"{i}",
                    password=_password,
                    system_user_type_id=(index % 3) + 1,
                    create_by="init_db",
                    status="Enable",
                    pictureUrl="/static/data_base/image/default/system.png",
                )
                db.add(_user)

            await db.commit()

        # **FIXME - *************************
        _p_001 = None
        _p_002 = None
        _now = time_now(0)
        _parking_lot = Parking_Lot(
            name="ลานจอด 001",
            detail="ลานจอด 001",
            limit=500,
            create_id=_root.id,
        )
        db.add(_parking_lot)
        await db.commit()
        await db.refresh(_parking_lot)
        _p_001 = _parking_lot.id
        _parking_lot = Parking_Lot(
            name="ลานจอด 002",
            detail="ลานจอด 002",
            limit=1000,
            create_id=_root.id,
        )
        db.add(_parking_lot)
        await db.commit()
        await db.refresh(_parking_lot)
        _p_002 = _parking_lot.id

        print(_parking_lot)
        _gateway_01 = GateWay(
            create_id=1,
            name="ทางเข้า 01",
            date_created=_now,
            type="IN",
            remark="Gateway For Test",
            images_path="/static/data_base/image/default/system.png",
            parking_id=_p_001,
            ip_cameras="https://loremflickr.com/320/240/car\nhttps://loremflickr.com/320/240/dog",
        )
        db.add(_gateway_01)
        _gateway_02 = GateWay(
            create_id=1,
            name="ทางเข้า 02",
            date_created=_now,
            type="IN",
            remark="Gateway For Test",
            images_path="/static/data_base/image/default/system.png",
            parking_id=_p_002,
        )
        db.add(_gateway_02)

        _gateway_11 = GateWay(
            create_id=1,
            name="ทางออก 01",
            date_created=_now,
            type="OUT",
            remark="Gateway For Test",
            images_path="/static/data_base/image/default/system.png",
            parking_id=_p_001,
            ip_cameras="https://loremflickr.com/320/240/car\nhttps://loremflickr.com/320/240/cat",
        )
        db.add(_gateway_11)

        _gateway_12 = GateWay(
            create_id=1,
            date_created=_now,
            name="ทางออก 02",
            type="OUT",
            remark="Gateway For Test",
            images_path="/static/data_base/image/default/system.png",
            parking_id=_p_002,
        )
        db.add(_gateway_12)
        await db.commit()

        await db.refresh(_gateway_01)
        await db.refresh(_gateway_02)
        await db.refresh(_gateway_11)
        await db.refresh(_gateway_12)

        _services_fees = Service_Fees(
            create_id=1,
            name="ค่าบริการ 001",
            remark="Test Fee 001",
        )
        db.add(_services_fees)
        await db.commit()
        await db.refresh(_services_fees)
        _services_fees_format = Service_Fees_Format(
            service_fees_id=_services_fees.id,
            name="ค่าบริการตั้งต้น",
            condition_type="default",
            calculate_list="00:00=+5,02:00=+5@60",
            primary=1,
        )
        db.add(_services_fees_format)
        await db.commit()
        _services_fees_format = Service_Fees_Format(
            service_fees_id=_services_fees.id,
            name="PARKED_RANGE",
            condition_type="PARKED_RANGE",
            calculate_list="00:10=+5,00:20=+5,00:30=+5,00:40=+5,00:50=+5,01:00=+5,02:00=+5@60",
            condition="08:00-22:00",
        )
        db.add(_services_fees_format)
        await db.commit()

        _services_fees = Service_Fees(
            create_id=1,
            name="ค่าบริการ 002",
            remark="Test Fee 002",
        )
        db.add(_services_fees)
        await db.commit()
        await db.refresh(_services_fees)
        _services_fees_format = Service_Fees_Format(
            service_fees_id=_services_fees.id,
            name="ค่าบริการตั้งต้น",
            condition_type="default",
            calculate_list="00:10=+5,00:20=+5,00:30=+5,00:40=+5,00:50=+5,01:00=+5,03:00=+5@60",
            primary=1,
        )
        db.add(_services_fees_format)
        _services_fees_format = Service_Fees_Format(
            service_fees_id=_services_fees.id,
            name="ค่าบริการกลางวัน",
            condition_type="PARKED_RANGE",
            calculate_list="00:10=+5,00:20=+5,00:30=+5,00:40=+5,00:50=+5,01:00=+5,01:10=+5@60",
            condition="08:00-22:00",
        )
        db.add(_services_fees_format)
        await db.commit()
        temp_member_count = 10
        temp_member_name = []
        for i in range(temp_member_count):
            _n = fake.name()
            if _n not in temp_member_name:
                temp_member_name.append(_n)
        for i in temp_member_name:
            _m = Member_User(create_id=1, name=i, remark="Member For Test")
            db.add(_m)
        await db.commit()

        _p_r = Permission_Role(name="วันทำการจ-ศ", create_id=1, remark="ใช้งานได้เฉพาะวัน จันทร์-ศุกร์")
        db.add(_p_r)

        _m_u_p_01 = Member_User_Permission(name="Member Class 1", create_id=1, limit=5, detail="Member Class 1")
        _m_u_p_02 = Member_User_Permission(name="Member Class 2", create_id=1, limit=3, detail="Member Class 2")
        db.add(_m_u_p_01)
        db.add(_m_u_p_02)
        await db.commit()
        _m_type = Member_Type(create_id=1, name="บัตรจอดรถ", amount=0, remark="บัตรจอดรถ คิดค่าบริการ", expire_day=1000)
        db.add(_m_type)
        # _m_type = Member_Type(create_id=1, name="รายวัน", amount=50, remark="ใช้ภายใน 1 วัน", expire_day=1, permission_role_id=1)
        # db.add(_m_type)
        _m_type = Member_Type(create_id=1, name="เหมา30วัน", amount=1000, remark="อายุบัตรเหมา 30วัน", expire_day=30)
        db.add(_m_type)
        _m_type = Member_Type(create_id=1, name="เหมา90วัน", amount=2500, remark="อายุบัตรเหมา 90วัน", expire_day=90)
        db.add(_m_type)
        # _m_type = Member_Type(create_id=1, name="เหมา180วัน", amount=5000, remark="อายุบัตรเหมา 180วัน", expire_day=180)
        # db.add(_m_type)

        await db.commit()

        temp_member_name = []
        for i in range(temp_member_count):
            _d_d = random.randint(0, 5)

            _m_u = random.randint(0, temp_member_count)
            if _m_u == 0:
                _m_u = None
            _t = random.randint(1, 3)
            _exp = 360
            if _t == 2:
                _exp = 30
            if _t == 3:
                _exp = 90

            if _d_d <= 1:
                _s_d = _now - timedelta(days=_d_d)
            else:
                _s_d = _now + timedelta(days=_d_d)

            _ex_d = _s_d + timedelta(days=_exp)
            # print(_s_d, _ex_d, (_ex_d - _s_d))
            _m = Member(
                create_date_time=_now,
                start_date_time=_s_d,
                expire_date_time=_ex_d,
                create_id=1,
                card_id=str(i),
                member_user_id=_m_u,
                member_type_id=_t,
                remark=f"Test for:{i}",
            )
            db.add(_m)
        await db.commit()
        _lpr_system_user = System_User(
            name=f"LPR System",
            username=f"LPR System",
            password="",
            system_user_type_id=1,
            create_by="init_db",
            status="Enable",
            pictureUrl="/static/image/p001.png",
        )
        db.add(_lpr_system_user)
        await db.commit()
        await db.refresh(_lpr_system_user)

        _lpr = Lpr_Camera(
            create_id=1,
            device_id="180300121847",
            device_ip="192.168.1.203",
            device_name="LPR001",
            device_model="XD01",
            gateway_id=_gateway_01.id,
            system_user_id=_lpr_system_user.id,
            service_fees_id=1,
        )
        db.add(_lpr)
        _lpr = Lpr_Camera(
            create_id=1,
            device_id="180300121754",
            device_ip="192.168.1.204",
            device_name="LPR002",
            device_model="XD01",
            gateway_id=_gateway_11.id,
            system_user_id=_lpr_system_user.id,
            service_fees_id=1,
        )
        db.add(_lpr)
        await db.commit()

        ess = ("ES001", "ES002", "ES003", "ES004", "ES005", "ES006", "ES007", "ES008", "ES009", "ES010")
        for es in ess:
            _Estamp_Device = Estamp_Device(
                create_id=1,
                device_id=f"SN-{es}",
                device_ip="",
                device_model="WEB",
                device_name=es,
                service_fees_ids="1,2",
                system_user_ids="1,2",
                images_path="/static/data_base/image/default/system.png",
                mode="TEST",
                type="WEB",
                status="ENABLE",
            )
            db.add(_Estamp_Device)
        await db.commit()

    if not max:
        return
    fake = Faker()

    async with _async_session_maker() as db:
        sql = delete(Transaction_Record)
        await db.execute(sql)
        sql = delete(Log_Transaction)
        await db.execute(sql)
        await db.commit()

        sql = select(GateWay.id).where(GateWay.type == "IN")
        GI = (await db.execute(sql)).all()

        sql = select(GateWay.id).where(GateWay.type != "IN")
        GO = (await db.execute(sql)).all()

        sql = select(System_User.id)
        S = (await db.execute(sql)).all()

        sql = select(Member.card_id)
        M = (await db.execute(sql)).all()

        sql = select(Service_Fees.id)
        SF = (await db.execute(sql)).all()
        for i in range(max):
            print(f" {str(i).zfill(4)}", end="")
            print("\b\b\b\b\b", end="")
            d0 = fake.date_time_between(start_date="-30d", end_date="now")

            m = random.choice(M)[0]
            sf = random.choice(SF)[0]
            s = random.choice(S)[0]
            gi = random.choice(GI)[0]
            go = random.choice(GO)[0]

            l = Log_Transaction(card_id=m, license=f"{s}", create_id=s, gateway_id=gi, date_time=d0)
            db.add(l)
            await db.commit()
            await db.refresh(l)
            t = Transaction_Record(card_id=m, create_id=s, service_fees_id=sf, remark=f"Test:{i}", log_in=l.id)
            db.add(t)

            out_success = random.randrange(10)
            if out_success > 5:
                parked = timedelta(hours=random.randint(0, 24), minutes=random.randint(0, 59))
                d1 = d0 + parked
                s = random.choice(S)[0]
                l = Log_Transaction(card_id=m, license=f"{i}", create_id=s, gateway_id=go, date_time=d1)
                db.add(l)
                await db.commit()
                await db.refresh(l)
                t.log_out = l.id
                t.parked = parked.total_seconds()
                t.status = "SUCCESS"
                amount = random.randint(0, 10)
                if amount > 3:
                    tex_date = d1.strftime("%Y%m%d")
                    tex_no = f"EXT{tex_date}-{t.id}"
                    amount = amount * 10
                    pay = random.randint(2, 10)
                    acc = Account_Record(
                        transaction_record_id=t.id,
                        create_id=s,
                        amount=amount,
                        pay=pay * 100,
                        no=tex_no,
                        date_time=d1,
                    )
                    db.add(acc)
                    await db.commit()
        print(".")
        await db.commit()

    print_success("********************* Success Set Data For Test ************************")


async def init_db():
    # return
    await set_databases(10)
    async with _async_session_maker() as db:
        pass
        # sql = "DROP TABLE Estamp_Device;"
        # result = await db.execute(sql)
        # sql = """
        # ALTER TABLE member_user
        #     ADD member_user_permission_id int;
        # """
        # result = await db.execute(sql)
        # print(result)

        # sql = "DROP TABLE Lpr_Log;"
        # result = await db.execute(sql)
    async with async_engine.begin() as conn:
        pass

        # await conn.run_sync(SQLModel.metadata.create_all)

    async with _async_session_maker() as db:
        # sql = """
        # ALTER TABLE member_user
        #     ADD member_user_permission_id int;
        # """
        # result = await db.execute(sql)
        # print(result)

        # sql = "DROP TABLE Estamp_Device;"
        # result = await db.execute(sql)

        # in_log: Log_Transaction = aliased(Log_Transaction)
        # out_log: Log_Transaction = aliased(Log_Transaction)

        # sql = (
        #     select(Transaction_Record, in_log, out_log)
        #     .where(Transaction_Record.id > 10000, Transaction_Record.log_out != None)
        #     .join(in_log, (Transaction_Record.log_in == in_log.id))
        #     .join(out_log, (Transaction_Record.log_out == out_log.id))
        # )
        # rows = (await db.execute(sql)).all()
        # for row in rows:
        #     _t: Transaction_Record = row[0]
        #     _li: Log_Transaction = row[1]
        #     _lo: Log_Transaction = row[2]
        #     p: timedelta = _lo.date_time - _li.date_time
        #     print(p)
        #     _t.parked = p.total_seconds()
        #     await db.commit()
        #     await db.refresh(_t)
        #     print(_t.card_id)

        # sql = select(Member_User)
        # Member_users = (await db.execute(sql)).all()

        # sql = select(Member)
        # rows = (await db.execute(sql)).all()
        # for row in rows:
        #     _m: Member = row[0]
        #     _mu: Member_User = random.choice(Member_users)[0]
        #     _m.member_user_id = _mu.id
        #     await db.commit()
        #     await db.refresh(_m)
        #     print(_mu.name)
        # _mup = Member_User_Permission(name="Test", create_id=1, detail="test", status="active")
        # db.add(_mup)
        # db.commit()

        sql = select(App_Configurations.value).where(App_Configurations.key == "app_configurations_allow_not_register_member")
        row = (await db.execute(sql)).one_or_none()
        if row:
            app_configurations_allow_not_register_member = row[0]
            if app_configurations_allow_not_register_member == "Enable":
                config.app_configurations_allow_not_register_member = True

        sql = (
            select(Parking_Lot.id, func.count(Transaction_Record.id))
            .where(Transaction_Record.log_out == None)
            .join(
                Log_Transaction,
                (Transaction_Record.log_in == Log_Transaction.id),
            )
            .join(
                GateWay,
                (Log_Transaction.gateway_id == GateWay.id),
            )
            .join(
                Parking_Lot,
                (GateWay.parking_id == Parking_Lot.id),
            )
            .group_by(
                Parking_Lot.id,
            )
        )
        rows = (await db.execute(sql)).all()
        for row in rows:
            # print(row)
            sql = update(Parking_Lot).where(Parking_Lot.id == row[0]).values(value=row[1])
            result = await db.execute(sql)
            await db.commit()
            # print_success(f"update rows is successful :{result.rowcount}")

        print_success("app_configurations_allow_not_register_member :", app_configurations_allow_not_register_member)
    return
