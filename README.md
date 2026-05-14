# Pylontech H3X Bridge and Energy Arbitrage for Home Assistant

This repository contains the HACS-installable **Pylontech H3X Bridge** Home Assistant custom integration for a Pylontech Force H3X system.

| Integration | Domain | Purpose |
| --- | --- | --- |
| Pylontech H3X Bridge | `pylontech_h3x_bridge` | Local Modbus TCP bridge for Force H3X sensors and controls. |

The Nord Pool arbitrage controller now lives in its own HACS repository: `https://github.com/shuffleznl/h3x-energy-arbitrage`. HACS integration repositories can only manage one integration under `custom_components/`, so Pylontech H3X Bridge and the arbitrage controller are installed separately.

Pylontech H3X Bridge exposes the H3X sensors and writable Modbus controls needed by Home Assistant automations and external optimizers.

## What It Controls

Default entity IDs are based on a clean Pylontech H3X Bridge install:

| Purpose | Default entity |
| --- | --- |
| EMS mode | `select.pylontech_h3x_bridge_ems_mode` |
| Charge/discharge power | `number.pylontech_h3x_bridge_charge_discharge_power_ref` |
| Battery SOC | `sensor.pylontech_h3x_bridge_battery_soc` |
| House load | `sensor.pylontech_h3x_bridge_load_power` |
| Battery module count | `sensor.pylontech_h3x_bridge_battery_module_count` |
| Battery system capacity | `sensor.pylontech_h3x_bridge_battery_system_capacity` |
| Battery usable capacity | `sensor.pylontech_h3x_bridge_battery_usable_capacity` |
| BMS temperature | `sensor.pylontech_h3x_bridge_bms_temperature` |
| Charge SOC limit | `number.pylontech_h3x_bridge_charge_limit_soc` |
| Discharge SOC limit | `number.pylontech_h3x_bridge_discharge_limit_soc_eps` |

The H3X integration writes Modbus register `40907` for EMS mode and `40901` for the signed charge/discharge power reference. It must be in `User mode` while forcing charge or discharge.

## HACS Installation

1. In HACS, add `https://github.com/shuffleznl/pylontech-fh3x-bridge` as a custom repository of type **Integration**.
2. Install **Pylontech H3X Bridge**.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration**.
5. Add **Pylontech H3X Bridge** and enter the Modbus TCP IP/port.

## Optional Energy Dashboard

A Lovelace dashboard is provided in:

```text
dashboards/force-h3x-energy.yaml
```

It shows dynamic prices, current arbitrage decisions, planned charge/discharge slots, estimated value, battery power, and battery SOC. See [dashboards/README.md](dashboards/README.md) for installation.

The price and decision cards require the optional `h3x-energy-arbitrage` HACS integration. The rich charts use `apexcharts-card` from HACS; built-in history cards are included for battery power and SOC.

## Manual Installation

1. Copy `custom_components/pylontech_h3x_bridge` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration**.
4. Add **Pylontech H3X Bridge** and enter the Modbus TCP IP/port.

## Operational Notes

- Register `40901` is written as signed `S16`: negative values charge, positive values discharge.
- Home Assistant exposes `40901` as whole percent values from `-100` to `100`; the integration converts that to the raw Modbus `0.1Pn%` signed integer.
- The integration always sets EMS mode `40907` to `4` (`User mode`) before nonzero charge/discharge power writes.
- The integration uses a small raw Modbus TCP transport instead of PyModbus. Requests stay serialized on one socket, and late duplicate ACK frames are discarded until the matching transaction id is received.
- The integration performs its own locked write retries and keeps confirmation reads on the normal polling cycle.
- The BMS module count is read from ESS register `0x1436` / decimal `5174`, calculated as ESS base `0x1400` plus offset `0x0036` ("Module number in series").
- Total and usable capacity are derived from the Force H3 datasheet table for the detected module count. The derived usable capacity is checked against the 95% depth-of-discharge theoretical value and exposed with a deviation percentage.
- IP and port can be changed later from **Settings > Devices & services > Pylontech H3X Bridge > Configure**.
- Keep only one Modbus client connected to the inverter. Disable the original `pylon_fh3x` integration and other polling tools for the same H3X while using Pylontech H3X Bridge; concurrent TCP sessions can desynchronize Modbus transaction IDs.

## Time-Slot Services

Version `0.3.0` keeps the service-based control using the manufacturer time-slot registers and renames the Home Assistant domain to `pylontech_h3x_bridge`. These services are intended for controlled testing:

| Service | Purpose |
| --- | --- |
| `pylontech_h3x_bridge.force_charge_now` | Program a temporary charge slot, default slot `4`, default EMS mode `pn_customer` (`40907 = 5`). |
| `pylontech_h3x_bridge.test_force_charge_modes` | Program the same temporary charge slot first with EMS mode `5`, then with EMS mode `4`, and return measured snapshots. |
| `pylontech_h3x_bridge.clear_time_slot` | Disable one time slot. |

The slot command writes `40908-40931` style registers: disable slot, optionally sync inverter clock (`40932-40935`), write start/end/mode/power/weekday, set EMS mode, then enable the slot.

## Files

```text
custom_components/
  pylontech_h3x_bridge/
    __init__.py
    config_flow.py
    const.py
    coordinator.py
    manifest.json
    number.py
    select.py
    sensor.py
    switch.py
```
