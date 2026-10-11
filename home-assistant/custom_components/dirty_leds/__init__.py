"""Dirty LEDs: control the music reactive LED server from Home Assistant"""
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import DirtyLedsClient
from .coordinator import DirtyLedsCoordinator
from .entity import server_device_info

PANEL_URL = "/dirty_leds_panel"
# Sidebar page with the full web interface
PANEL_PATH = "dirty-leds"

PLATFORMS = [Platform.LIGHT, Platform.MEDIA_PLAYER, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

type DirtyLedsConfigEntry = ConfigEntry[DirtyLedsCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DirtyLedsConfigEntry) -> bool:
    client = DirtyLedsClient(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT])
    coordinator = DirtyLedsCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # Before any platform, so the strips can name it as the device they connect through
    server_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **server_device_info(coordinator)
    )
    coordinator.server_device_id = server_device.id
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_stream()
    await _register_panel(hass, entry)
    return True


async def _register_panel(hass: HomeAssistant, entry: DirtyLedsConfigEntry) -> None:
    # Static paths can't be unregistered, so only once per Home Assistant run
    if not hass.data.get(PANEL_URL):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_URL, str(Path(__file__).parent / "panel"), cache_headers=False)]
        )
        hass.data[PANEL_URL] = True
    frontend.async_register_built_in_panel(
        hass,
        "iframe",
        sidebar_title="LEDs",
        sidebar_icon="mdi:led-strip-variant",
        frontend_url_path=PANEL_PATH,
        config={"url": f"{PANEL_URL}/index.html?host={entry.data[CONF_HOST]}&port={entry.data[CONF_PORT]}"},
        require_admin=False,
        update=True,
    )


async def async_unload_entry(hass: HomeAssistant, entry: DirtyLedsConfigEntry) -> bool:
    await entry.runtime_data.stop_stream()
    frontend.async_remove_panel(hass, PANEL_PATH)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
