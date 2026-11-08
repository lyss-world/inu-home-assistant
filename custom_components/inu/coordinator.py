"""One bounded status read; durable uncertainty, no command replay."""
import asyncio
import logging
import re
from datetime import timedelta
from uuid import uuid4
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import InvalidAuth, CannotConnect
from .const import DOMAIN, FINAL_OUTCOMES


class InuCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN,
                         update_interval=timedelta(minutes=5))
        self.entry, self.client = entry, client
        self.store = Store(hass, 1, DOMAIN + ".pending." + entry.entry_id)
        self.pending = None
        self.draft = ""
        self.result = {"outcome": "idle", "feedback": ""}
        self.lock = asyncio.Lock()

    async def async_restore(self):
        self.pending = await self.store.async_load()
        if self.pending and (not isinstance(self.pending, str) or not re.fullmatch(r"[a-f0-9]{32}", self.pending)):
            self.pending = "invalid"
        if self.pending:
            self.result = {"outcome": "uncertain", "feedback": "Check the previous result before sending another message."}

    async def _async_update_data(self):
        try:
            return await self.client.info()
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed("Reconnect Inu with a new connection key.") from error
        except CannotConnect as error:
            raise UpdateFailed("Inu is currently unavailable.") from error

    async def _accept(self, result):
        self.result = result
        if result["outcome"] in FINAL_OUTCOMES:
            await self.store.async_save(None)
            self.pending = None
        self.hass.loop.call_soon(self.async_update_listeners)
        return result

    async def async_complete(self, task_name):
        task_name = task_name.strip()
        if not task_name or len(task_name) > 490:
            raise HomeAssistantError("Enter one task name, up to 490 characters.")
        return await self.async_send(task_name + " abhaken")

    async def async_send(self, message):
        message = message.strip()
        if not message or len(message) > 500:
            raise HomeAssistantError("Enter a message, up to 500 characters.")
        if self.lock.locked() or self.pending:
            raise HomeAssistantError("Check the previous result or mark it reviewed before sending another message.")
        async with self.lock:
            self.pending = uuid4().hex
            # Save only the receipt ID, never task text or credentials, before network I/O.
            await self.store.async_save(self.pending)
            self.result = {"outcome": "checking", "feedback": ""}
            self.async_update_listeners()
            try:
                result = await self.client.send(self.pending, message)
            except InvalidAuth:
                self.entry.async_start_reauth(self.hass)
                result = {"outcome": "uncertain", "feedback": "Reconnect Inu, then check the previous result."}
            except CannotConnect:
                result = {"outcome": "uncertain", "feedback": "Not confirmed. Check the result; do not send the message again."}
            finally:
                self.async_update_listeners()
            return await self._accept(result)

    async def async_check(self):
        if self.lock.locked() or not self.pending:
            return self.result
        async with self.lock:
            try:
                result = await self.client.receipt(self.pending)
            except InvalidAuth:
                self.entry.async_start_reauth(self.hass)
                raise HomeAssistantError("Reconnect Inu, then check the result.") from None
            except CannotConnect:
                raise HomeAssistantError("Could not check the result. Try checking again.") from None
            return await self._accept(result)

    async def async_reviewed(self):
        if self.lock.locked():
            raise HomeAssistantError("Wait for the current action.")
        await self.store.async_save(None)
        self.pending = None
        self.result = {"outcome": "idle", "feedback": ""}
        self.async_update_listeners()
