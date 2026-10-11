"""Base entities: one device for the server, one per strip"""
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DirtyLedsCoordinator


def server_device_info(coordinator: DirtyLedsCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.unique_id)},
        name="Dirty LEDs",
        manufacturer="dirty-leds",
        model="Music reactive LED server",
        configuration_url=coordinator.client.base_url,
    )


def _via_server(coordinator: DirtyLedsCoordinator) -> dict:
    # Home Assistant 2026.9 links devices by id and rejects via_device
    if "via_device_id" in DeviceInfo.__annotations__:
        return {"via_device_id": coordinator.server_device_id}
    return {"via_device": (DOMAIN, coordinator.config_entry.unique_id)}


class DirtyLedsEntity(CoordinatorEntity[DirtyLedsCoordinator]):
    """Belongs to the server itself: brightness, auto show, audio..."""
    _attr_has_entity_name = True

    def __init__(self, coordinator: DirtyLedsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}-{key}"
        self._attr_device_info = server_device_info(coordinator)


class DirtyLedsStripEntity(CoordinatorEntity[DirtyLedsCoordinator]):
    """Belongs to one LED strip (an ESP8266)"""
    _attr_has_entity_name = True

    def __init__(self, coordinator: DirtyLedsCoordinator, strip: str, key: str) -> None:
        super().__init__(coordinator)
        server_id = coordinator.config_entry.unique_id
        self.strip = strip
        self._attr_unique_id = f"{server_id}-{strip}-{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{server_id}-{strip}")},
            name=strip,
            manufacturer="dirty-leds",
            model="ESP8266 LED strip",
            **_via_server(coordinator),
        )

    @property
    def strip_state(self) -> dict | None:
        return self.coordinator.device(self.strip)

    def effect_state(self, effect: str) -> dict | None:
        return next((item for item in self.strip_state["effects"] if item["name"] == effect), None)

    @property
    def available(self) -> bool:
        # A strip removed from config.json disappears from the state
        return super().available and self.strip_state is not None
