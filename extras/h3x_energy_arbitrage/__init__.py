"""Pylontech H3X energy arbitrage integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import H3XArbitrageCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up the integration from a config entry."""
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    coordinator = H3XArbitrageCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = getattr(entry, "runtime_data", None)
    if unload_ok and coordinator:
        await coordinator.async_shutdown()
    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
