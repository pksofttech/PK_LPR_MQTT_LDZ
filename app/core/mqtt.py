import json
import random
import string
import time
from fastapi_mqtt import FastMQTT, MQTTConfig

from ..stdio import *
import httpx as requests

DEVICE_ID = "JT_LPR_TEST"
PUBLISH = f"/smart_parking/sub/JT_LPR_TEST"
SUBSCRIBE = f"/smart_parking/pub/JT_LPR_TEST"

_mqtt_host = "mqtt-dashboard.com"
# _mqtt_host = "stpk-bfs-03003.laz.ipa"


# _mqtt_host = "mqtt.dollysolutions.com"
_mqtt_port = 8883
fast_mqtt = FastMQTT(
    # client_id="localhost_test",
    config=MQTTConfig(
        host=_mqtt_host,
        ssl=True,
        # username="",
        # password="",
        # keepalive=600,
        port=_mqtt_port,
    ),
)


def _random_string(length) -> str:
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    # print("Random string of length", length, "is:", result_str)
    return result_str


traceId = _random_string(10)


@fast_mqtt.on_connect()
def connect(client, flags, rc, properties):
    fast_mqtt.client.subscribe(f"{SUBSCRIBE}")
    # fast_mqtt.client.subscribe("/getmoney/#")
    # fast_mqtt.client.subscribe("/heartbeat/#")
    # fast_mqtt.client.subscribe("/stats/#")
    print_success("Connected: ", flags, rc, properties)


_examples_mqtt = {
    "api": {"code": "0", "message": "Please open the gate. Vehicle is assigned into WA 0001"},
    "gate": {"command": "OPEN", "name": "Gate 1"},
    "traceId": "1399c657-7665-4e24-994a-e6bfa4953a98",
    "vehicle": {"driverId": "23123", "plateNumber": "HGDJHFGK.KGJ", "vehicleType": "VAN"},
    "timestamp": 1689325135399,
}

"""{"api": {"code": "0", "message": "Please open the gate. Vehicle is assigned into WA 0001"},"gate": {"command": "OPEN", "name": "Gate 1"},"traceId": "1399c657-7665-4e24-994a-e6bfa4953a98","vehicle": {"driverId": "23123","plateNumber":"HGDJHFGK.KGJ","vehicleType":"VAN"},"timestamp": 1689325135399}"""


@fast_mqtt.on_message()
async def message(client, topic: str, payload, qos, properties):
    start_time = time.perf_counter()
    try:
        retain = properties.get("retain", 0)
        if retain:
            print_warning(f"Ignore Retain : is {topic}: {payload}")
            return 0
        mqtt_msg = payload.decode()
        json_msg = json.loads(mqtt_msg)

        print(json_msg)

    except Exception as e:
        print_error("Received message: ", topic, payload, "qos:", qos)
        print_error(e)

    end_time = time.perf_counter()
    total_time = (end_time - start_time) * 1000
    print(f"Function @fast_mqtt.on_message() Took {total_time:.4f} ms")


@fast_mqtt.on_disconnect()
def disconnect(client, packet, exc=None):
    print_warning(f"Disconnecting client:{client} packet {packet}")
    print_warning("Disconnected")


@fast_mqtt.on_subscribe()
def subscribe(client, mid, qos, properties):
    global traceId
    print_success("subscribed", client, mid, qos, properties)
    fast_mqtt.publish(PUBLISH, f"subscribed from lpr_mqtt_lzd successfully traceId:{traceId}")


async def lzd_vender_send(plateNumber: str, gate: str) -> bool:
    print("lzd_vender_send")
    global traceId
    try:
        traceId = _random_string(10)
        ts = str(time.time()).split(".")[0]
        data = {
            "tenantId": "LAZADA_TH",
            "nodeId": "SORTATION_20048751",
            "plateNumber": plateNumber,
            "deviceId": DEVICE_ID,
            "traceId": traceId,
            "timestamp": ts,
            "gate": gate,
        }
        msg_json = json.dumps(data)
        fast_mqtt.publish(PUBLISH, msg_json)
        return True
    except Exception as e:
        print_error(e)
        return False


print_success("Set MQTT MODULE IN FASTAPI")
