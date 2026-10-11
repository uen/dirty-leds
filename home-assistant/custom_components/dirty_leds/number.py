"""Per strip tuning: minimum brightness and calm"""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DirtyLedsConfigEntry
from .coordinator import DirtyLedsCoordinator
from .entity import DirtyLedsStripEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DirtyLedsConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities = []
    for device in coordinator.data["devices"]:
        entities.append(StripPercent(coordinator, device["name"], "minBrightness", "set-min-brightness",
                                     "Minimum brightness", "mdi:brightness-4"))
        entities.append(StripPercent(coordinator, device["name"], "calm", "set-calm", "Calm", "mdi:waves"))
    async_add_entities(entities)


class StripPercent(DirtyLedsStripEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: DirtyLedsCoordinator, strip: str, state_key: str, action: str, name: str, icon: str
    ) -> None:
        super().__init__(coordinator, strip, state_key)
        self._state_key = state_key
        self._action = action
        self._attr_name = name
        self._attr_icon = icon

    @property
    def native_value(self) -> int:
        return self.strip_state[self._state_key]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.action(self._action, {"device": self.strip, "value": round(value)})
