"""Tests for when and how the battery level is synced."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.tibber_ev_soc_sync.api import TibberAppAuthError, TibberAppError
from custom_components.tibber_ev_soc_sync.const import DOMAIN
from custom_components.tibber_ev_soc_sync.sync import plug_status, read_level

SET_LEVEL = "custom_components.tibber_ev_soc_sync.api.TibberAppClient.async_set_battery_level"


@pytest.fixture
def set_level():
    with patch(SET_LEVEL, new_callable=AsyncMock) as mock:
        yield mock


async def _setup(hass: HomeAssistant, entry, soc="80", plug="disconnected") -> None:
    hass.states.async_set("sensor.car_battery", soc)
    hass.states.async_set("sensor.charger_status", plug)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _state(hass, entity_id):
    return hass.states.get(entity_id).state


async def test_plug_in_syncs(hass: HomeAssistant, config_entry, set_level) -> None:
    await _setup(hass, config_entry)
    hass.states.async_set("sensor.charger_status", "awaiting_start")
    await hass.async_block_till_done()
    set_level.assert_awaited_once_with("home-1", "vehicle-1", 80)
    assert _state(hass, "sensor.kia_offline_tibber_battery_level_in_tibber") == "80"
    assert _state(hass, "sensor.kia_offline_tibber_sync_status") == "ok"


async def test_unknown_to_plugged_does_not_sync(hass: HomeAssistant, config_entry, set_level) -> None:
    await _setup(hass, config_entry, plug="unavailable")
    hass.states.async_set("sensor.charger_status", "charging")
    await hass.async_block_till_done()
    set_level.assert_not_awaited()


async def test_level_change_needs_delta_and_plug(hass: HomeAssistant, config_entry, set_level) -> None:
    await _setup(hass, config_entry)
    # Not plugged in: no sync
    hass.states.async_set("sensor.car_battery", "50")
    await hass.async_block_till_done()
    set_level.assert_not_awaited()
    # Plug in → sync 50
    hass.states.async_set("sensor.charger_status", "charging")
    await hass.async_block_till_done()
    set_level.assert_awaited_once_with("home-1", "vehicle-1", 50)
    # Small change → no sync
    hass.states.async_set("sensor.car_battery", "53")
    await hass.async_block_till_done()
    assert set_level.await_count == 1


async def test_auth_error_starts_reauth(hass: HomeAssistant, config_entry) -> None:
    await _setup(hass, config_entry)
    with patch(SET_LEVEL, side_effect=TibberAppAuthError("bad password")):
        hass.states.async_set("sensor.charger_status", "charging")
        await hass.async_block_till_done()
    assert _state(hass, "sensor.kia_offline_tibber_sync_status") == "auth_error"
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == SOURCE_REAUTH for flow in flows)


async def test_api_error_sets_status(hass: HomeAssistant, config_entry) -> None:
    await _setup(hass, config_entry)
    with patch(SET_LEVEL, side_effect=TibberAppError("down")):
        hass.states.async_set("sensor.charger_status", "charging")
        await hass.async_block_till_done()
    assert _state(hass, "sensor.kia_offline_tibber_sync_status") == "error"
    attributes = hass.states.get("sensor.kia_offline_tibber_sync_status").attributes
    assert attributes["last_error"] == "down"


async def test_button_and_service(hass: HomeAssistant, config_entry, set_level) -> None:
    await _setup(hass, config_entry, soc="77")
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.kia_offline_tibber_sync_now"}, blocking=True
    )
    set_level.assert_awaited_with("home-1", "vehicle-1", 77)
    await hass.services.async_call(
        DOMAIN, "sync", {"config_entry_id": config_entry.entry_id, "level": 42}, blocking=True
    )
    set_level.assert_awaited_with("home-1", "vehicle-1", 42)


async def test_service_without_valid_level(hass: HomeAssistant, config_entry, set_level) -> None:
    await _setup(hass, config_entry, soc="unavailable")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "sync", {"config_entry_id": config_entry.entry_id}, blocking=True)
    set_level.assert_not_awaited()


async def test_unload(hass: HomeAssistant, config_entry, set_level) -> None:
    await _setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    hass.states.async_set("sensor.charger_status", "charging")
    await hass.async_block_till_done()
    set_level.assert_not_awaited()


def test_helpers() -> None:
    from homeassistant.core import State

    assert read_level(State("sensor.x", "84.4")) == 84
    assert read_level(State("sensor.x", "unknown")) is None
    assert read_level(State("sensor.x", "120")) is None
    assert plug_status(State("binary_sensor.x", "on"), []) is True
    assert plug_status(State("binary_sensor.x", "off"), []) is False
    assert plug_status(State("sensor.x", "Disconnected"), ["disconnected"]) is False
    assert plug_status(State("sensor.x", "charging"), ["disconnected"]) is True
    assert plug_status(State("sensor.x", "unavailable"), ["disconnected"]) is None
