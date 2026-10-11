"""Media player: what the lights are listening to, with seeking through pre-analysed tracks"""
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DirtyLedsConfigEntry
from .coordinator import DirtyLedsCoordinator
from .entity import DirtyLedsEntity

OFF_SOURCE = "off"
TRACK_PREFIX = "track:"
# Turning on with nothing to go back to listens to whatever this PC plays
DEFAULT_SOURCE = "system"


async def async_setup_entry(
    hass: HomeAssistant, entry: DirtyLedsConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([MusicPlayer(entry.runtime_data)])


class MusicPlayer(DirtyLedsEntity, MediaPlayerEntity):
    _attr_name = "Music"
    _attr_icon = "mdi:music-circle"
    _attr_media_content_type = MediaType.MUSIC

    def __init__(self, coordinator: DirtyLedsCoordinator) -> None:
        super().__init__(coordinator, "music")
        self._last_source: str | None = None
        self._playing: str | None = None

    @property
    def _audio(self) -> dict:
        return self.coordinator.data["audio"]

    @property
    def _is_track(self) -> bool:
        return self._audio["source"].startswith(TRACK_PREFIX)

    @property
    def _label(self) -> str | None:
        return next((source["label"] for source in self._audio["sources"] if source["id"] == self._audio["source"]), None)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.add_features_listener(self._features_changed))

    @callback
    def _features_changed(self) -> None:
        # Only until a new track's playhead is known
        if self._is_track and self._attr_media_position is None:
            self._read_position()
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        source = self._audio["source"]
        if source != OFF_SOURCE:
            self._last_source = source
        # The playhead only moves with the music, so take it when the source changes and let
        # the frontend count on from there instead of writing the state every couple of seconds
        if source != self._playing:
            self._playing = source
            self._attr_media_position = None
            self._attr_media_position_updated_at = None
        if self._is_track and self._attr_media_position is None:
            self._read_position()
        super()._handle_coordinator_update()

    def _read_position(self) -> None:
        position = self.coordinator.features.get("position")
        if position is not None:
            self._attr_media_position = int(position)
            self._attr_media_position_updated_at = dt_util.utcnow()

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        features = (
            MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF | MediaPlayerEntityFeature.SELECT_SOURCE
        )
        if self._is_track:
            features |= MediaPlayerEntityFeature.SEEK
        return features

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.OFF if self._audio["source"] == OFF_SOURCE else MediaPlayerState.PLAYING

    @property
    def source_list(self) -> list[str]:
        return [source["label"] for source in self._audio["sources"] if source["id"] != OFF_SOURCE]

    @property
    def source(self) -> str | None:
        return None if self._audio["source"] == OFF_SOURCE else self._label

    @property
    def media_title(self) -> str | None:
        if self._audio["source"] == OFF_SOURCE:
            return None
        # Track labels are "Artist - Title"
        label = self._label or self._audio["source"]
        return label.split(" - ", 1)[1] if self._is_track and " - " in label else label

    @property
    def media_artist(self) -> str | None:
        label = self._label or ""
        return label.split(" - ", 1)[0] if self._is_track and " - " in label else None

    @property
    def media_duration(self) -> int | None:
        duration = self._audio["analysis"].get("duration") if self._is_track else None
        return None if duration is None else int(duration)

    @property
    def extra_state_attributes(self) -> dict:
        analysis = self._audio["analysis"]
        return {
            # ready: the whole track is planned; lookahead: live audio heard early; live: reacting as it plays
            "analysis": analysis.get("status"),
            "drops": [round(drop) for drop in analysis.get("drops", [])],
            "error": self._audio["error"],
        }

    async def async_turn_on(self) -> None:
        await self._set_source(self._last_source or DEFAULT_SOURCE)

    async def async_turn_off(self) -> None:
        await self._set_source(OFF_SOURCE)

    async def async_select_source(self, source: str) -> None:
        await self._set_source(next(item["id"] for item in self._audio["sources"] if item["label"] == source))

    async def async_media_seek(self, position: float) -> None:
        await self.coordinator.action("seek", {"position": position})
        self._attr_media_position = int(position)
        self._attr_media_position_updated_at = dt_util.utcnow()
        self.async_write_ha_state()

    async def _set_source(self, source: str) -> None:
        await self.coordinator.action("set-audio", {"source": source})
