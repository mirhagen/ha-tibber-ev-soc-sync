"""Constants for Tibber EV SoC Sync."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "tibber_ev_soc_sync"

CONF_HOME_ID: Final = "home_id"
CONF_VEHICLE_ID: Final = "vehicle_id"
CONF_VEHICLE_NAME: Final = "vehicle_name"
CONF_SOC_ENTITY: Final = "soc_entity"
CONF_PLUG_ENTITY: Final = "plug_entity"
CONF_UNPLUGGED_STATES: Final = "unplugged_states"
CONF_MIN_DELTA: Final = "min_delta"
CONF_ONLY_WHEN_PLUGGED: Final = "only_when_plugged"
CONF_REFRESH_DELAY: Final = "refresh_delay"

DEFAULT_UNPLUGGED_STATES: Final = ["disconnected", "unplugged", "not_connected", "off"]
DEFAULT_MIN_DELTA: Final = 5
DEFAULT_ONLY_WHEN_PLUGGED: Final = True
DEFAULT_REFRESH_DELAY: Final = 60

# States that say nothing about whether the car is plugged in.
UNKNOWN_STATES: Final = {"unknown", "unavailable", "", "none"}

# Minimum time between two automatic syncs, to be gentle with Tibber's API.
MIN_SECONDS_BETWEEN_SYNCS: Final = 60

SERVICE_SYNC: Final = "sync"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_LEVEL: Final = "level"
