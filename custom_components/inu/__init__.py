"""Native Home Assistant integration; no YAML, broker or MCP required."""
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import InuClient
from .const import DOMAIN, KEY, PLATFORMS
from .coordinator import InuCoordinator


async def async_setup_entry(hass, entry):
    coordinator = InuCoordinator(hass, entry, InuClient(async_get_clientsession(hass), entry.data[KEY]))
    await coordinator.async_restore()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not hass.services.has_service(DOMAIN, "complete_task"):
        async def complete(call):
            entries = [e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e, "runtime_data", None)]
            if selected := call.data.get("config_entry_id"):
                entries = [e for e in entries if e.entry_id == selected]
            if len(entries) != 1:
                raise HomeAssistantError("Choose one connected Inu account.")
            return await entries[0].runtime_data.async_complete(call.data["task_name"])
        hass.services.async_register(DOMAIN, "complete_task", complete,
            schema=vol.Schema({vol.Required("task_name"): vol.All(str, vol.Length(min=1, max=490)),
                               vol.Optional("config_entry_id"): str}), supports_response=SupportsResponse.OPTIONAL)
    return True


async def async_unload_entry(hass, entry):
    if entry.runtime_data.lock.locked():
        return False
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        entry.runtime_data = None
        if not any(getattr(e, "runtime_data", None) for e in hass.config_entries.async_entries(DOMAIN)):
            hass.services.async_remove(DOMAIN, "complete_task")
    return result
