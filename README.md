# Force H3X Bridge and Energy Arbitrage for Home Assistant

This repository contains the HACS-installable **Force H3X Bridge** Home Assistant custom integration for a Pylontech Force H3X system.

| Integration | Domain | Purpose |
| --- | --- | --- |
| Force H3X Bridge | `force_h3x_bridge` | Local Modbus TCP bridge for Force H3X sensors and controls. |

The Nord Pool arbitrage controller from the initial prototype is kept in `extras/h3x_energy_arbitrage` and should be split into its own HACS repository before installing through HACS. HACS integration repositories can only manage one integration under `custom_components/`.

Force H3X Bridge exposes the H3X sensors and writable Modbus controls needed by Home Assistant automations and external optimizers.

## What It Controls

Default entity IDs are based on a clean Force H3X Bridge install:

| Purpose | Default entity |
| --- | --- |
| EMS mode | `select.force_h3x_bridge_ems_mode` |
| Charge/discharge power | `number.force_h3x_bridge_charge_discharge_power_ref` |
| Battery SOC | `sensor.force_h3x_bridge_battery_soc` |
| House load | `sensor.force_h3x_bridge_load_power` |
| BMS temperature | `sensor.force_h3x_bridge_bms_temperature` |
| Charge SOC limit | `number.force_h3x_bridge_charge_limit_soc` |
| Discharge SOC limit | `number.force_h3x_bridge_discharge_limit_soc_eps` |

The H3X integration writes Modbus register `40907` for EMS mode and `40901` for the signed charge/discharge power reference. It must be in `User mode` while forcing charge or discharge.

## HACS Installation

1. In HACS, add `https://github.com/shuffleznl/force-h3x-bridge` as a custom repository of type **Integration**.
2. Install **Force H3X Bridge**.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration**.
5. Add **Force H3X Bridge** and enter the Modbus TCP IP/port.

## Optional Energy Dashboard

A Lovelace dashboard is provided in:

```text
dashboards/force-h3x-energy.yaml
```

It shows dynamic prices, current arbitrage decisions, planned charge/discharge slots, estimated value, battery power, and battery SOC. See [dashboards/README.md](dashboards/README.md) for installation.

The price and decision cards require the optional `extras/h3x_energy_arbitrage` integration. The rich charts use `apexcharts-card` from HACS; built-in history cards are included for battery power and SOC.

## Manual Installation

1. Copy `custom_components/force_h3x_bridge` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration**.
4. Add **Force H3X Bridge** and enter the Modbus TCP IP/port.

## Operational Notes

- Register `40901` is written as signed `S16`: negative values charge, positive values discharge.
- The integration sets EMS mode `40907` to `4` (`User mode`) before nonzero charge/discharge power writes.
- IP and port can be changed later from **Settings > Devices & services > Force H3X Bridge > Configure**.
- Keep only one Modbus client connected to the inverter.

## Files

```text
custom_components/
  force_h3x_bridge/
    __init__.py
    config_flow.py
    const.py
    coordinator.py
    manifest.json
    number.py
    select.py
    sensor.py
    switch.py
extras/
  h3x_energy_arbitrage/
    __init__.py
    config_flow.py
    const.py
    coordinator.py
    manifest.json
    sensor.py
    translations/en.json
```
