"""Config flow for Tibber EV SoC Sync."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import TibberAccount, TibberAppAuthError, TibberAppClient, TibberAppError
from .const import (
    CONF_HOME_ID,
    CONF_MIN_DELTA,
    CONF_ONLY_WHEN_PLUGGED,
    CONF_PLUG_ENTITY,
    CONF_REFRESH_DELAY,
    CONF_SOC_ENTITY,
    CONF_UNPLUGGED_STATES,
    CONF_VEHICLE_ID,
    CONF_VEHICLE_NAME,
    DEFAULT_MIN_DELTA,
    DEFAULT_ONLY_WHEN_PLUGGED,
    DEFAULT_REFRESH_DELAY,
    DEFAULT_UNPLUGGED_STATES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL)),
        vol.Required(CONF_PASSWORD): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
)


def _behaviour_schema(defaults: Mapping[str, Any]) -> dict:
    """Fields shared by the last setup step and the options flow."""
    return {
        vol.Required(CONF_SOC_ENTITY, default=defaults.get(CONF_SOC_ENTITY, vol.UNDEFINED)): EntitySelector(
            EntitySelectorConfig(domain=["sensor", "number", "input_number"])
        ),
        vol.Optional(
            CONF_PLUG_ENTITY,
            description={"suggested_value": defaults.get(CONF_PLUG_ENTITY)},
        ): EntitySelector(EntitySelectorConfig(domain=["binary_sensor", "sensor", "switch", "input_boolean"])),
        vol.Required(
            CONF_UNPLUGGED_STATES,
            default=list(defaults.get(CONF_UNPLUGGED_STATES, DEFAULT_UNPLUGGED_STATES)),
        ): SelectSelector(
            SelectSelectorConfig(options=list(DEFAULT_UNPLUGGED_STATES), multiple=True, custom_value=True)
        ),
        vol.Required(
            CONF_ONLY_WHEN_PLUGGED, default=defaults.get(CONF_ONLY_WHEN_PLUGGED, DEFAULT_ONLY_WHEN_PLUGGED)
        ): BooleanSelector(),
        vol.Required(CONF_MIN_DELTA, default=defaults.get(CONF_MIN_DELTA, DEFAULT_MIN_DELTA)): NumberSelector(
            NumberSelectorConfig(min=1, max=50, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_REFRESH_DELAY, default=defaults.get(CONF_REFRESH_DELAY, DEFAULT_REFRESH_DELAY)
        ): NumberSelector(
            NumberSelectorConfig(min=0, max=600, step=10, unit_of_measurement="s", mode=NumberSelectorMode.BOX)
        ),
    }


class TibberEvSocSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a vehicle: log in → choose vehicle → choose sensors."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, str] = {}
        self._account: TibberAccount | None = None
        self._vehicle: dict[str, str] = {}

    async def _async_fetch_account(self, credentials: Mapping[str, str]) -> tuple[TibberAccount | None, str | None]:
        client = TibberAppClient(
            async_get_clientsession(self.hass), credentials[CONF_EMAIL], credentials[CONF_PASSWORD]
        )
        try:
            return await client.async_get_account(), None
        except TibberAppAuthError:
            return None, "invalid_auth"
        except TibberAppError:
            _LOGGER.exception("Could not reach Tibber")
            return None, "cannot_connect"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            account, error = await self._async_fetch_account(user_input)
            if error:
                errors["base"] = error
            elif not account.vehicles:
                errors["base"] = "no_vehicles"
            elif not account.homes:
                errors["base"] = "no_homes"
            else:
                self._credentials = user_input
                self._account = account
                return await self.async_step_vehicle()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(CREDENTIALS_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_vehicle(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._account is not None
        vehicles = {vehicle.id: vehicle.title for vehicle in self._account.vehicles}
        homes = {home.id: home.title for home in self._account.homes}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_VEHICLE_ID])
            self._abort_if_unique_id_configured()
            self._vehicle = {
                CONF_VEHICLE_ID: user_input[CONF_VEHICLE_ID],
                CONF_VEHICLE_NAME: vehicles[user_input[CONF_VEHICLE_ID]],
                CONF_HOME_ID: user_input.get(CONF_HOME_ID) or next(iter(homes)),
            }
            return await self.async_step_entities()

        schema: dict = {
            vol.Required(CONF_VEHICLE_ID, default=next(iter(vehicles))): SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=key, label=label) for key, label in vehicles.items()],
                    mode=SelectSelectorMode.LIST,
                )
            )
        }
        if len(homes) > 1:
            schema[vol.Required(CONF_HOME_ID, default=next(iter(homes)))] = SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=key, label=label) for key, label in homes.items()],
                    mode=SelectSelectorMode.LIST,
                )
            )
        return self.async_show_form(step_id="vehicle", data_schema=vol.Schema(schema))

    async def async_step_entities(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self._vehicle[CONF_VEHICLE_NAME],
                data={**self._credentials, **self._vehicle},
                options=user_input,
            )
        return self.async_show_form(step_id="entities", data_schema=vol.Schema(_behaviour_schema({})))

    # ── Re-authentication ────────────────────────────────────────────
    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            _, error = await self._async_fetch_account(user_input)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, {CONF_EMAIL: entry.data.get(CONF_EMAIL)}
            ),
            errors=errors,
            description_placeholders={"vehicle": entry.title},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return TibberEvSocSyncOptionsFlow()


class TibberEvSocSyncOptionsFlow(OptionsFlow):
    """Change which sensors are used and how often to sync."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_behaviour_schema(self.config_entry.options))
        )
