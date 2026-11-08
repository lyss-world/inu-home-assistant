from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


class InuEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.entry.unique_id + "_" + key
        self._attr_translation_key = key
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.entry.unique_id)},
                                  "name": "Inu", "manufacturer": "Inu", "model": "Cloud connection"}
