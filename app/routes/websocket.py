import json
from ..stdio import *
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        websocket.subscribe = ""
        self.active_connections.append(websocket)
        print_success(f"WebSockets:Client connections form {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"WebSockets:    Client disconnect {websocket.client}")
        print(f"WebSockets:    Client active_connections : {len(self.active_connections)}")

    async def send_notification(self, subscribe: str, message: str):
        success = 0
        for websocket in self.active_connections:
            if websocket.subscribe == subscribe:
                await websocket.send_text(f"notification:{message}")
                success += 1

        return success

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_json(self, strjson: str, websocket: WebSocket):
        await websocket.send_json(strjson)

    async def broadcast(self, message: str, sendMode="text"):
        # print(self.active_connections)
        for connection in self.active_connections:
            if sendMode == "json":
                await connection.send_json(message)
            else:
                await connection.send_text(message)


WebSockets = ConnectionManager()
router = APIRouter()
# ! ******************************************************************************************************************************** #


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(websocket)
    await WebSockets.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # await WebSockets.broadcast(f"Client  broadcast: {data}")
            # await WebSockets.send_message(f"Connect to Server Success", websocket)
            # print(f"Send data to Client : {data}")

            # if websocket in WebSockets.active_connections:
            #     _json = json.loads(data)
            #     _subscribe = _json.get("subscribe", None)
            #     if _subscribe:
            #         websocket.subscribe = _subscribe
            #     print_success(WebSockets)
    except WebSocketDisconnect:
        WebSockets.disconnect(websocket)
        # await WebSockets.broadcast(f"Client #{websocket} disconnected")
