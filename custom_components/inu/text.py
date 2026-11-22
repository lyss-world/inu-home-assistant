from homeassistant.components.text import TextEntity, TextMode
from homeassistant.exceptions import HomeAssistantError
from .entity import InuEntity


async def async_setup_entry(hass, entry, async_add_entities):
    hub = entry.runtime_data
    entities = []
    if "complete_tasks" in hub.data["scopes"]:
        entities.append(InuInput(hub, "complete_task_name", hub.async_complete, "mdi:checkbox-marked-circle-outline"))
    if "send_notifications" in hub.data["scopes"]:
        entities.append(InuInput(hub, "send_notification_message", hub.async_notify, "mdi:message-arrow-right-outline"))
    # Keep existing automations and dashboards that use text.set_value.
    entities.append(InuInput(hub, "task_name", hub.async_send, "mdi:message-text-outline", legacy=True))
    async_add_entities(entities)


class InuInput(InuEntity, TextEntity):
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_mode = TextMode.TEXT

    def __init__(self, coordinator, key, submit, icon, *, legacy=False):
        super().__init__(coordinator, key)
        self._submit = submit
        self._attr_icon = icon
        self._attr_entity_registry_visible_default = not legacy

    @property
    def native_value(self):
        # Commands are one-shot. Never let the Recorder restore a draft.
        return ""

    async def async_set_value(self, value):
        if not value.strip():
            return
        result = await self._submit(value)
        self.async_write_ha_state()
        if result["outcome"] not in {"completed", "already_completed", "queued"}:
            raise HomeAssistantError(result["feedback"])
