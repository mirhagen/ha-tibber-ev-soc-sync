"""Sensors showing the state of the sync."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TibberEvSocSyncConfigEntry
from .entity import TibberEvSocSyncEntity
from .sync import STATUS_AUTH_ERROR, STATUS_ERROR, STATUS_NEVER, STATUS_OK, STATUS_SYNCING

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TibberEvSocSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    async_add_entities(
        [
            LastSentLevelSensor(manager, "last_sent_level"),
            LastSuccessSensor(manager, "last_success"),
            StatusSensor(manager, "status"),
        ]
    )


class LastSentLevelSensor(TibberEvSocSyncEntity, SensorEntity):
    """The battery level most recently accepted by Tibber."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY

    @property
    def native_value(self) -> int | None:
        return self.manager.last_sent_level


class LastSuccessSensor(TibberEvSocSyncEntity, SensorEntity):
    """When Tibber last accepted a battery level."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        return self.manager.last_success


class StatusSensor(TibberEvSocSyncEntity, SensorEntity):
    """Result of the latest sync."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATUS_NEVER, STATUS_SYNCING, STATUS_OK, STATUS_ERROR, STATUS_AUTH_ERROR]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        return self.manager.status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "last_error": self.manager.last_error,
            "last_reason": self.manager.last_reason,
            "last_attempt": self.manager.last_attempt.isoformat() if self.manager.last_attempt else None,
        }
