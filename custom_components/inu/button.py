from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from .entity import InuEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([InuButton(entry.runtime_data, key) for key in ("check_result", "mark_reviewed")])


class InuButton(InuEntity, ButtonEntity):
    _attr_icon = "mdi:check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self):
        if self.coordinator.lock.locked():
            return False
        return bool(self.coordinator.pending)

    async def async_press(self):
        if self._attr_translation_key == "check_result":
            await self.coordinator.async_check()
        else:
            await self.coordinator.async_reviewed()
