from homeassistant.components.text import TextEntity, TextMode
from .entity import InuEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([InuTaskName(entry.runtime_data, "task_name")])


class InuTaskName(InuEntity, TextEntity):
    _attr_native_min = 0
    _attr_native_max = 120
    _attr_mode = TextMode.TEXT
    _attr_icon = "mdi:checkbox-marked-outline"

    @property
    def native_value(self):
        return self.coordinator.draft

    async def async_set_value(self, value):
        self.coordinator.draft = value[:120]
        self.async_write_ha_state()
