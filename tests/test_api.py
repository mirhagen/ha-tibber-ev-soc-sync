"""Tests for the Tibber app API client."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_ev_soc_sync.api import (
    GQL_URL,
    LOGIN_URL,
    TibberAppAuthError,
    TibberAppClient,
    TibberAppError,
    parse_account,
)


def test_parse_account() -> None:
    account = parse_account(
        {
            "me": {
                "homes": [{"id": "h1", "title": "Hemma"}, {"id": "h2", "title": None}],
                "myVehicles": {"vehicles": [{"id": "v1", "title": "Kia offline"}, None]},
            }
        }
    )
    assert [(home.id, home.title) for home in account.homes] == [("h1", "Hemma"), ("h2", "h2")]
    assert [(vehicle.id, vehicle.title) for vehicle in account.vehicles] == [("v1", "Kia offline")]


def test_parse_account_empty() -> None:
    account = parse_account({"me": {"homes": [], "myVehicles": None}})
    assert account.homes == [] and account.vehicles == []


async def test_set_battery_level(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(LOGIN_URL, json={"token": "abc"})
    aioclient_mock.post(GQL_URL, json={"data": {"me": {"setVehicleSettings": {"__typename": "Vehicle"}}}})
    client = TibberAppClient(async_get_clientsession(hass), "a@b.se", "pw")

    await client.async_set_battery_level("h1", "v1", 84)

    login_call, gql_call = aioclient_mock.mock_calls
    assert login_call[2] == {"email": "a@b.se", "password": "pw"}
    assert gql_call[3]["Authorization"] == "Bearer abc"
    assert gql_call[2]["variables"] == {
        "vehicleId": "v1",
        "homeId": "h1",
        "settings": [{"key": "offline.vehicle.batteryLevel", "value": 84}],
    }


async def test_login_rejected(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(LOGIN_URL, status=401)
    client = TibberAppClient(async_get_clientsession(hass), "a@b.se", "wrong")
    with pytest.raises(TibberAppAuthError):
        await client.async_get_account()


async def test_graphql_error(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(LOGIN_URL, json={"token": "abc"})
    aioclient_mock.post(GQL_URL, json={"errors": [{"message": "Something broke"}]})
    client = TibberAppClient(async_get_clientsession(hass), "a@b.se", "pw")
    with pytest.raises(TibberAppError, match="Something broke"):
        await client.async_set_battery_level("h1", "v1", 50)


async def test_unconfirmed_result(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(LOGIN_URL, json={"token": "abc"})
    aioclient_mock.post(GQL_URL, json={"data": {"me": {"setVehicleSettings": None}}})
    client = TibberAppClient(async_get_clientsession(hass), "a@b.se", "pw")
    with pytest.raises(TibberAppError):
        await client.async_set_battery_level("h1", "v1", 50)


async def test_level_out_of_range(hass: HomeAssistant) -> None:
    client = TibberAppClient(async_get_clientsession(hass), "a@b.se", "pw")
    with pytest.raises(ValueError):
        await client.async_set_battery_level("h1", "v1", 101)
