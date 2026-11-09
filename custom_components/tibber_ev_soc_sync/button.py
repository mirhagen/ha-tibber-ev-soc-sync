"""Button to sync the battery level right away."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TibberEvSocSyncConfigEntry
from .entity import TibberEvSocSyncEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TibberEvSocSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SyncNowButton(entry.runtime_data, "sync_now")])


class SyncNowButton(TibberEvSocSyncEntity, ButtonEntity):
    """Sends the vehicle's current battery level to Tibber."""

    async def async_press(self) -> None:
        await self.manager.async_sync("button")
