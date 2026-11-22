"""One write per action, with automatic confirmation after connection loss."""
import asyncio
from contextlib import suppress
from datetime import timedelta
from hashlib import sha256
import logging
import re
from uuid import uuid4

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InvalidAuth, CannotConnect
from .const import DOMAIN, FINAL_OUTCOMES, KEY


CHECKING = {"outcome": "checking", "feedback": "Waiting for Inu to confirm the last action."}
UNCERTAIN = {"outcome": "uncertain", "feedback": "The last action is still being checked. Look in Inu if you need the answer now."}


class InuCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN,
                         update_interval=timedelta(minutes=5))
        self.entry, self.client = entry, client
        self.store = Store(hass, 1, DOMAIN + ".pending." + entry.entry_id)
        self.pending = None
        self.legacy_pending = False
        self.connection = sha256(entry.data[KEY].encode()).hexdigest()
        self.result = {"outcome": "idle", "feedback": ""}
        self.lock = asyncio.Lock()
        self.sending = False
        self.recovery = None
        self.reauth = False
        self.stopping = False

    async def async_restore(self):
        saved = await self.store.async_load()
        if saved is None:
            return
        identifier = saved if isinstance(saved, str) else saved.get("id") if isinstance(saved, dict) else None
        if isinstance(identifier, str) and re.fullmatch(r"[a-f0-9]{32}", identifier):
            if isinstance(saved, str) or saved.get("connection") == self.connection:
                self.pending = identifier
                self.legacy_pending = isinstance(saved, str)
                self.result = CHECKING
                return
        # A new connection key cannot send the old action. Its previous outcome
        # may already be committed, so report that boundary without replaying it.
        await self.store.async_save(None)
        self.result = {"outcome": "unavailable", "feedback": "Check the last action in Inu before repeating it."}

    async def _async_update_data(self):
        try:
            info = await self.client.info()
            self.start_recovery()
            return info
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed("Reconnect Inu with a new connection key.") from error
        except CannotConnect as error:
            raise UpdateFailed("Inu is currently unavailable.") from error

    async def _accept(self, result):
        if result["outcome"] in FINAL_OUTCOMES:
            await self.store.async_save(None)
            self.pending = None
            self.legacy_pending = False
        self.result = result
        self.async_update_listeners()
        return result

    def _reauth(self):
        if not self.reauth:
            self.reauth = True
            self.entry.async_start_reauth(self.hass)

    async def _resolve_locked(self):
        try:
            if self.legacy_pending:
                reply = await self.client.receipt(self.pending)
                if reply["outcome"] in FINAL_OUTCOMES:
                    return reply
            reply = await self.client.resolve(self.pending)
            if self.legacy_pending and reply["outcome"] == "unavailable":
                # Old records lack their connection fingerprint. A missing
                # receipt after a key replacement cannot establish non-delivery.
                return {"outcome": "unavailable", "feedback": "Check the last action in Inu before repeating it."}
            return reply
        except InvalidAuth:
            self._reauth()
            return {"outcome": "uncertain", "feedback": "Reconnect Inu to check the last action."}
        except CannotConnect:
            return UNCERTAIN

    def start_recovery(self):
        if self.pending and not self.sending and not self.reauth and not self.stopping and not self.recovery:
            self.recovery = self.hass.async_create_background_task(self._recover(), "Inu confirm last action")

    async def _recover(self):
        try:
            for delay in (0, 3, 12):
                if delay:
                    await asyncio.sleep(delay)
                async with self.lock:
                    if not self.pending or self.reauth:
                        return
                    await self._accept(await self._resolve_locked())
                    if not self.pending or self.reauth:
                        return
        finally:
            self.recovery = None

    async def stop_recovery(self):
        self.stopping = True
        if task := self.recovery:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def async_complete(self, task_name):
        task_name = task_name.strip()
        if not task_name or len(task_name) > 490:
            raise HomeAssistantError("Enter one task name, up to 490 characters.")
        return await self.async_send("complete: " + task_name)

    async def async_notify(self, message):
        message = message.strip()
        if not message or len(message) > 320:
            raise HomeAssistantError("Enter a notification, up to 320 characters.")
        return await self.async_send("notify: " + message)

    async def async_send(self, message):
        message = message.strip()
        if not message or len(message) > 500:
            raise HomeAssistantError("Enter a message, up to 500 characters.")
        if self.lock.locked() or self.pending:
            self.start_recovery()
            raise HomeAssistantError("Inu is checking the last action. See Last result on the Inu device.")
        self.sending = True
        try:
            async with self.lock:
                pending = uuid4().hex
                # A command body or raw key is never persisted for recovery.
                await self.store.async_save({"id": pending, "connection": self.connection})
                self.pending = pending
                self.result = CHECKING
                self.async_update_listeners()
                try:
                    reply = await self.client.send(self.pending, message)
                except InvalidAuth:
                    self._reauth()
                    reply = {"outcome": "uncertain", "feedback": "Reconnect Inu to check the last action."}
                except CannotConnect:
                    reply = UNCERTAIN
                if reply["outcome"] == "uncertain" and not self.reauth:
                    reply = await self._resolve_locked()
                return await self._accept(reply)
        finally:
            self.sending = False
            self.start_recovery()
