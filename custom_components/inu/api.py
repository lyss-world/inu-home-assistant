"""Small fixed-origin HTTP client. Writes have no automatic retries."""
import json
import re
import asyncio
import aiohttp
from .const import BASE_URL, FINAL_OUTCOMES


class InvalidAuth(Exception):
    """The limited Inu connection needs to be renewed."""


class CannotConnect(Exception):
    """A response cannot be trusted or was not received."""


class InuClient:
    def __init__(self, session: aiohttp.ClientSession, key: str):
        self.session = session
        self._key = key

    async def _request(self, method, path, **kwargs):
        try:
            async with self.session.request(method, BASE_URL + path,
                    headers={"Authorization": "Bearer " + self._key},
                    allow_redirects=False, timeout=aiohttp.ClientTimeout(total=30), **kwargs) as response:
                if response.status in (401, 403):
                    raise InvalidAuth
                if response.status != 200:
                    raise CannotConnect
                raw = bytearray()
                async for chunk in response.content.iter_chunked(8192):
                    raw.extend(chunk)
                    if len(raw) > 65536:
                        raise CannotConnect
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise CannotConnect
                return value
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            raise CannotConnect from error

    async def info(self):
        value = await self._request("GET", "/info")
        if (not isinstance(value.get("connection_id"), str)
                or not re.fullmatch(r"[a-f0-9]{32}", value["connection_id"])
                or not isinstance(value.get("scopes"), list)
                or not set(value.get("scopes", [])) & {"complete_tasks", "send_notifications"}):
            raise CannotConnect
        return value

    async def send(self, request_id, message):
        # Preserve the user's command verbatim; the cloud owns interpretation.
        return self._result(await self._request("POST", "/commands", json={
            "request_id": request_id, "text": message}))

    async def complete(self, request_id, task_name):
        # Compatibility for existing automations, not the primary UI.
        return await self.send(request_id, task_name + " abhaken")

    async def receipt(self, request_id):
        if not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise CannotConnect
        return self._result(await self._request("GET", "/requests/" + request_id))

    @staticmethod
    def _result(value):
        if value.get("outcome") not in FINAL_OUTCOMES | {"uncertain"} or not isinstance(value.get("feedback"), str):
            raise CannotConnect
        return {"outcome": value["outcome"], "feedback": value["feedback"][:500]}
