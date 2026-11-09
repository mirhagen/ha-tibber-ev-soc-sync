"""Decides when to send the vehicle's battery level to Tibber, and does it."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .api import TibberAppAuthError, TibberAppClient, TibberAppError
from .const import (
    CONF_HOME_ID,
    CONF_MIN_DELTA,
    CONF_ONLY_WHEN_PLUGGED,
    CONF_PLUG_ENTITY,
    CONF_REFRESH_DELAY,
    CONF_SOC_ENTITY,
    CONF_UNPLUGGED_STATES,
    CONF_VEHICLE_ID,
    DEFAULT_MIN_DELTA,
    DEFAULT_ONLY_WHEN_PLUGGED,
    DEFAULT_REFRESH_DELAY,
    DEFAULT_UNPLUGGED_STATES,
    MIN_SECONDS_BETWEEN_SYNCS,
    UNKNOWN_STATES,
)

_LOGGER = logging.getLogger(__name__)

STATUS_NEVER = "never"
STATUS_OK = "ok"
STATUS_SYNCING = "syncing"
STATUS_ERROR = "error"
STATUS_AUTH_ERROR = "auth_error"


def read_level(state: State | None) -> int | None:
    """Return the battery level of a sensor state as 0–100, or None."""
    if state is None or state.state in UNKNOWN_STATES:
        return None
    try:
        level = round(float(state.state))
    except (TypeError, ValueError):
        return None
    return level if 0 <= level <= 100 else None


def plug_status(state: State | None, unplugged_states: list[str]) -> bool | None:
    """True if plugged in, False if unplugged, None if unknown."""
    if state is None or state.state.lower() in UNKNOWN_STATES:
        return None
    if state.domain == "binary_sensor":
        return state.state == STATE_ON
    return state.state.lower() not in {value.lower() for value in unplugged_states}


class SocSyncManager:
    """One per config entry: listens to the vehicle's sensors and syncs to Tibber."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: TibberAppClient) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.status: str = STATUS_NEVER
        self.last_sent_level: int | None = None
        self.last_success: datetime | None = None
        self.last_attempt: datetime | None = None
        self.last_error: str | None = None
        self.last_reason: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribe: list[CALLBACK_TYPE] = []
        self._lock = asyncio.Lock()
        self._pending: asyncio.Task | None = None

    # ── Configuration ────────────────────────────────────────────────
    def _option(self, key: str, default: Any) -> Any:
        return self.entry.options.get(key, self.entry.data.get(key, default))

    @property
    def soc_entity(self) -> str:
        return self._option(CONF_SOC_ENTITY, "")

    @property
    def plug_entity(self) -> str | None:
        return self._option(CONF_PLUG_ENTITY, None) or None

    @property
    def unplugged_states(self) -> list[str]:
        return list(self._option(CONF_UNPLUGGED_STATES, DEFAULT_UNPLUGGED_STATES))

    @property
    def min_delta(self) -> int:
        return int(self._option(CONF_MIN_DELTA, DEFAULT_MIN_DELTA))

    @property
    def only_when_plugged(self) -> bool:
        return bool(self._option(CONF_ONLY_WHEN_PLUGGED, DEFAULT_ONLY_WHEN_PLUGGED))

    @property
    def refresh_delay(self) -> int:
        return int(self._option(CONF_REFRESH_DELAY, DEFAULT_REFRESH_DELAY))

    def is_plugged(self) -> bool | None:
        if not self.plug_entity:
            return None
        return plug_status(self.hass.states.get(self.plug_entity), self.unplugged_states)

    # ── Listeners for entities ───────────────────────────────────────
    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(update_callback)

        @callback
        def remove() -> None:
            self._listeners.remove(update_callback)

        return remove

    @callback
    def _notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    # ── Lifecycle ────────────────────────────────────────────────────
    @callback
    def async_start(self) -> None:
        self._unsubscribe.append(async_track_state_change_event(self.hass, [self.soc_entity], self._soc_changed))
        if self.plug_entity:
            self._unsubscribe.append(async_track_state_change_event(self.hass, [self.plug_entity], self._plug_changed))

    @callback
    def async_stop(self) -> None:
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe.clear()
        if self._pending and not self._pending.done():
            self._pending.cancel()

    # ── Triggers ─────────────────────────────────────────────────────
    @callback
    def _plug_changed(self, event: Event[EventStateChangedData]) -> None:
        old = plug_status(event.data["old_state"], self.unplugged_states)
        new = plug_status(event.data["new_state"], self.unplugged_states)
        if old is False and new is True:
            _LOGGER.debug("Vehicle plugged in, syncing battery level")
            self._schedule(self.async_sync("plugged_in", refresh=True))

    @callback
    def _soc_changed(self, event: Event[EventStateChangedData]) -> None:
        level = read_level(event.data["new_state"])
        if level is None:
            return
        if self.only_when_plugged and self.plug_entity and self.is_plugged() is not True:
            return
        if self.last_sent_level is not None and abs(level - self.last_sent_level) < self.min_delta:
            return
        if self.last_attempt and (dt_util.utcnow() - self.last_attempt).total_seconds() < MIN_SECONDS_BETWEEN_SYNCS:
            return
        self._schedule(self.async_sync("level_changed"))

    @callback
    def _schedule(self, coro) -> None:
        if self._pending and not self._pending.done():
            coro.close()
            return

        async def run() -> None:
            # Errors are already logged and reflected in the status sensor.
            with contextlib.suppress(HomeAssistantError):
                await coro

        self._pending = self.entry.async_create_background_task(
            self.hass, run(), f"tibber_ev_soc_sync {self.entry.entry_id}"
        )

    # ── Sync ─────────────────────────────────────────────────────────
    async def async_sync(self, reason: str, level: int | None = None, refresh: bool = False) -> None:
        """Send the battery level to Tibber. Raises HomeAssistantError on failure."""
        async with self._lock:
            if refresh and self.refresh_delay > 0 and level is None:
                await self.hass.services.async_call(
                    "homeassistant", "update_entity", {"entity_id": self.soc_entity}, blocking=False
                )
                await asyncio.sleep(self.refresh_delay)

            if level is None:
                level = read_level(self.hass.states.get(self.soc_entity))
            if level is None:
                self._finish(STATUS_ERROR, reason, f"No valid battery level in {self.soc_entity}")
                raise HomeAssistantError(f"No valid battery level in {self.soc_entity}")

            self.status = STATUS_SYNCING
            self.last_attempt = dt_util.utcnow()
            self._notify()
            try:
                await self.client.async_set_battery_level(
                    self.entry.data[CONF_HOME_ID], self.entry.data[CONF_VEHICLE_ID], level
                )
            except TibberAppAuthError as err:
                self._finish(STATUS_AUTH_ERROR, reason, str(err))
                self.entry.async_start_reauth(self.hass)
                raise HomeAssistantError(f"Tibber login failed: {err}") from err
            except TibberAppError as err:
                self._finish(STATUS_ERROR, reason, str(err))
                raise HomeAssistantError(f"Could not update Tibber: {err}") from err

            self.last_sent_level = level
            self.last_success = dt_util.utcnow()
            self._finish(STATUS_OK, reason, None)
            _LOGGER.info("Sent battery level %s %% to Tibber (%s)", level, reason)

    @callback
    def _finish(self, status: str, reason: str, error: str | None) -> None:
        self.status = status
        self.last_reason = reason
        self.last_error = error
        if error:
            _LOGGER.warning("Tibber EV SoC Sync (%s): %s", reason, error)
        self._notify()
