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
from homeassistant.const import UnitOfEnergy, UnitOfPower
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
            "estimated_plan_value": data.get("estimated_plan_value"),
            "estimated_today_value": data.get("estimated_today_value"),
            "planned_charge_kwh": data.get("planned_charge_kwh"),
            "planned_discharge_kwh": data.get("planned_discharge_kwh"),
            "applied": data.get("applied"),
            "apply_error": data.get("apply_error"),
            "updated_at": data.get("updated_at"),
        }
    )
    return attributes


def _price_plan_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Return price and dispatch arrays for dashboard charts."""
    attributes = dict(data.get("attributes") or {})
    return {
        "area": attributes.get("area"),
        "currency": attributes.get("currency"),
        "resolution_minutes": data.get("resolution_minutes"),
        "updated_at": data.get("updated_at"),
        "price_slots": attributes.get("price_slots", []),
        "today_slots": attributes.get("today_slots", []),
        "tomorrow_slots": attributes.get("tomorrow_slots", []),
        "dispatch_plan": attributes.get("dispatch_plan", []),
    }


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
        key="estimated_savings",
        translation_key="estimated_savings",
        name="Estimated savings",
        native_unit_of_measurement="currency",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cash-multiple",
        value_fn=lambda data: data.get("estimated_plan_value"),
    ),
    H3XArbitrageSensorDescription(
        key="estimated_savings_today",
        translation_key="estimated_savings_today",
        name="Estimated savings today",
        native_unit_of_measurement="currency",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cash-clock",
        value_fn=lambda data: data.get("estimated_today_value"),
    ),
    H3XArbitrageSensorDescription(
        key="planned_charge_energy",
        translation_key="planned_charge_energy",
        name="Planned charge energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-plus",
        value_fn=lambda data: data.get("planned_charge_kwh"),
    ),
    H3XArbitrageSensorDescription(
        key="planned_discharge_energy",
        translation_key="planned_discharge_energy",
        name="Planned discharge energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-minus",
        value_fn=lambda data: data.get("planned_discharge_kwh"),
    ),
    H3XArbitrageSensorDescription(
        key="price_plan",
        translation_key="price_plan",
        name="Price plan",
        native_unit_of_measurement="currency/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-timeline-variant",
        value_fn=lambda data: data.get("current_price"),
        extra_fn=_price_plan_attributes,
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
