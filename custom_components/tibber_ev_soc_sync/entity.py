"""Base entity for Tibber EV SoC Sync."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import CONF_VEHICLE_ID, CONF_VEHICLE_NAME, DOMAIN
from .sync import SocSyncManager


class TibberEvSocSyncEntity(Entity):
    """Entity that belongs to one synced vehicle and updates with the sync manager."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: SocSyncManager, key: str) -> None:
        self.manager = manager
        entry = manager.entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.data[CONF_VEHICLE_ID]}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_VEHICLE_ID])},
            name=f"{entry.data[CONF_VEHICLE_NAME]} (Tibber)",
            manufacturer="Tibber",
            model="Vehicle without Tibber integration",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.manager.async_add_listener(self.async_write_ha_state))
