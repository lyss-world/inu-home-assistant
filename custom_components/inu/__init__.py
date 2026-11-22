"""Native Home Assistant integration; no YAML, broker or MCP required."""
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import InuClient
from .const import DOMAIN, KEY, PLATFORMS
from .coordinator import InuCoordinator


async def async_setup_entry(hass, entry):
    coordinator = InuCoordinator(hass, entry, InuClient(async_get_clientsession(hass), entry.data[KEY]))
    await coordinator.async_restore()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    registry = entity_registry.async_get(hass)
    legacy_buttons = {"complete_task", "check_result", "mark_reviewed"}
    for entity in entity_registry.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform != DOMAIN:
            continue
        if entity.domain == "button" and any(entity.unique_id == entry.unique_id + "_" + key for key in legacy_buttons):
            registry.async_remove(entity.entity_id)
        elif entity.unique_id == entry.unique_id + "_task_name" and entity.hidden_by is None and entity.name is None:
            registry.async_update_entity(entity.entity_id, hidden_by=entity_registry.RegistryEntryHider.INTEGRATION)
    coordinator.start_recovery()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not hass.services.has_service(DOMAIN, "send_message"):
        async def send(call):
            entries = [e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e, "runtime_data", None)]
            if selected := call.data.get("config_entry_id"):
                entries = [e for e in entries if e.entry_id == selected]
            if len(entries) != 1:
                raise HomeAssistantError("Choose one connected Inu account.")
            result = await entries[0].runtime_data.async_send(call.data["message"])
            if result["outcome"] not in {"completed", "already_completed", "queued"}:
                raise HomeAssistantError(result["feedback"])
            return result
        hass.services.async_register(DOMAIN, "send_message", send,
            schema=vol.Schema({vol.Required("message"): vol.All(str, vol.Length(min=1, max=500)),
                               vol.Optional("config_entry_id"): str}), supports_response=SupportsResponse.OPTIONAL)
    if not hass.services.has_service(DOMAIN, "complete_task"):
        async def complete(call):
            entries = [e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e, "runtime_data", None)]
            if selected := call.data.get("config_entry_id"):
                entries = [e for e in entries if e.entry_id == selected]
            if len(entries) != 1:
                raise HomeAssistantError("Choose one connected Inu account.")
            result = await entries[0].runtime_data.async_complete(call.data["task_name"])
            if result["outcome"] not in {"completed", "already_completed"}:
                raise HomeAssistantError(result["feedback"])
            return result
        hass.services.async_register(DOMAIN, "complete_task", complete,
            schema=vol.Schema({vol.Required("task_name"): vol.All(str, vol.Length(min=1, max=490)),
                               vol.Optional("config_entry_id"): str}), supports_response=SupportsResponse.OPTIONAL)
    if not hass.services.has_service(DOMAIN, "send_notification"):
        async def notify(call):
            entries = [e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e, "runtime_data", None)]
            if selected := call.data.get("config_entry_id"):
                entries = [e for e in entries if e.entry_id == selected]
            if len(entries) != 1:
                raise HomeAssistantError("Choose one connected Inu account.")
            result = await entries[0].runtime_data.async_send("notify: " + call.data["message"])
            if result["outcome"] != "queued":
                raise HomeAssistantError(result["feedback"])
            return result
        hass.services.async_register(DOMAIN, "send_notification", notify,
            schema=vol.Schema({vol.Required("message"): vol.All(str, vol.Length(min=1, max=320)),
                               vol.Optional("config_entry_id"): str}), supports_response=SupportsResponse.OPTIONAL)
    return True


async def async_unload_entry(hass, entry):
    coordinator = entry.runtime_data
    if coordinator.sending:
        return False
    await coordinator.stop_recovery()
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator.stopping = False
        coordinator.start_recovery()
        return False

    entry.runtime_data = None
    if not any(getattr(e, "runtime_data", None) for e in hass.config_entries.async_entries(DOMAIN)):
        for service in ("complete_task", "send_message", "send_notification"):
            hass.services.async_remove(DOMAIN, service)
    return True
