"""UI-only setup and reauthentication."""
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from .api import InuClient, InvalidAuth, CannotConnect
from .const import DOMAIN, KEY

SCHEMA = vol.Schema({vol.Required(KEY): selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))})


class InuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, data):
        key = data[KEY].strip()
        if not re.fullmatch(r"inu_ha_[a-zA-Z0-9_-]{1,64}\.[a-zA-Z0-9_-]{43}", key):
            raise InvalidAuth
        info = await InuClient(async_get_clientsession(self.hass), key).info()
        return key, info

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                key, info = await self._validate(user_input)
                await self.async_set_unique_id(info["connection_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Inu", data={KEY: key})
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                key, info = await self._validate(user_input)
                entry = self._get_reauth_entry()
                if info["connection_id"] != entry.unique_id:
                    errors["base"] = "wrong_account"
                else:
                    return self.async_update_reload_and_abort(entry, data_updates={KEY: key})
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="reauth_confirm", data_schema=SCHEMA, errors=errors)
