"""Sensors for Pylontech H3X energy arbitrage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import H3XArbitrageCoordinator


@dataclass(frozen=True, kw_only=True)
class H3XArbitrageSensorDescription(SensorEntityDescription):
    """Describe an arbitrage sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    extra_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


def _decision_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Return rich diagnostics for the decision sensor."""
    attributes = dict(data.get("attributes") or {})
    attributes.update(
        {
            "reason": data.get("reason"),
            "current_price": data.get("current_price"),
            "target_power_w": data.get("target_power_w"),
            "target_power_percent": data.get("target_power_percent"),
            "soc": data.get("soc"),
            "load_power_w": data.get("load_power_w"),
            "bms_temperature_c": data.get("bms_temperature_c"),
            "resolution_minutes": data.get("resolution_minutes"),
            "slots_available": data.get("slots_available"),
            "next_slot_start": data.get("next_slot_start"),
            "next_slot_end": data.get("next_slot_end"),
            "estimated_first_slot_value": data.get("estimated_first_slot_value"),
            "applied": data.get("applied"),
            "apply_error": data.get("apply_error"),
            "updated_at": data.get("updated_at"),
        }
    )
    return attributes


SENSORS: tuple[H3XArbitrageSensorDescription, ...] = (
    H3XArbitrageSensorDescription(
        key="decision",
        translation_key="decision",
        name="Decision",
        icon="mdi:battery-sync",
        value_fn=lambda data: data.get("action"),
        extra_fn=_decision_attributes,
    ),
    H3XArbitrageSensorDescription(
        key="target_power",
        translation_key="target_power",
        name="Target power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("target_power_w"),
    ),
    H3XArbitrageSensorDescription(
        key="target_power_percent",
        translation_key="target_power_percent",
        name="Target power percent",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("target_power_percent"),
    ),
    H3XArbitrageSensorDescription(
        key="current_price",
        translation_key="current_price",
        name="Current price",
        native_unit_of_measurement="currency/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("current_price"),
    ),
    H3XArbitrageSensorDescription(
        key="first_slot_value",
        translation_key="first_slot_value",
        name="First slot value",
        native_unit_of_measurement="currency",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("estimated_first_slot_value"),
    ),
    H3XArbitrageSensorDescription(
        key="resolution_minutes",
        translation_key="resolution_minutes",
        name="Price resolution",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("resolution_minutes"),
    ),
    H3XArbitrageSensorDescription(
        key="slots_available",
        translation_key="slots_available",
        name="Price slots available",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("slots_available"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: H3XArbitrageCoordinator = entry.runtime_data
    async_add_entities(
        H3XArbitrageSensor(coordinator, entry, description) for description in SENSORS
    )


class H3XArbitrageSensor(CoordinatorEntity[H3XArbitrageCoordinator], SensorEntity):
    """A diagnostic sensor for the arbitrage controller."""

    entity_description: H3XArbitrageSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: H3XArbitrageCoordinator,
        entry: ConfigEntry,
        description: H3XArbitrageSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Pylontech H3X Energy Arbitrage",
            "manufacturer": "Local",
            "model": "Nord Pool Optimizer",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional attributes."""
        if self.entity_description.extra_fn is None:
            return None
        return self.entity_description.extra_fn(self.coordinator.data or {})
