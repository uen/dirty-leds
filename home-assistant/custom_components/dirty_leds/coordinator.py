"""Keeps the dirty-leds state, pushed over the event stream with a slow poll behind it"""
import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import DirtyLedsClient, DirtyLedsError
from .const import DOMAIN, OFF_EFFECT, POLL_SECONDS, RECONNECT_SECONDS

_LOGGER = logging.getLogger(__name__)


class DirtyLedsCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: DirtyLedsClient) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=POLL_SECONDS)
        )
        self.client = client
        # Latest music features (tempo, meters) from the frame events
        self.features: dict = {}
        self._feature_listeners: list = []
        # Effect each strip had before it was turned off, to restore on turn on
        self.last_effects: dict[str, str] = {}
        self._stream_task: asyncio.Task | None = None
        # The server's own device, which every strip device connects through
        self.server_device_id: str | None = None

    async def _async_update_data(self) -> dict:
        try:
            state = await self.client.get_state()
        except DirtyLedsError as error:
            raise UpdateFailed(str(error)) from error
        self._remember_effects(state)
        return state

    def device(self, name: str) -> dict | None:
        return next((device for device in self.data["devices"] if device["name"] == name), None)

    @callback
    def _remember_effects(self, state: dict) -> None:
        for device in state["devices"]:
            if device["currentEffect"] != OFF_EFFECT:
                self.last_effects[device["name"]] = device["currentEffect"]

    def async_set_updated_data(self, data: dict) -> None:
        self._remember_effects(data)
        super().async_set_updated_data(data)

    async def action(self, name: str, payload: dict) -> None:
        await self.actions([(name, payload)])

    async def actions(self, actions: list[tuple[str, dict]]) -> None:
        """Run actions in order, then read the state back once"""
        try:
            for name, payload in actions:
                await self.client.action(name, payload)
        except DirtyLedsError as error:
            raise HomeAssistantError(str(error)) from error
        # Not the debounced refresh: a second call within its cooldown would show stale state.
        # The event stream pushes the new state too; this covers it being down
        await self.async_refresh()

    @callback
    def add_features_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._feature_listeners.append(listener)
        return lambda: self._feature_listeners.remove(listener)

    @callback
    def _on_features(self, features: dict) -> None:
        self.features = features
        for listener in list(self._feature_listeners):
            listener()

    @callback
    def start_stream(self) -> None:
        self._stream_task = self.config_entry.async_create_background_task(
            self.hass, self._follow_stream(), f"{DOMAIN} event stream"
        )

    async def stop_stream(self) -> None:
        if self._stream_task:
            self._stream_task.cancel()

    async def _follow_stream(self) -> None:
        while True:
            try:
                await self.client.stream(self.async_set_updated_data, self._on_features)
            except (aiohttp.ClientError, TimeoutError, ValueError) as error:
                _LOGGER.debug("Event stream dropped: %s", error)
            await asyncio.sleep(RECONNECT_SECONDS)
