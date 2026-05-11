# Force H3X Bridge and Energy Arbitrage for Home Assistant

This repository contains two deployable Home Assistant custom integrations for a Pylontech Force H3X system:

| Integration | Domain | Purpose |
| --- | --- | --- |
| Force H3X Bridge | `force_h3x_bridge` | Local Modbus TCP bridge for Force H3X sensors and controls. |
| Pylontech H3X Energy Arbitrage | `h3x_energy_arbitrage` | Nord Pool price optimizer that charges from grid when cheap and exports when expensive. |

The controller is dynamic. It does not use fixed clock times. Every update it fetches Nord Pool price indices for today and tomorrow, supports 15/30/60 minute price slots, optimizes the battery dispatch over the configured horizon, and applies the current slot decision to the H3X Modbus control entities.

## What It Controls

The arbitrage integration expects the Pylontech Force H3X to be exposed in Home Assistant through **Force H3X Bridge**.

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

## Required Home Assistant Integrations

1. Built-in `Nord Pool` integration.
2. `force_h3x_bridge` custom integration from this repository.
3. This `h3x_energy_arbitrage` custom integration.

Home Assistant's Nord Pool integration provides public market prices from Nord Pool and has a `get_price_indices_for_date` action with `15`, `30`, and `60` minute resolution. Nord Pool has transitioned European day-ahead trading to 15-minute market time units, so this integration defaults to 15-minute pricing.

Official references:

| Topic | Source |
| --- | --- |
| Nord Pool in Home Assistant, data fetching, and 15-minute MTU note | <https://www.home-assistant.io/integrations/nordpool/> |
| Home Assistant Modbus write actions | <https://www.home-assistant.io/integrations/modbus> |
| Nord Pool 15-minute MTU transition | <https://www.nordpoolgroup.com/en/trading/transition-to-15-minute-market-time-unit-mtu/> |

## Installation

1. Copy `custom_components/force_h3x_bridge` and `custom_components/h3x_energy_arbitrage` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration**.
4. Add **Force H3X Bridge** and enter the Modbus TCP IP/port.
5. Add **Pylontech H3X Energy Arbitrage**. If only one Nord Pool config entry exists, it is detected automatically.
6. Start arbitrage with `Enable automatic control` turned off for the first run, verify the diagnostic sensors, then enable control.

Created diagnostic entities include:

| Entity | Meaning |
| --- | --- |
| `sensor.pylontech_h3x_energy_arbitrage_decision` | `charge`, `discharge`, `idle`, or `failsafe` |
| `sensor.pylontech_h3x_energy_arbitrage_target_power` | Target AC power in watts |
| `sensor.pylontech_h3x_energy_arbitrage_target_power_percent` | Signed H3X power reference percentage |
| `sensor.pylontech_h3x_energy_arbitrage_current_price` | Current Nord Pool base price in currency/kWh |
| `sensor.pylontech_h3x_energy_arbitrage_price_resolution` | Active price slot duration |

Exact entity IDs can differ if Home Assistant resolves name conflicts.

## Recommended Starting Settings

These defaults are conservative for LiFePO4 service life and avoid spending cycle life on marginal spreads:

| Setting | Default | Reason |
| --- | ---: | --- |
| Minimum SOC | `15%` | Avoid deep cycling. |
| Reserve SOC | `20%` | Preserve backup/self-consumption headroom. |
| Maximum SOC | `90%` | Avoid unnecessary time near 100% SOC. |
| Round-trip efficiency | `0.90` | Typical AC-coupled battery/inverter assumption. |
| Cycle cost | `0.035` currency/kWh | Approximate degradation cost gate. Tune to your battery cost and warranty. |
| Extra margin | `0.015` currency/kWh | Avoid tiny or noisy arbitrage. |
| Continuous power | `11000 W` | Requested continuous charge/discharge cap. |
| Peak power | `13800 W` | Requested short peak cap. Used only when spreads exceed the extra peak margin. |
| Full-scale H3X power | `13800 W` | Maps `100%` H3X power reference to watts. Adjust if your inverter uses a different full scale. |
| Minimum charge temperature | `5 C` | Avoid cold LiFePO4 charging. The BMS remains the final safety layer. |
| Maximum BMS temperature | `45 C` | Stops active cycling when warm. |

For a larger battery stack, set `Battery capacity kWh` to the installed usable nominal capacity. The optimizer uses this to decide whether the current slot should be spent charging, exporting, or waiting.

## Grid Connection Protection

Set these if you want the controller to respect your site connection:

| Setting | Behavior |
| --- | --- |
| `grid_import_limit_w` | Charging is capped so `house_load + charge_power <= grid_import_limit_w`. |
| `grid_export_limit_w` | Discharging is capped so estimated grid export stays below the configured export limit. |

Use `0` to disable a limit. The default house-load sensor is the H3X `load_power` sensor, but you can replace it with your main-meter load sensor if that is more accurate.

Examples:

| Connection | Approximate power |
| --- | ---: |
| 3 x 25 A at 230 V | `17250 W` |
| 3 x 35 A at 230 V | `24150 W` |

## Strategy Details

The optimizer uses dynamic programming over the future price slots. It values charging as a buy-side cost and discharging as sell-side revenue after round-trip efficiency, cycle cost, and a configurable minimum margin. By default, the end of the optimization horizon must preserve the current battery energy, so the controller does not simply empty the battery into one expensive slot without planning a recharge.

Set `terminal_soc_mode` to:

| Mode | Behavior |
| --- | --- |
| `preserve_current` | Default. End the horizon at least as charged as now. |
| `reserve_only` | Allows net sale down to the configured reserve SOC when economics justify it. |

Peak power is allowed only when the spread between the cheapest and most expensive available slots exceeds the normal economic threshold plus `peak_extra_margin_per_kwh`.

## Operational Notes

- The controller sets H3X EMS mode to `User mode` while actively charging/discharging.
- While idle or failsafe it sets the power reference to `0%` and returns EMS mode to `Self-Consumption`.
- If Nord Pool data, SOC, or H3X control entities are unavailable, the controller enters `failsafe`.
- The Nord Pool integration normally publishes tomorrow's prices around 13:00 CET/CEST; before then, optimization uses the currently available horizon.
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
  h3x_energy_arbitrage/
    __init__.py
    config_flow.py
    const.py
    coordinator.py
    manifest.json
    sensor.py
    translations/en.json
```
