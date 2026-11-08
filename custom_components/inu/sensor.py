from homeassistant.components.sensor import SensorEntity
from .entity import InuEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([InuResult(entry.runtime_data, "task_result")])


class InuResult(InuEntity, SensorEntity):
    _attr_icon = "mdi:information-outline"
    _unrecorded_attributes = frozenset({"feedback"})

    @property
    def native_value(self):
        return self.coordinator.result["outcome"]

    @property
    def extra_state_attributes(self):
        return {"feedback": self.coordinator.result["feedback"]}
