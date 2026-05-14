# Pylontech H3X Bridge

This workspace includes **Pylontech H3X Bridge**, a renamed and patched Home Assistant custom integration for Pylontech Force H3X Modbus TCP.

```text
custom_components/pylontech_h3x_bridge/
```

It is based on `wietse108/HA-pylontech-force-H3X`, but uses its own domain (`pylontech_h3x_bridge`) so it can be installed without conflicting with the original integration. The patch changes the Modbus write path for the manufacturer-documented EMS control registers.

Repository metadata points to `https://github.com/shuffleznl/pylontech-fh3x-bridge`; code ownership is set to `@shufflez`, `@shuffleznl`, and `@openai`.

## Manufacturer Register Findings

From `ModBus-Protocol-Pylon-FH3X-V1.2_20250811.docx`:

| Register | Hex | Format | Meaning | Direction |
| --- | --- | --- | --- | --- |
| `40901` | `9FC5` | `S16`, unit `0.1Pn%` | Charge/discharge power reference | Positive = discharge, negative = charge |
| `40902` | `9FC6` | `U16`, `%` | Charge limit SOC | `50-100` |
| `40903` | `9FC7` | `U16`, `%` | EPS/discharge limit SOC | `5-100` |
| `40907` | `9FCB` | `U16` | EMS mode | `4 = User mode`, `5 = PN-Customer mode` |

The document also states the device only supports Modbus TCP, default external LAN IP is `172.22.184.210`, and port is `502`.

## Fixes Made

1. `40901` writes now use explicit signed 16-bit encoding.

   Example: a Home Assistant value of `-50.0%` becomes raw `-500`, encoded as the Modbus word `0xFE0C`. That is the correct two's-complement representation for an `S16` register.

2. Invalid register values are rejected instead of silently masked.

   Unsigned registers must be `0..65535`. Signed registers must be `-32768..32767`.

3. Nonzero `Charge/Discharge Power Ref` writes always set EMS mode register `40907` to `4` (`User mode`) before writing register `40901`.

   The manufacturer document says register `40901` must be set when EMS mode is active. The command path no longer trusts cached `ems_mode`; this is important because positive discharge can appear to work in other modes, while negative forced charge generally requires User mode.

4. The raw Modbus TCP transport discards stale duplicate transaction frames and skips immediate forced refreshes.

   Live H3X logs showed duplicate write responses arriving after the acknowledged write. The transport waits for the matching transaction id and lets the next scheduled poll confirm the final device state.

5. The integration now has an options flow for updating Modbus TCP host and port.

   Go to **Settings > Devices & services > Pylontech H3X Bridge > Configure** to change IP/port. The integration reloads after saving.

6. The default setup IP is now the manufacturer documented default `172.22.184.210`; default port remains `502`.

## Deployment

Copy this directory into Home Assistant:

```text
custom_components/pylontech_h3x_bridge
```

Then restart Home Assistant.

Because the domain is different, this integration can be installed next to the upstream `pylon_fh3x` integration at the Home Assistant filesystem level. For a live inverter, keep only one of them enabled per H3X. Concurrent polling/control sessions can leave stale Modbus TCP frames on the socket and trigger transaction-ID mismatch errors in PyModbus.

After restart:

1. Open **Settings > Devices & services**.
2. Check **Pylontech H3X Bridge** is loaded.
3. Use **Configure** to set or update IP/port.
4. Test `number.pylontech_h3x_bridge_charge_discharge_power_ref`:
   - `-10` should request charging at `10%` of nominal inverter power.
   - `0` should stop forced charge/discharge reference.
   - `10` should request discharging at `10%`.

The BMS and inverter remain the final safety layer. Start with small percentages and verify actual battery/grid power before enabling a fully automated arbitrage loop.
