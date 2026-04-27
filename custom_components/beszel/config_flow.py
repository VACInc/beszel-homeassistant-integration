"""Config flow for Beszel integration."""

import logging

from homeassistant.config_entries import ConfigFlow
from pocketbase.utils import ClientResponseError
import voluptuous as vol

from .api import BeszelApiClient, BeszelApiAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("Host"): str,
        vol.Required("Username"): str,
        vol.Required("Password"): str,
    }
)


class BeszelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Beszel."""

    VERSION = 1

    async def _async_validate_input(self, user_input):
        """Validate Beszel connection details."""
        api_client = BeszelApiClient(
            user_input["Host"],
            user_input["Username"],
            user_input["Password"],
        )
        await api_client.async_authenticate()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                await self._async_validate_input(user_input)
            except BeszelApiAuthError:
                errors["base"] = "invalid_auth"
            except ClientResponseError as exc:
                _LOGGER.error("PocketBase API error during connection setup: %s", exc)
                errors["base"] = "cannot_connect"
            except Exception as exc:
                _LOGGER.exception("Unexpected exception during setup: %s", exc)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input['Host']}_{user_input['Username']}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["Host"], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of an existing entry."""
        errors = {}
        if user_input is not None:
            try:
                await self._async_validate_input(user_input)
            except BeszelApiAuthError:
                errors["base"] = "invalid_auth"
            except ClientResponseError as exc:
                _LOGGER.error("PocketBase API error during reconfiguration: %s", exc)
                errors["base"] = "cannot_connect"
            except Exception as exc:
                _LOGGER.exception("Unexpected exception during reconfiguration: %s", exc)
                errors["base"] = "unknown"
            else:
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=f"{user_input['Host']}_{user_input['Username']}",
                    title=user_input["Host"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
