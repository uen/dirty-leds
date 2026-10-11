"""Set up Dirty LEDs from the UI: just where the server is"""
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import DirtyLedsClient, DirtyLedsError
from .const import DEFAULT_HOST, DEFAULT_PORT, DOMAIN


class DirtyLedsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            client = DirtyLedsClient(async_get_clientsession(self.hass), user_input[CONF_HOST], user_input[CONF_PORT])
            try:
                await client.get_state()
            except DirtyLedsError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Dirty LEDs", data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
