"""Switches: auto show and sync"""
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DirtyLedsConfigEntry
from .coordinator import DirtyLedsCoordinator
from .entity import DirtyLedsEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DirtyLedsConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([
        ServerSwitch(coordinator, "autoShow", "auto-show", "Auto show", "mdi:auto-fix"),
        ServerSwitch(coordinator, "sync", "set-sync", "Sync strips", "mdi:link-variant", EntityCategory.CONFIG),
    ])


class ServerSwitch(DirtyLedsEntity, SwitchEntity):
    def __init__(
        self,
        coordinator: DirtyLedsCoordinator,
        state_key: str,
        action: str,
        name: str,
        icon: str,
        category: EntityCategory | None = None,
    ) -> None:
        super().__init__(coordinator, state_key)
        self._state_key = state_key
        self._action = action
        self._attr_name = name
        self._attr_icon = icon
        self._attr_entity_category = category

    @property
    def is_on(self) -> bool:
        return self.coordinator.data[self._state_key]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.action(self._action, {"value": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.action(self._action, {"value": False})
