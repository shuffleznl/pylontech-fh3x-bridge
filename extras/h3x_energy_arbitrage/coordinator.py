"""Coordinator and optimizer for Pylontech H3X energy arbitrage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
import logging
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AREA,
    CONF_BATTERY_CAPACITY_KWH,
    CONF_BMS_TEMP_ENTITY,
    CONF_BUY_COST_ADDER,
    CONF_CHARGE_LIMIT_SOC_ENTITY,
    CONF_CONTINUOUS_POWER_W,
    CONF_CONTROL_ENABLED,
    CONF_CURRENCY,
    CONF_CYCLE_COST,
    CONF_DISCHARGE_LIMIT_SOC_ENTITY,
    CONF_EMS_MODE_ENTITY,
    CONF_ENABLE_PEAK_POWER,
    CONF_GRID_EXPORT_LIMIT_W,
    CONF_GRID_IMPORT_LIMIT_W,
    CONF_HORIZON_HOURS,
    CONF_IDLE_EMS_MODE,
    CONF_INVERTER_FULL_SCALE_POWER_W,
    CONF_LOAD_POWER_ENTITY,
    CONF_MAX_BMS_TEMP_C,
    CONF_MAX_SOC,
    CONF_MIN_ACTIVE_POWER_W,
    CONF_MIN_CHARGE_TEMP_C,
    CONF_MIN_PROFIT_MARGIN,
    CONF_MIN_SOC,
    CONF_NORDPOOL_CONFIG_ENTRY,
    CONF_PEAK_EXTRA_MARGIN,
    CONF_PEAK_POWER_W,
    CONF_POWER_REF_ENTITY,
    CONF_RESERVE_SOC,
    CONF_RESOLUTION,
    CONF_ROUND_TRIP_EFFICIENCY,
    CONF_SELL_COST_ADDER,
    CONF_SOC_ENTITY,
    CONF_TERMINAL_SOC_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_USER_EMS_MODE,
    DEFAULTS,
    DOMAIN,
    NORDPOOL_CONF_AREAS,
    NORDPOOL_CONF_CURRENCY,
    NORDPOOL_DOMAIN,
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PriceSlot:
    """One Nord Pool price interval."""

    start: datetime
    end: datetime
    price: float

    @property
    def duration_hours(self) -> float:
        """Return the full slot duration in hours."""
        return max((self.end - self.start).total_seconds() / 3600, 0.0)


@dataclass(slots=True)
class Decision:
    """Computed control decision."""

    action: str = "idle"
    reason: str = "waiting"
    current_price: float | None = None
    target_power_w: float = 0.0
    target_power_percent: float = 0.0
    soc: float | None = None
    load_power_w: float | None = None
    bms_temperature_c: float | None = None
    resolution_minutes: int | None = None
    slots_available: int = 0
    next_slot_start: str | None = None
    next_slot_end: str | None = None
    estimated_first_slot_value: float = 0.0
    applied: bool = False
    apply_error: str | None = None
    updated_at: str = field(default_factory=lambda: dt_util.utcnow().isoformat())
    attributes: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary for sensors."""
        data = asdict(self)
        data["target_power_w"] = round(self.target_power_w, 1)
        data["target_power_percent"] = round(self.target_power_percent, 1)
        data["estimated_first_slot_value"] = round(self.estimated_first_slot_value, 4)
        return data


class H3XArbitrageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch prices, optimize dispatch, and apply H3X controls."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        update_minutes = float(self._option(CONF_UPDATE_INTERVAL_MINUTES))
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=max(update_minutes, 1.0)),
        )
        self._last_power_percent: float | None = None
        self._last_ems_mode: str | None = None

    def _option(self, key: str) -> Any:
        """Return an option value with a default fallback."""
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, DEFAULTS[key])

    async def _async_update_data(self) -> dict[str, Any]:
        """Update price data, compute the decision, and apply controls."""
        try:
            slots = await self._fetch_price_slots()
            decision = self._compute_decision(slots)
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception("Failed to compute arbitrage decision")
            decision = Decision(action="failsafe", reason=str(err))

        if bool(self._option(CONF_CONTROL_ENABLED)):
            await self._apply_decision(decision)
        else:
            decision.reason = f"{decision.reason}; control disabled"

        return decision.as_dict()

    async def _fetch_price_slots(self) -> list[PriceSlot]:
        """Fetch today and tomorrow price slots from Home Assistant Nord Pool."""
        entry_id = self._resolve_nordpool_entry_id()
        area = self._resolve_area()
        currency = self._resolve_currency()
        resolution = int(self._option(CONF_RESOLUTION))

        today = dt_util.now().date()
        responses: list[dict[str, Any]] = []
        for day in (today, today + timedelta(days=1)):
            response = await self._call_nordpool(entry_id, area, currency, resolution, day)
            responses.extend(response.get(area, []))

        slots: dict[tuple[str, str], PriceSlot] = {}
        now = dt_util.utcnow()
        horizon_end = now + timedelta(hours=float(self._option(CONF_HORIZON_HOURS)))

        for row in responses:
            start = dt_util.parse_datetime(str(row["start"]))
            end = dt_util.parse_datetime(str(row["end"]))
            if start is None or end is None:
                continue
            start = dt_util.as_utc(start)
            end = dt_util.as_utc(end)
            if end <= now or start >= horizon_end:
                continue
            key = (start.isoformat(), end.isoformat())
            slots[key] = PriceSlot(start=start, end=end, price=float(row["price"]) / 1000)

        return sorted(slots.values(), key=lambda slot: slot.start)

    async def _call_nordpool(
        self,
        entry_id: str,
        area: str,
        currency: str,
        resolution: int,
        day: date,
    ) -> dict[str, Any]:
        """Call the Nord Pool service and return its response."""
        try:
            response = await self.hass.services.async_call(
                NORDPOOL_DOMAIN,
                "get_price_indices_for_date",
                {
                    "config_entry": entry_id,
                    "date": day.isoformat(),
                    "areas": area,
                    "currency": currency,
                    "resolution": resolution,
                },
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as err:
            LOGGER.debug("Nord Pool price fetch failed for %s: %s", day, err)
            return {area: []}

        if not isinstance(response, dict):
            return {area: []}
        return response

    def _resolve_nordpool_entry_id(self) -> str:
        """Resolve the configured or first available Nord Pool config entry."""
        configured = str(self._option(CONF_NORDPOOL_CONFIG_ENTRY)).strip()
        entries = self.hass.config_entries.async_entries(NORDPOOL_DOMAIN)
        if configured and configured.lower() != "auto":
            return configured
        if not entries:
            raise RuntimeError("Nord Pool integration is not configured")
        return entries[0].entry_id

    def _resolve_area(self) -> str:
        """Resolve the configured Nord Pool area."""
        configured = str(self._option(CONF_AREA)).strip().upper()
        if configured and configured != "AUTO":
            return configured
        entries = self.hass.config_entries.async_entries(NORDPOOL_DOMAIN)
        for entry in entries:
            areas = entry.data.get(NORDPOOL_CONF_AREAS)
            if isinstance(areas, list) and areas:
                return str(areas[0]).upper()
        raise RuntimeError("Nord Pool area is not configured")

    def _resolve_currency(self) -> str:
        """Resolve the configured Nord Pool currency."""
        configured = str(self._option(CONF_CURRENCY)).strip().upper()
        if configured and configured != "AUTO":
            return configured
        entries = self.hass.config_entries.async_entries(NORDPOOL_DOMAIN)
        for entry in entries:
            currency = entry.data.get(NORDPOOL_CONF_CURRENCY)
            if currency:
                return str(currency).upper()
        return "EUR"

    def _compute_decision(self, slots: list[PriceSlot]) -> Decision:
        """Compute the current best charge/discharge action."""
        now = dt_util.utcnow()
        future_slots = [slot for slot in slots if slot.end > now]
        if not future_slots:
            return Decision(action="failsafe", reason="no current or future price slots")

        soc = self._state_float(str(self._option(CONF_SOC_ENTITY)))
        if soc is None:
            return Decision(action="failsafe", reason="battery SOC entity unavailable")

        capacity_kwh = max(float(self._option(CONF_BATTERY_CAPACITY_KWH)), 0.1)
        min_soc = max(float(self._option(CONF_MIN_SOC)), 0.0)
        reserve_soc = max(float(self._option(CONF_RESERVE_SOC)), min_soc)
        max_soc = min(max(float(self._option(CONF_MAX_SOC)), reserve_soc + 1.0), 100.0)
        floor_soc = min(reserve_soc, max_soc - 1.0)
        min_energy = capacity_kwh * floor_soc / 100
        max_energy = capacity_kwh * max_soc / 100
        current_energy = min(max(capacity_kwh * soc / 100, min_energy), max_energy)

        bms_temp = self._state_float(str(self._option(CONF_BMS_TEMP_ENTITY)))
        charge_allowed, discharge_allowed, temp_reason = self._temperature_permissions(
            bms_temp
        )

        interval_minutes = self._infer_resolution_minutes(future_slots)
        decision = self._run_optimizer(
            future_slots=future_slots,
            current_energy=current_energy,
            min_energy=min_energy,
            max_energy=max_energy,
            terminal_energy=self._terminal_energy(current_energy, min_energy, max_energy),
            charge_allowed=charge_allowed,
            discharge_allowed=discharge_allowed,
        )

        current_slot = future_slots[0]
        decision.soc = soc
        decision.current_price = current_slot.price
        decision.bms_temperature_c = bms_temp
        decision.resolution_minutes = interval_minutes
        decision.slots_available = len(future_slots)
        decision.next_slot_start = current_slot.start.isoformat()
        decision.next_slot_end = current_slot.end.isoformat()
        decision.load_power_w = self._state_float(str(self._option(CONF_LOAD_POWER_ENTITY)))
        decision.updated_at = now.isoformat()
        decision.attributes.update(
            {
                "area": self._resolve_area(),
                "currency": self._resolve_currency(),
                "min_soc": floor_soc,
                "max_soc": max_soc,
                "capacity_kwh": capacity_kwh,
                "temperature_guard": temp_reason,
                "control_enabled": bool(self._option(CONF_CONTROL_ENABLED)),
                "nordpool_resolution_minutes": int(self._option(CONF_RESOLUTION)),
            }
        )

        if decision.action == "charge" and not charge_allowed:
            return self._idle_from(decision, temp_reason or "charging not allowed")
        if decision.action == "discharge" and not discharge_allowed:
            return self._idle_from(decision, temp_reason or "discharging not allowed")

        if decision.action in {"charge", "discharge"}:
            limited_power = self._apply_grid_limit(decision.action, decision.target_power_w)
            if limited_power < float(self._option(CONF_MIN_ACTIVE_POWER_W)):
                return self._idle_from(decision, "target below minimum active power")
            decision.target_power_w = limited_power
            decision.target_power_percent = self._power_to_percent(
                decision.action, limited_power
            )

        return decision

    def _run_optimizer(
        self,
        future_slots: list[PriceSlot],
        current_energy: float,
        min_energy: float,
        max_energy: float,
        terminal_energy: float,
        charge_allowed: bool,
        discharge_allowed: bool,
    ) -> Decision:
        """Run a dynamic-programming arbitrage optimizer."""
        now = dt_util.utcnow()
        capacity_range = max_energy - min_energy
        step_kwh = max(0.25, capacity_range / 100)
        level_count = max(int(round(capacity_range / step_kwh)), 1)
        levels = [min_energy + index * capacity_range / level_count for index in range(level_count + 1)]
        initial_idx = min(
            range(len(levels)),
            key=lambda index: abs(levels[index] - current_energy),
        )

        terminal_values = {
            index: 0.0 if energy + step_kwh / 2 >= terminal_energy else -1_000_000.0
            for index, energy in enumerate(levels)
        }
        values = terminal_values
        policy: dict[tuple[int, int], int] = {}
        first_rewards: dict[tuple[int, int], float] = {}

        charge_eff = math.sqrt(float(self._option(CONF_ROUND_TRIP_EFFICIENCY)))
        discharge_eff = charge_eff
        buy_adder = float(self._option(CONF_BUY_COST_ADDER))
        sell_adder = float(self._option(CONF_SELL_COST_ADDER))
        required_margin = float(self._option(CONF_CYCLE_COST)) + float(
            self._option(CONF_MIN_PROFIT_MARGIN)
        )

        for slot_index in range(len(future_slots) - 1, -1, -1):
            slot = future_slots[slot_index]
            duration_h = self._slot_duration_hours(slot, now if slot_index == 0 else None)
            pmax_w = self._slot_power_limit(slot, future_slots)
            max_charge_delta = pmax_w * duration_h / 1000 * charge_eff
            max_discharge_delta = pmax_w * duration_h / 1000 / discharge_eff
            buy_price = slot.price + buy_adder
            sell_price = slot.price - sell_adder

            next_values: dict[int, float] = {}
            for idx, energy in enumerate(levels):
                best_value = values[idx]
                best_idx = idx
                best_reward = 0.0

                if charge_allowed:
                    for next_idx in range(idx + 1, len(levels)):
                        delta = levels[next_idx] - energy
                        if delta > max_charge_delta + step_kwh / 2:
                            break
                        ac_kwh = delta / charge_eff
                        reward = -ac_kwh * buy_price
                        candidate = reward + values[next_idx]
                        if candidate > best_value:
                            best_value = candidate
                            best_idx = next_idx
                            best_reward = reward

                if discharge_allowed:
                    for next_idx in range(idx - 1, -1, -1):
                        delta = energy - levels[next_idx]
                        if delta > max_discharge_delta + step_kwh / 2:
                            break
                        ac_kwh = delta * discharge_eff
                        reward = ac_kwh * (sell_price - required_margin)
                        candidate = reward + values[next_idx]
                        if candidate > best_value:
                            best_value = candidate
                            best_idx = next_idx
                            best_reward = reward

                next_values[idx] = best_value
                policy[(slot_index, idx)] = best_idx
                if slot_index == 0:
                    first_rewards[(slot_index, idx)] = best_reward

            values = next_values

        next_idx = policy.get((0, initial_idx), initial_idx)
        delta = levels[next_idx] - levels[initial_idx]
        duration_h = self._slot_duration_hours(future_slots[0], now)
        if abs(delta) < step_kwh / 2 or duration_h <= 0:
            return Decision(
                action="idle",
                reason="optimizer selected no economic movement",
                estimated_first_slot_value=first_rewards.get((0, initial_idx), 0.0),
            )

        if delta > 0:
            target_power = delta / charge_eff / duration_h * 1000
            return Decision(
                action="charge",
                reason="current slot is economical for grid charging",
                target_power_w=min(target_power, self._slot_power_limit(future_slots[0], future_slots)),
                estimated_first_slot_value=first_rewards.get((0, initial_idx), 0.0),
            )

        target_power = abs(delta) * discharge_eff / duration_h * 1000
        return Decision(
            action="discharge",
            reason="current slot is economical for grid export",
            target_power_w=min(target_power, self._slot_power_limit(future_slots[0], future_slots)),
            estimated_first_slot_value=first_rewards.get((0, initial_idx), 0.0),
        )

    def _terminal_energy(
        self, current_energy: float, min_energy: float, max_energy: float
    ) -> float:
        """Return the terminal energy floor for the optimization horizon."""
        mode = str(self._option(CONF_TERMINAL_SOC_MODE))
        if mode == "reserve_only":
            return min_energy
        return min(max(current_energy, min_energy), max_energy)

    def _slot_duration_hours(self, slot: PriceSlot, now: datetime | None = None) -> float:
        """Return usable duration for a price slot."""
        start = max(slot.start, now) if now is not None else slot.start
        return max((slot.end - start).total_seconds() / 3600, 0.0)

    def _slot_power_limit(self, slot: PriceSlot, slots: list[PriceSlot]) -> float:
        """Return the allowed AC power for a slot."""
        continuous = float(self._option(CONF_CONTINUOUS_POWER_W))
        peak = float(self._option(CONF_PEAK_POWER_W))
        if not bool(self._option(CONF_ENABLE_PEAK_POWER)):
            return continuous

        buy_adder = float(self._option(CONF_BUY_COST_ADDER))
        sell_adder = float(self._option(CONF_SELL_COST_ADDER))
        required_margin = (
            float(self._option(CONF_CYCLE_COST))
            + float(self._option(CONF_MIN_PROFIT_MARGIN))
            + float(self._option(CONF_PEAK_EXTRA_MARGIN))
        )
        min_buy = min(price_slot.price + buy_adder for price_slot in slots)
        max_sell = max(price_slot.price - sell_adder for price_slot in slots)
        if max_sell - min_buy > required_margin:
            return peak
        return continuous

    def _temperature_permissions(
        self, bms_temp: float | None
    ) -> tuple[bool, bool, str | None]:
        """Return charge and discharge permissions from BMS temperature."""
        if bms_temp is None:
            return True, True, None
        min_charge = float(self._option(CONF_MIN_CHARGE_TEMP_C))
        max_temp = float(self._option(CONF_MAX_BMS_TEMP_C))
        if bms_temp < min_charge:
            return False, True, f"BMS temperature below charge guard ({bms_temp:.1f} C)"
        if bms_temp > max_temp:
            return False, False, f"BMS temperature above guard ({bms_temp:.1f} C)"
        return True, True, None

    def _apply_grid_limit(self, action: str, target_power_w: float) -> float:
        """Limit battery power to avoid exceeding configured grid connection limits."""
        load_power = max(
            self._state_float(str(self._option(CONF_LOAD_POWER_ENTITY))) or 0.0,
            0.0,
        )
        if action == "charge":
            import_limit = float(self._option(CONF_GRID_IMPORT_LIMIT_W))
            if import_limit > 0:
                return min(target_power_w, max(import_limit - load_power, 0.0))
        elif action == "discharge":
            export_limit = float(self._option(CONF_GRID_EXPORT_LIMIT_W))
            if export_limit > 0:
                return min(target_power_w, max(export_limit + load_power, 0.0))
        return target_power_w

    def _power_to_percent(self, action: str, power_w: float) -> float:
        """Convert AC watt target into the signed H3X power reference percentage."""
        full_scale = max(float(self._option(CONF_INVERTER_FULL_SCALE_POWER_W)), 1.0)
        percent = min(max(power_w / full_scale * 100, 0.0), 100.0)
        return -percent if action == "charge" else percent

    def _idle_from(self, decision: Decision, reason: str) -> Decision:
        """Return an idle decision preserving diagnostic context."""
        decision.action = "idle"
        decision.reason = reason
        decision.target_power_w = 0.0
        decision.target_power_percent = 0.0
        return decision

    def _infer_resolution_minutes(self, slots: list[PriceSlot]) -> int | None:
        """Infer the active price resolution from the first slot."""
        if not slots:
            return None
        return int(round(slots[0].duration_hours * 60))

    def _state_float(self, entity_id: str | None) -> float | None:
        """Read a Home Assistant entity as a float."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE, ""}:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    async def _apply_decision(self, decision: Decision) -> None:
        """Apply the control decision through Home Assistant entity services."""
        try:
            await self._set_soc_limits()
            if decision.action in {"charge", "discharge"}:
                await self._set_ems_mode(str(self._option(CONF_USER_EMS_MODE)))
                await self._set_power_ref(decision.target_power_percent)
            else:
                await self._set_power_ref(0.0)
                await self._set_ems_mode(str(self._option(CONF_IDLE_EMS_MODE)))
            decision.applied = True
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception("Failed to apply H3X arbitrage decision")
            decision.applied = False
            decision.apply_error = str(err)

    async def _set_soc_limits(self) -> None:
        """Set conservative SOC limits on the H3X integration when entities exist."""
        charge_entity = str(self._option(CONF_CHARGE_LIMIT_SOC_ENTITY)).strip()
        discharge_entity = str(self._option(CONF_DISCHARGE_LIMIT_SOC_ENTITY)).strip()
        max_soc = float(self._option(CONF_MAX_SOC))
        floor_soc = max(float(self._option(CONF_MIN_SOC)), float(self._option(CONF_RESERVE_SOC)))

        if charge_entity and self.hass.states.get(charge_entity) is not None:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"value": round(max_soc)},
                target={"entity_id": charge_entity},
                blocking=True,
            )
        if discharge_entity and self.hass.states.get(discharge_entity) is not None:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"value": round(floor_soc)},
                target={"entity_id": discharge_entity},
                blocking=True,
            )

    async def _set_ems_mode(self, mode: str) -> None:
        """Set EMS mode if it changed."""
        entity_id = str(self._option(CONF_EMS_MODE_ENTITY)).strip()
        if not entity_id:
            return
        state = self.hass.states.get(entity_id)
        if state and state.state == mode and self._last_ems_mode == mode:
            return
        await self.hass.services.async_call(
            "select",
            "select_option",
            {"option": mode},
            target={"entity_id": entity_id},
            blocking=True,
        )
        self._last_ems_mode = mode

    async def _set_power_ref(self, percent: float) -> None:
        """Set signed charge/discharge power reference percentage."""
        entity_id = str(self._option(CONF_POWER_REF_ENTITY)).strip()
        if not entity_id:
            raise RuntimeError("power reference entity is not configured")

        percent = round(percent, 1)
        state = self.hass.states.get(entity_id)
        current = None
        if state and state.state not in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            try:
                current = float(state.state)
            except ValueError:
                current = None
        if current is not None and abs(current - percent) < 0.2:
            self._last_power_percent = percent
            return
        if self._last_power_percent is not None and abs(self._last_power_percent - percent) < 0.2:
            return

        await self.hass.services.async_call(
            "number",
            "set_value",
            {"value": percent},
            target={"entity_id": entity_id},
            blocking=True,
        )
        self._last_power_percent = percent
