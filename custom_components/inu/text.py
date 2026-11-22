from homeassistant.components.text import TextEntity, TextMode
from .entity import InuEntity


async def async_setup_entry(hass, entry, async_add_entities):
    # Keep the old unique key so existing dashboards still find the input.
    async_add_entities([InuMessage(entry.runtime_data, "task_name")])


class InuMessage(InuEntity, TextEntity):
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_mode = TextMode.TEXT
    _attr_icon = "mdi:message-arrow-right-outline"

    @property
    def native_value(self):
        # Neither recorder nor restart may restore/replay a command draft.
        return ""

    async def async_set_value(self, value):
        if not value.strip():
            return
        await self.coordinator.async_send(value)
        self.async_write_ha_state()
