"""Diagnostics for Tibber EV SoC Sync."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import TibberEvSocSyncConfigEntry

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: TibberEvSocSyncConfigEntry) -> dict[str, Any]:
    manager = entry.runtime_data
    return {
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "state": {
            "status": manager.status,
            "last_sent_level": manager.last_sent_level,
            "last_success": manager.last_success.isoformat() if manager.last_success else None,
            "last_attempt": manager.last_attempt.isoformat() if manager.last_attempt else None,
            "last_error": manager.last_error,
            "last_reason": manager.last_reason,
            "plugged_in": manager.is_plugged(),
        },
    }
