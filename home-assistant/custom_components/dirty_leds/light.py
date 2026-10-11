"""Lights: all strips together, and each strip on its own"""
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT, ColorMode, LightEntity, LightEntityFeature
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback, async_get_current_platform

from . import DirtyLedsConfigEntry
from .const import AUTO_EFFECT, DEFAULT_EFFECT, OFF_EFFECT
from .coordinator import DirtyLedsCoordinator
from .entity import DirtyLedsEntity, DirtyLedsStripEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DirtyLedsConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[LightEntity] = [AllStripsLight(coordinator)]
    entities += [StripLight(coordinator, device["name"]) for device in coordinator.data["devices"]]
    async_add_entities(entities)
    # Any effect setting the web interface has, for automations and scripts
    async_get_current_platform().async_register_entity_service(
        "set_option",
        {
            vol.Required("option"): cv.string,
            vol.Required("value"): vol.Any(bool, int, float, str),
            vol.Optional("effect"): cv.string,
        },
        "async_set_option",
    )


def _effect_names(device: dict) -> list[str]:
    return [effect["name"] for effect in device["effects"] if effect["name"] != OFF_EFFECT]


class AllStripsLight(DirtyLedsEntity, LightEntity):
    """Every strip at once. Brightness is the server's master brightness"""
    _attr_name = None
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, coordinator: DirtyLedsCoordinator) -> None:
        super().__init__(coordinator, "light")

    @property
    def is_on(self) -> bool:
        return any(device["currentEffect"] != OFF_EFFECT for device in self.coordinator.data["devices"])

    @property
    def brightness(self) -> int:
        return round(self.coordinator.data["brightness"] * 255 / 100)

    @property
    def effect_list(self) -> list[str]:
        devices = self.coordinator.data["devices"]
        return _effect_names(devices[0]) if devices else []

    @property
    def effect(self) -> str | None:
        effects = {device["currentEffect"] for device in self.coordinator.data["devices"]}
        return effects.pop() if len(effects) == 1 else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        actions = []
        if ATTR_BRIGHTNESS in kwargs:
            actions.append(("set-brightness", {"value": round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)}))
        if ATTR_EFFECT in kwargs:
            actions += self._effect_actions(kwargs[ATTR_EFFECT])
        elif not self.is_on:
            for device in self.coordinator.data["devices"]:
                effect = self.coordinator.last_effects.get(device["name"], DEFAULT_EFFECT)
                actions.append(("set-effect", {"device": device["name"], "effect": effect}))
        await self.coordinator.actions(actions)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.actions(self._effect_actions(OFF_EFFECT))

    async def async_set_option(self, option: str, value: bool | int | float | str, effect: str | None = None) -> None:
        """Change one setting of an effect on every strip, each strip's current effect unless named"""
        await self.coordinator.actions([
            ("set-option", {"device": device["name"], "effect": effect or device["currentEffect"], "option": option,
                            "value": value})
            for device in self.coordinator.data["devices"]
        ])

    def _effect_actions(self, effect: str) -> list[tuple[str, dict]]:
        if effect == AUTO_EFFECT:
            return [("auto-show", {"value": True})]
        return [("set-effect", {"device": device["name"], "effect": effect}) for device in self.coordinator.data["devices"]]


class StripLight(DirtyLedsStripEntity, LightEntity):
    """One strip's effect. With sync on in the server, changing one changes them all"""
    _attr_name = None
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_supported_features = LightEntityFeature.EFFECT
    # Changes every few bars in the auto show; keep it out of the history database
    _unrecorded_attributes = frozenset({"showing"})

    def __init__(self, coordinator: DirtyLedsCoordinator, strip: str) -> None:
        super().__init__(coordinator, strip, "light")

    @property
    def extra_state_attributes(self) -> dict:
        """The effect the auto show picked for this strip, when on Auto"""
        return {"showing": self.strip_state["showing"] or self.strip_state["currentEffect"]}

    @property
    def is_on(self) -> bool:
        return self.strip_state["currentEffect"] != OFF_EFFECT

    @property
    def effect_list(self) -> list[str]:
        return _effect_names(self.strip_state)

    @property
    def effect(self) -> str | None:
        return self.strip_state["currentEffect"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        effect = kwargs.get(ATTR_EFFECT)
        if effect is None:
            if self.is_on:
                return
            effect = self.coordinator.last_effects.get(self.strip, DEFAULT_EFFECT)
        await self.coordinator.action("set-effect", {"device": self.strip, "effect": effect})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.action("set-effect", {"device": self.strip, "effect": OFF_EFFECT})

    async def async_set_option(self, option: str, value: bool | int | float | str, effect: str | None = None) -> None:
        """Change one setting of an effect, the strip's current one unless named"""
        effect = effect or self.strip_state["currentEffect"]
        await self.coordinator.action(
            "set-option", {"device": self.strip, "effect": effect, "option": option, "value": value}
        )
