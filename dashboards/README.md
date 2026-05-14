# Force H3X Energy Dashboard

`force-h3x-energy.yaml` is a Lovelace dashboard for the optional energy-arbitrage stack.

It shows:

- current and future dynamic electricity prices,
- current optimizer decision and reason,
- planned charge/discharge slots,
- estimated arbitrage value for today and for the active horizon,
- battery power and state-of-charge over time,
- Force H3X Bridge controls and diagnostics.

## Requirements

1. Install this repository through HACS for `force_h3x_bridge`.
2. Install the optional `https://github.com/shuffleznl/h3x-energy-arbitrage` custom repository through HACS if you want the price/decision/savings cards to populate.
3. Install `apexcharts-card` from HACS for the richer charts.

The dashboard also includes built-in `history-graph` cards for battery power and SOC, so those trends still display without ApexCharts.

## Install The YAML Dashboard

Copy `dashboards/force-h3x-energy.yaml` into your Home Assistant config directory, for example:

```text
config/dashboards/force-h3x-energy.yaml
```

Then add this to `configuration.yaml`:

```yaml
lovelace:
  mode: storage
  dashboards:
    force-h3x-energy:
      mode: yaml
      title: Force H3X Energy
      icon: mdi:battery-charging-70
      show_in_sidebar: true
      filename: dashboards/force-h3x-energy.yaml
```

Restart Home Assistant or reload Lovelace resources after installing `apexcharts-card`.

## Entity IDs

The dashboard assumes the default entity IDs created by:

- `force_h3x_bridge`
- `h3x_energy_arbitrage`

If Home Assistant adds suffixes such as `_2`, edit the dashboard YAML and replace the entity IDs.
