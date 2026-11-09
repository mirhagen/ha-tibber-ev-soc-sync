"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tibber_ev_soc_sync.api import (
    TibberAccount,
    TibberAppAuthError,
    TibberHome,
    TibberVehicle,
)
from custom_components.tibber_ev_soc_sync.const import DOMAIN

ACCOUNT = TibberAccount(
    homes=[TibberHome("home-1", "Hemma")],
    vehicles=[TibberVehicle("vehicle-1", "Kia offline")],
)
GET_ACCOUNT = "custom_components.tibber_ev_soc_sync.config_flow.TibberAppClient.async_get_account"


async def test_full_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"

    with patch(GET_ACCOUNT, return_value=ACCOUNT):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.se", "password": "pw"}
        )
    assert result["step_id"] == "vehicle"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"vehicle_id": "vehicle-1"})
    assert result["step_id"] == "entities"

    with patch("custom_components.tibber_ev_soc_sync.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "soc_entity": "sensor.car_battery",
                "plug_entity": "sensor.charger_status",
                "unplugged_states": ["disconnected"],
                "only_when_plugged": True,
                "min_delta": 5,
                "refresh_delay": 60,
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kia offline"
    assert result["data"]["home_id"] == "home-1"
    assert result["data"]["vehicle_id"] == "vehicle-1"
    assert result["options"]["soc_entity"] == "sensor.car_battery"


async def test_invalid_auth(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(GET_ACCOUNT, side_effect=TibberAppAuthError("nope")):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.se", "password": "wrong"}
        )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_no_vehicles(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(GET_ACCOUNT, return_value=TibberAccount(homes=[TibberHome("h", "H")], vehicles=[])):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.se", "password": "pw"}
        )
    assert result["errors"] == {"base": "no_vehicles"}


async def test_already_configured(hass: HomeAssistant, config_entry) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(GET_ACCOUNT, return_value=ACCOUNT):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.se", "password": "pw"}
        )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"vehicle_id": "vehicle-1"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, config_entry) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    with (
        patch(GET_ACCOUNT, return_value=ACCOUNT),
        patch("custom_components.tibber_ev_soc_sync.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "test@example.com", "password": "new"}
        )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert config_entry.data["password"] == "new"


async def test_options_flow(hass: HomeAssistant, config_entry) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["step_id"] == "init"
    with patch("custom_components.tibber_ev_soc_sync.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "soc_entity": "sensor.other_battery",
                "unplugged_states": ["off"],
                "only_when_plugged": False,
                "min_delta": 10,
                "refresh_delay": 0,
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options["soc_entity"] == "sensor.other_battery"
    assert "plug_entity" not in config_entry.options
