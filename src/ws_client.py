from __future__ import annotations

import asyncio
import json
import websockets


class WSKrakenOutMsg:
    def __init__(self, payload: str | dict) -> None:
        self.payload = (
            payload if type(payload) is str
            else json.dumps(payload)
        )

class WSKrakenInMsg:
    def __init__(self, payload: str) -> None:
        self.payload = json.loads(payload)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(payload={self.payload})"


class WSKrakenClient:
    def __init__(
        self,
        uri: str = "wss://ws.kraken.com"
    ) -> None:
        self.uri = uri

    async def send(self, msg: WSKrakenOutMsg) -> None:
        await self._raw_send(msg.payload)

    async def _raw_send(self, *args, **kwargs) -> None:
        await self.websocket.send(*args, **kwargs)

    async def recv(self) -> WSKrakenInMsg:
        return WSKrakenInMsg(await self._raw_recv())

    async def _raw_recv(self) -> str | bytes:
        return await self.websocket.recv()

    async def __aenter__(self) -> WSKrakenClient:
        self.websocket: websockets.WebSocketClientProtocol = (
            await websockets.connect(self.uri)
        )
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb) -> None:
        await self.websocket.close()

    async def ping(self):
        await self.send(WSKrakenOutMsg({
            "event": "ping"
        }))

    async def subscribe_ticker(self, pairs):
        await self.send(WSKrakenOutMsg({
            "event": "subscribe",
            "pair": pairs,
            "subscription": {
                "name": "ticker"
            }
        }))


if __name__ == "__main__":
    async def recv_msgs(websocket):
        async for msg in websocket:
            await handle_msg(WSKrakenInMsg(msg))

    async def handle_msg(msg):
        print(msg)

    async def main():
        async with WSKrakenClient() as client:
            recv_task = asyncio.create_task(recv_msgs(client.websocket))

            await client.ping()
            await client.subscribe_ticker(["LUNA/EUR"])

            await recv_task

    try:
        import uvloop
        uvloop.install()
    except ModuleNotFoundError:
        print("cannot import uvloop")

    asyncio.run(main())