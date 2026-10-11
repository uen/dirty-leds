"""Sensors: the music as the server hears it"""
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DirtyLedsConfigEntry
from .coordinator import DirtyLedsCoordinator
from .const import DOMAIN
from .entity import DirtyLedsEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DirtyLedsConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        TempoSensor(coordinator),
        MeterSensor(coordinator, "intensity", "Intensity", "mdi:equalizer", enabled=True),
        MeterSensor(coordinator, "bass", "Bass", "mdi:speaker", enabled=False),
        MeterSensor(coordinator, "mid", "Mid", "mdi:speaker", enabled=False),
        MeterSensor(coordinator, "treble", "Treble", "mdi:speaker", enabled=False),
    ]
    async_add_entities(entities)
    # Each strip had a Showing sensor, which flooded the logbook while the auto show ran. It is
    # now an unrecorded attribute of the strip's light
    registry = er.async_get(hass)
    for device in coordinator.data["devices"]:
        unique_id = f"{entry.unique_id}-{device['name']}-showing"
        if entity_id := registry.async_get_entity_id("sensor", DOMAIN, unique_id):
            registry.async_remove(entity_id)


class FeatureSensor(DirtyLedsEntity, SensorEntity):
    """Updated from the event stream's music features every couple of seconds"""
    _attr_state_class = SensorStateClass.MEASUREMENT

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.add_features_listener(self._features_changed))

    @callback
    def _features_changed(self) -> None:
        self.async_write_ha_state()


class TempoSensor(FeatureSensor):
    _attr_name = "Tempo"
    _attr_icon = "mdi:metronome"
    _attr_native_unit_of_measurement = "BPM"

    def __init__(self, coordinator: DirtyLedsCoordinator) -> None:
        super().__init__(coordinator, "tempo")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.features.get("tempo")


class MeterSensor(FeatureSensor):
    """0-1 loudness of a band, as driving the effects"""

    def __init__(
        self, coordinator: DirtyLedsCoordinator, meter: str, name: str, icon: str, enabled: bool
    ) -> None:
        super().__init__(coordinator, meter)
        self._meter = meter
        self._attr_name = name
        self._attr_icon = icon
        self._attr_entity_registry_enabled_default = enabled

    @property
    def native_value(self) -> float | None:
        return self.coordinator.features.get("meters", {}).get(self._meter)
