# Pylontech H3X Energy Dashboard

`pylontech-h3x-energy.yaml` is the default Lovelace dashboard for the optional energy-arbitrage stack.

`pylontech-h3x-energy-plotly.yaml` is an alternative dashboard built around Plotly Graph Card. It keeps controls and diagnostics concise and uses Plotly's unified hover, zooming, range selector buttons, and multi-axis traces to combine prices, dispatch, battery power, and SOC in one view.

It shows:

- current and future dynamic electricity prices,
- current optimizer decision and reason,
- planned charge/discharge slots,
- estimated arbitrage value for today and for the active horizon,
- battery power and state-of-charge over time,
- Pylontech H3X Bridge controls and diagnostics.

## Requirements

1. Install this repository through HACS for `pylontech_h3x_bridge`.
2. Install the optional `https://github.com/shuffleznl/h3x-energy-arbitrage` custom repository through HACS if you want the price/decision/savings cards to populate.
3. Install `apexcharts-card` from HACS for the default dashboard charts.
4. Install `Plotly Graph Card` from HACS if you want to use the Plotly dashboard.

The default dashboard uses ApexCharts for price, dispatch, power, and SOC history. The Plotly dashboard requires `custom:plotly-graph`.

## Install The YAML Dashboard

Copy `dashboards/pylontech-h3x-energy.yaml` into your Home Assistant config directory, for example:

```text
config/dashboards/pylontech-h3x-energy.yaml
```

Then add this to `configuration.yaml`:

```yaml
lovelace:
  mode: storage
  dashboards:
    pylontech-h3x-energy:
      mode: yaml
      title: Pylontech H3X Energy
      icon: mdi:battery-charging-70
      show_in_sidebar: true
      filename: dashboards/pylontech-h3x-energy.yaml
```

Restart Home Assistant or reload Lovelace resources after installing `apexcharts-card`.

To install the Plotly variant, copy `dashboards/pylontech-h3x-energy-plotly.yaml` and add a second dashboard:

```yaml
lovelace:
  mode: storage
  dashboards:
    pylontech-h3x-energy-plotly:
      mode: yaml
      title: Pylontech H3X Energy Plotly
      icon: mdi:chart-timeline-variant
      show_in_sidebar: true
      filename: dashboards/pylontech-h3x-energy-plotly.yaml
```

Install `Plotly Graph Card` through HACS before opening the Plotly dashboard.

## Planned Slot Display

The optimizer exposes a full `dispatch_plan` with one row per price interval, including idle rows. The dashboards intentionally hide idle rows in the visible planned-action tables and show only charge/discharge actions plus the dedicated next charge, next discharge, and periodic full-charge sensors. The full plan is still used by the charts.

Planned values can change when Nord Pool publishes new prices, the battery SOC changes, the house load changes, or grid-limit sensors update.

## Entity IDs

The dashboard assumes the default entity IDs created by:

- `pylontech_h3x_bridge`
- `h3x_energy_arbitrage`

For the arbitrage integration, Home Assistant prefixes entities with the device name by default, for example `sensor.pylontech_h3x_energy_arbitrage_decision` and `sensor.pylontech_h3x_energy_arbitrage_price_plan`.

If Home Assistant adds suffixes such as `_2`, edit the dashboard YAML and replace the entity IDs.
