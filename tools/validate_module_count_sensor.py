#!/usr/bin/env python3
"""Validate Force H3 module-count wiring across bridge and arbitrage repos."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "custom_components" / "pylontech_h3x_bridge"
ARBITRAGE = ROOT / "h3x-energy-arbitrage" / "custom_components" / "h3x_energy_arbitrage"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(source: str, token: str, label: str) -> None:
    if token not in source:
        raise AssertionError(f"{label} missing {token!r}")


def main() -> None:
    coordinator = read(BRIDGE / "coordinator.py")
    sensor = read(BRIDGE / "sensor.py")
    manifest = read(BRIDGE / "manifest.json")

    require(coordinator, "BMS_ESS_BASE_ADDRESS = 0x1400", "bridge coordinator")
    require(coordinator, "BMS_MODULE_NUMBER_OFFSET = 0x0036", "bridge coordinator")
    require(
        coordinator,
        "REGISTER_BMS_MODULE_NUMBER = BMS_ESS_BASE_ADDRESS + BMS_MODULE_NUMBER_OFFSET",
        "bridge coordinator",
    )
    require(
        coordinator,
        "REGISTER_BMS_MODULE_NUMBER, 1, 1",
        "bridge coordinator module-count read",
    )
    require(
        coordinator,
        'data["battery_module_count"] = get_16bit_uint(r_bms_modules, 0)',
        "bridge coordinator module-count data",
    )
    require(sensor, 'key="battery_module_count"', "bridge sensor")
    require(sensor, 'name="Battery Module Count"', "bridge sensor")
    require(manifest, '"version": "0.3.2"', "bridge manifest")

    if not ARBITRAGE.exists():
        print("arbitrage repo not present; skipped cross-repo validation")
        return

    arbitrage_const = read(ARBITRAGE / "const.py")
    arbitrage_coordinator = read(ARBITRAGE / "coordinator.py")
    require(
        arbitrage_const,
        '"sensor.pylontech_h3x_bridge_battery_module_count"',
        "arbitrage default module-count entity",
    )
    require(
        arbitrage_coordinator,
        "module_count_from_entity = self._state_float(module_entity)",
        "arbitrage module-count read",
    )
    require(
        arbitrage_coordinator,
        "capacity_kwh=self._capacity_for_modules(modules)",
        "arbitrage module-count capacity application",
    )


if __name__ == "__main__":
    main()
