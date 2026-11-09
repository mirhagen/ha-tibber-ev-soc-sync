"""Tibber EV SoC Sync – keeps Tibber's battery level for an offline vehicle up to date."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .api import TibberAppClient
from .const import ATTR_CONFIG_ENTRY_ID, ATTR_LEVEL, DOMAIN, SERVICE_SYNC
from .sync import SocSyncManager

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type TibberEvSocSyncConfigEntry = ConfigEntry[SocSyncManager]

SYNC_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_LEVEL): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the sync service."""

    async def handle_sync(call: ServiceCall) -> None:
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="entry_not_loaded")
        manager: SocSyncManager = entry.runtime_data
        await manager.async_sync("service", level=call.data.get(ATTR_LEVEL))

    hass.services.async_register(DOMAIN, SERVICE_SYNC, handle_sync, schema=SYNC_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TibberEvSocSyncConfigEntry) -> bool:
    """Set up one vehicle."""
    client = TibberAppClient(async_get_clientsession(hass), entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    manager = SocSyncManager(hass, entry, client)
    entry.runtime_data = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    manager.async_start()
    entry.async_on_unload(manager.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TibberEvSocSyncConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: TibberEvSocSyncConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
