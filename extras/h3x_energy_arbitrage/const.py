"""Constants for the Pylontech H3X energy arbitrage integration."""

from homeassistant.const import Platform

DOMAIN = "h3x_energy_arbitrage"
NORDPOOL_DOMAIN = "nordpool"
PLATFORMS = [Platform.SENSOR]

CONF_NORDPOOL_CONFIG_ENTRY = "nordpool_config_entry"
CONF_AREA = "area"
CONF_CURRENCY = "currency"
CONF_RESOLUTION = "resolution"
CONF_CONTROL_ENABLED = "control_enabled"

CONF_EMS_MODE_ENTITY = "ems_mode_entity"
CONF_POWER_REF_ENTITY = "power_ref_entity"
CONF_SOC_ENTITY = "soc_entity"
CONF_LOAD_POWER_ENTITY = "load_power_entity"
CONF_BMS_TEMP_ENTITY = "bms_temperature_entity"
CONF_CHARGE_LIMIT_SOC_ENTITY = "charge_limit_soc_entity"
CONF_DISCHARGE_LIMIT_SOC_ENTITY = "discharge_limit_soc_entity"

CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"
CONF_MIN_SOC = "min_soc"
CONF_MAX_SOC = "max_soc"
CONF_RESERVE_SOC = "reserve_soc"
CONF_TERMINAL_SOC_MODE = "terminal_soc_mode"
CONF_ROUND_TRIP_EFFICIENCY = "round_trip_efficiency"
CONF_CYCLE_COST = "cycle_cost_per_kwh"
CONF_MIN_PROFIT_MARGIN = "min_profit_margin_per_kwh"
CONF_BUY_COST_ADDER = "buy_cost_adder_per_kwh"
CONF_SELL_COST_ADDER = "sell_cost_adder_per_kwh"

CONF_CONTINUOUS_POWER_W = "continuous_power_w"
CONF_PEAK_POWER_W = "peak_power_w"
CONF_ENABLE_PEAK_POWER = "enable_peak_power"
CONF_PEAK_EXTRA_MARGIN = "peak_extra_margin_per_kwh"
CONF_INVERTER_FULL_SCALE_POWER_W = "inverter_full_scale_power_w"
CONF_MIN_ACTIVE_POWER_W = "min_active_power_w"
CONF_GRID_IMPORT_LIMIT_W = "grid_import_limit_w"
CONF_GRID_EXPORT_LIMIT_W = "grid_export_limit_w"

CONF_HORIZON_HOURS = "horizon_hours"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
CONF_IDLE_EMS_MODE = "idle_ems_mode"
CONF_USER_EMS_MODE = "user_ems_mode"
CONF_MIN_CHARGE_TEMP_C = "min_charge_temperature_c"
CONF_MAX_BMS_TEMP_C = "max_bms_temperature_c"

DEFAULT_NORDPOOL_ENTRY = "auto"
DEFAULT_AREA = "auto"
DEFAULT_CURRENCY = "auto"
DEFAULT_RESOLUTION = 15

DEFAULT_EMS_MODE_ENTITY = "select.force_h3x_bridge_ems_mode"
DEFAULT_POWER_REF_ENTITY = "number.force_h3x_bridge_charge_discharge_power_ref"
DEFAULT_SOC_ENTITY = "sensor.force_h3x_bridge_battery_soc"
DEFAULT_LOAD_POWER_ENTITY = "sensor.force_h3x_bridge_load_power"
DEFAULT_BMS_TEMP_ENTITY = "sensor.force_h3x_bridge_bms_temperature"
DEFAULT_CHARGE_LIMIT_SOC_ENTITY = "number.force_h3x_bridge_charge_limit_soc"
DEFAULT_DISCHARGE_LIMIT_SOC_ENTITY = (
    "number.force_h3x_bridge_discharge_limit_soc_eps"
)

DEFAULTS = {
    CONF_NORDPOOL_CONFIG_ENTRY: DEFAULT_NORDPOOL_ENTRY,
    CONF_AREA: DEFAULT_AREA,
    CONF_CURRENCY: DEFAULT_CURRENCY,
    CONF_RESOLUTION: DEFAULT_RESOLUTION,
    CONF_CONTROL_ENABLED: True,
    CONF_EMS_MODE_ENTITY: DEFAULT_EMS_MODE_ENTITY,
    CONF_POWER_REF_ENTITY: DEFAULT_POWER_REF_ENTITY,
    CONF_SOC_ENTITY: DEFAULT_SOC_ENTITY,
    CONF_LOAD_POWER_ENTITY: DEFAULT_LOAD_POWER_ENTITY,
    CONF_BMS_TEMP_ENTITY: DEFAULT_BMS_TEMP_ENTITY,
    CONF_CHARGE_LIMIT_SOC_ENTITY: DEFAULT_CHARGE_LIMIT_SOC_ENTITY,
    CONF_DISCHARGE_LIMIT_SOC_ENTITY: DEFAULT_DISCHARGE_LIMIT_SOC_ENTITY,
    CONF_BATTERY_CAPACITY_KWH: 20.0,
    CONF_MIN_SOC: 15.0,
    CONF_MAX_SOC: 90.0,
    CONF_RESERVE_SOC: 20.0,
    CONF_TERMINAL_SOC_MODE: "preserve_current",
    CONF_ROUND_TRIP_EFFICIENCY: 0.90,
    CONF_CYCLE_COST: 0.035,
    CONF_MIN_PROFIT_MARGIN: 0.015,
    CONF_BUY_COST_ADDER: 0.0,
    CONF_SELL_COST_ADDER: 0.0,
    CONF_CONTINUOUS_POWER_W: 11000.0,
    CONF_PEAK_POWER_W: 13800.0,
    CONF_ENABLE_PEAK_POWER: True,
    CONF_PEAK_EXTRA_MARGIN: 0.05,
    CONF_INVERTER_FULL_SCALE_POWER_W: 13800.0,
    CONF_MIN_ACTIVE_POWER_W: 500.0,
    CONF_GRID_IMPORT_LIMIT_W: 0.0,
    CONF_GRID_EXPORT_LIMIT_W: 0.0,
    CONF_HORIZON_HOURS: 36.0,
    CONF_UPDATE_INTERVAL_MINUTES: 5.0,
    CONF_IDLE_EMS_MODE: "Self-Consumption",
    CONF_USER_EMS_MODE: "User mode",
    CONF_MIN_CHARGE_TEMP_C: 5.0,
    CONF_MAX_BMS_TEMP_C: 45.0,
}

NORDPOOL_AREAS = (
    "auto",
    "EE",
    "LT",
    "LV",
    "AT",
    "BE",
    "FR",
    "GER",
    "NL",
    "PL",
    "DK1",
    "DK2",
    "FI",
    "NO1",
    "NO2",
    "NO3",
    "NO4",
    "NO5",
    "SE1",
    "SE2",
    "SE3",
    "SE4",
    "SYS",
)

CURRENCIES = ("auto", "DKK", "EUR", "NOK", "PLN", "SEK")
RESOLUTIONS = (15, 30, 60)

NORDPOOL_CONF_AREAS = "areas"
NORDPOOL_CONF_CURRENCY = "currency"
