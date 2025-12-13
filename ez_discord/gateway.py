# ez_discord/gateway.py

import asyncio
import aiohttp
import json
import logging
import sys

logger = logging.getLogger(__name__)

class GatewayClient:
    def __init__(self, http_client, token, intents):
        self.http = http_client
        self.token = token
        self.intents = intents
        self.ws = None
        self.heartbeat_interval = None
        self._last_sequence = None
        self._heartbeat_task = None

    async def connect(self):
        try:
            gateway_data = await self.http.get("/gateway/bot")
            gateway_url = gateway_data['url'] + "?v=10&encoding=json"

            self.ws = await self.http.session.ws_connect(gateway_url)
            logger.info("Connected to Gateway.")

            await self.listen()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to gateway: {e}")

    async def listen(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self.handle_message(json.loads(msg.data))
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                logger.warning(f"Gateway connection closed: {msg.data}")
                break

        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def handle_message(self, payload):
        op = payload['op']
        data = payload.get('d')
        sequence = payload.get('s')

        if sequence:
            self._last_sequence = sequence

        if op == 10:  # Hello
            self.heartbeat_interval = data['heartbeat_interval'] / 1000.0
            self._heartbeat_task = asyncio.create_task(self.heartbeat())
            await self.identify()
        elif op == 11:  # Heartbeat ACK
            logger.debug("Heartbeat ACK received.")
        elif op == 0:  # Dispatch
            logger.info(f"Received event: {payload['t']}")

    async def heartbeat(self):
        while not self.ws.closed:
            await asyncio.sleep(self.heartbeat_interval)
            await self.send_heartbeat()

    async def send_heartbeat(self):
        payload = {'op': 1, 'd': self._last_sequence}
        await self.ws.send_json(payload)
        logger.debug("Heartbeat sent.")

    async def identify(self):
        payload = {
            'op': 2,
            'd': {
                'token': self.token,
                'intents': self.intents,
                'properties': {
                    'os': sys.platform,
                    'browser': 'ez_discord',
                    'device': 'ez_discord'
                }
            }
        }
        await self.ws.send_json(payload)
        logger.info("Identify payload sent.")

    async def close(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self.ws and not self.ws.closed:
            await self.ws.close()
