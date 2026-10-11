"""Selects: where the music comes from, saved profiles, and each strip's effect and colours"""
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DirtyLedsConfigEntry
from .coordinator import DirtyLedsCoordinator
from .const import AUTO_EFFECT
from .entity import DirtyLedsEntity, DirtyLedsStripEntity

# The option holding an effect's colours: a palette for most effects, one colour for Single
COLOUR_OPTIONS = ("color_mode", "color")


async def async_setup_entry(
    hass: HomeAssistant, entry: DirtyLedsConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = [AudioSourceSelect(coordinator), ProfileSelect(coordinator), ShowStyleSelect(coordinator)]
    for device in coordinator.data["devices"]:
        entities += [StripEffectSelect(coordinator, device["name"]), StripColourSelect(coordinator, device["name"])]
    async_add_entities(entities)


class AudioSourceSelect(DirtyLedsEntity, SelectEntity):
    """Options are the sources' labels; the server wants their ids"""
    _attr_name = "Audio source"
    _attr_icon = "mdi:music"

    def __init__(self, coordinator: DirtyLedsCoordinator) -> None:
        super().__init__(coordinator, "audio-source")

    @property
    def _sources(self) -> list[dict]:
        return self.coordinator.data["audio"]["sources"]

    @property
    def options(self) -> list[str]:
        return [source["label"] for source in self._sources]

    @property
    def current_option(self) -> str | None:
        current = self.coordinator.data["audio"]["source"]
        return next((source["label"] for source in self._sources if source["id"] == current), None)

    @property
    def extra_state_attributes(self) -> dict:
        audio = self.coordinator.data["audio"]
        return {"source_id": audio["source"], "error": audio["error"], "analysis": audio["analysis"].get("status")}

    async def async_select_option(self, option: str) -> None:
        source = next(source["id"] for source in self._sources if source["label"] == option)
        await self.coordinator.action("set-audio", {"source": source})


class ProfileSelect(DirtyLedsEntity, SelectEntity):
    """Saved looks from the web interface. Shows nothing once a setting changes after loading"""
    _attr_name = "Profile"
    _attr_icon = "mdi:palette"

    def __init__(self, coordinator: DirtyLedsCoordinator) -> None:
        super().__init__(coordinator, "profile")

    @property
    def options(self) -> list[str]:
        return [profile["name"] for profile in self.coordinator.data["profiles"]]

    @property
    def current_option(self) -> str | None:
        current = self.coordinator.data["currentProfile"]
        return next((profile["name"] for profile in self.coordinator.data["profiles"] if profile["id"] == current), None)

    async def async_select_option(self, option: str) -> None:
        profile = next(profile["id"] for profile in self.coordinator.data["profiles"] if profile["name"] == option)
        await self.coordinator.action("load-profile", {"id": profile})


class ShowStyleSelect(DirtyLedsEntity, SelectEntity):
    """How the auto show directs: mixed, freestyle or effects. Set on every strip"""
    _attr_name = "Show style"
    _attr_icon = "mdi:movie-open-star"

    def __init__(self, coordinator: DirtyLedsCoordinator) -> None:
        super().__init__(coordinator, "show-style")

    def _style_option(self) -> tuple[dict, dict] | None:
        for device in self.coordinator.data["devices"]:
            for effect in device["effects"]:
                if effect["name"] == AUTO_EFFECT:
                    option = next((item for item in effect["options"] if item["key"] == "style"), None)
                    return (option, effect["values"]) if option else None
        return None

    @property
    def available(self) -> bool:
        return super().available and self._style_option() is not None

    @property
    def options(self) -> list[str]:
        found = self._style_option()
        return [str(value) for value in found[0]["config"]] if found else []

    @property
    def current_option(self) -> str | None:
        found = self._style_option()
        return str(found[1].get("style")) if found else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.actions([
            ("set-option", {"device": device["name"], "effect": AUTO_EFFECT, "option": "style", "value": option})
            for device in self.coordinator.data["devices"]
        ])


class StripEffectSelect(DirtyLedsStripEntity, SelectEntity):
    """Pick the strip's effect, Off and Auto included"""
    _attr_name = "Effect"
    _attr_icon = "mdi:auto-fix"

    def __init__(self, coordinator: DirtyLedsCoordinator, strip: str) -> None:
        super().__init__(coordinator, strip, "effect")

    @property
    def options(self) -> list[str]:
        return [effect["name"] for effect in self.strip_state["effects"]]

    @property
    def current_option(self) -> str | None:
        return self.strip_state["currentEffect"]

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.action("set-effect", {"device": self.strip, "effect": option})


class StripColourSelect(DirtyLedsStripEntity, SelectEntity):
    """Colours of the strip's current effect. Unavailable for effects without any (Auto, Stars...)"""
    _attr_name = "Colours"
    _attr_icon = "mdi:palette-outline"

    def __init__(self, coordinator: DirtyLedsCoordinator, strip: str) -> None:
        super().__init__(coordinator, strip, "colours")

    def _colour_option(self) -> tuple[dict, dict] | None:
        """The current effect's colour option and its values"""
        effect = self.effect_state(self.strip_state["currentEffect"])
        if effect is None:
            return None
        for key in COLOUR_OPTIONS:
            option = next((item for item in effect["options"] if item["key"] == key), None)
            if option and option["config"]:
                return option, effect
        return None

    @property
    def available(self) -> bool:
        return super().available and self._colour_option() is not None

    @property
    def options(self) -> list[str]:
        found = self._colour_option()
        return [str(value) for value in found[0]["config"]] if found else []

    @property
    def current_option(self) -> str | None:
        found = self._colour_option()
        if found is None:
            return None
        option, effect = found
        return str(effect["values"].get(option["key"]))

    async def async_select_option(self, option: str) -> None:
        found = self._colour_option()
        if found is None:
            return
        key, effect = found[0]["key"], found[1]["name"]
        await self.coordinator.action(
            "set-option", {"device": self.strip, "effect": effect, "option": key, "value": option}
        )
