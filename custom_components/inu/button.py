from homeassistant.components.button import ButtonEntity
from .entity import InuEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([InuButton(entry.runtime_data, key) for key in ("complete_task", "check_result", "mark_reviewed")])


class InuButton(InuEntity, ButtonEntity):
    _attr_icon = "mdi:check"

    @property
    def available(self):
        if self.coordinator.lock.locked():
            return False
        if self._attr_translation_key == "complete_task":
            return super().available and bool(self.coordinator.draft.strip()) and not self.coordinator.pending
        return bool(self.coordinator.pending)

    async def async_press(self):
        if self._attr_translation_key == "complete_task":
            await self.coordinator.async_complete(self.coordinator.draft)
        elif self._attr_translation_key == "check_result":
            await self.coordinator.async_check()
        else:
            await self.coordinator.async_reviewed()
