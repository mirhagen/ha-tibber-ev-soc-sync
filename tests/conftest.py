"""Shared fixtures."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tibber_ev_soc_sync.const import (
    CONF_HOME_ID,
    CONF_MIN_DELTA,
    CONF_ONLY_WHEN_PLUGGED,
    CONF_PLUG_ENTITY,
    CONF_REFRESH_DELAY,
    CONF_SOC_ENTITY,
    CONF_UNPLUGGED_STATES,
    CONF_VEHICLE_ID,
    CONF_VEHICLE_NAME,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load the integration from custom_components."""
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Kia offline",
        unique_id="vehicle-1",
        data={
            "email": "test@example.com",
            "password": "secret",
            CONF_HOME_ID: "home-1",
            CONF_VEHICLE_ID: "vehicle-1",
            CONF_VEHICLE_NAME: "Kia offline",
        },
        options={
            CONF_SOC_ENTITY: "sensor.car_battery",
            CONF_PLUG_ENTITY: "sensor.charger_status",
            CONF_UNPLUGGED_STATES: ["disconnected"],
            CONF_ONLY_WHEN_PLUGGED: True,
            CONF_MIN_DELTA: 5,
            CONF_REFRESH_DELAY: 0,
        },
    )
