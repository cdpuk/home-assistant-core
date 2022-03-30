"""The GivEnergy integration."""
from __future__ import annotations

from datetime import timedelta

import async_timeout
from givenergy_modbus.model.plant import Plant

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER
from .givenergy import GivEnergy

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GivEnergy from a config entry."""
    host = entry.data.get("host")

    connection = GivEnergy(host)
    coordinator = GivEnergyUpdateCoordinator(hass, connection)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class GivEnergyUpdateCoordinator(DataUpdateCoordinator[Plant]):
    """Update coordinator that enables efficient batched updates to all entities associated with an inverter."""

    def __init__(self, hass, connection: GivEnergy):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name="Inverter",
            update_interval=timedelta(seconds=60),
        )
        self.connection = connection

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(10):
                return await self.hass.async_add_executor_job(
                    self.connection.fetch_data
                )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
