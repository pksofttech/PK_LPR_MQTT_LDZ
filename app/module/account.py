# *! SECTION  Module ACCOUNT_

import os
import sys
from ..stdio import *
from sqlalchemy.ext.asyncio import AsyncSession
import random


def calculate_services_fee(calculate_list: str, in_time: datetime, out_time: datetime, round: int) -> tuple[str, float, str]:

    try:

        time_delta = timedelta(seconds=int(out_time.timestamp() - in_time.timestamp()))
        total_minute = int(time_delta.total_seconds()) // 60
        hours = total_minute // 60
        minute = total_minute % 60
        if round > 0 and round < minute and hours > 0:
            hours += 1
            minute = 0
        print(total_minute, hours, minute)
        parked = str(time_delta)
        amount = 0
        log = f"เวลาจอด:{parked}<br>\n"
        log += f"ปัดเศษ:{round}<br>\n"
        log += f"เวลาจอดรวม:{hours}:{str(minute).zfill(2)}<br>----------------------------"
        if calculate_list:
            calculate = calculate_list.split(",")
            h = str(hours).zfill(4)
            m = str(minute).zfill(2)
            h_s = f"{h}:{m}"
            # print(f"amount = ", end="")
            factor_minute = 0
            _a = 0
            last_k_h_s = "0000:00"
            for c in sorted(calculate):
                k, v = c.split("=")
                _k, _m = k.split(":")
                k_h_s = f"{_k.zfill(4)}:{_m}"
                if h_s >= k_h_s:
                    _factor_minute = factor_minute
                    if "@" in v:
                        v, f = v.split("@")
                        factor_minute = int(f)
                    else:
                        factor_minute = 0
                    if _factor_minute:
                        _t0 = timedelta(hours=int(_k), minutes=int(_m))
                        _t1 = timedelta(hours=int(last_k_h_s.split(":")[0]), minutes=int(last_k_h_s.split(":")[1]))
                        diff_minute = (_t0 - _t1).total_seconds() // 60
                        print(diff_minute, _t0, _t1)
                        _factor_count = diff_minute // _factor_minute
                        if _factor_count:
                            _l = f"<br>\n{last_k_h_s} : {_factor_count} * {_a} = {_factor_count * _a}"
                            print_success(_l)
                            log += _l

                            amount += _factor_count * _a
                    if v.startswith("+"):
                        _a = int(v[1:])
                        amount += _a
                        log += f"<br>\n{k_h_s} : amount += {_a}"
                        # print(v, end="")
                        print(v)
                    else:
                        _a = int(v)
                        amount = _a
                        log += f"<br>\n{k_h_s} : amount := {_a}"

                        # print(v, end="")
                        print(v)

                last_k_h_s = k_h_s

            if h_s >= last_k_h_s and factor_minute:
                _k, _m = h_s.split(":")
                _t0 = timedelta(hours=int(_k), minutes=int(_m))
                _t1 = timedelta(hours=int(last_k_h_s.split(":")[0]), minutes=int(last_k_h_s.split(":")[1]))
                diff_minute = (_t0 - _t1).total_seconds() // 60
                print(diff_minute, _t0, _t1)
                _factor_count = diff_minute // factor_minute
                if _factor_count:
                    amount += _factor_count * _a
                    _l = f"<br>\n{diff_minute}/{factor_minute}:({_factor_count} * {_a} = {_factor_count * _a})"
                    print_success(_l)
                    log += _l

            print_success(h_s, last_k_h_s)

            print(f" >> Total amount = {amount}")
            log += f"<br>\n Total amount = {amount}"
        else:
            print_warning("Not calculate_list")
        # num = random.random()
        # amount = int(num * 1000)
        return (parked, amount, log)
    except Exception as e:
        print_error(f"Error calculating {e}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print_error(exc_type, fname, exc_tb.tb_lineno)
        return (None, None, log)
