"""DataUpdateCoordinator for Force H3X Bridge."""
import asyncio
import logging
import struct
from datetime import timedelta

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

MODBUS_RECONNECT_SETTLE_SECONDS = 0.75
MODBUS_WRITE_ATTEMPTS = 3

# =========================================================
# Helper functions for Modbus decoding
# =========================================================
def get_16bit_uint(regs, idx):
    return regs[idx]

def get_16bit_int(regs, idx):
    return struct.unpack('>h', struct.pack('>H', regs[idx]))[0]

def get_32bit_int(regs, idx):
    return struct.unpack('>i', struct.pack('>HH', regs[idx], regs[idx+1]))[0]

def get_32bit_float(regs, idx):
    return struct.unpack('>f', struct.pack('>HH', regs[idx], regs[idx+1]))[0]


def encode_16bit_uint(value: int) -> int:
    """Encode an unsigned 16-bit register value."""
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"U16 value out of range: {value}")
    return value


def encode_16bit_int(value: int) -> int:
    """Encode a signed 16-bit register value as the Modbus wire word."""
    if not -0x8000 <= value <= 0x7FFF:
        raise ValueError(f"S16 value out of range: {value}")
    return struct.unpack(">H", struct.pack(">h", value))[0]


async def _modbus_read(client, address, count, target_id):
    try:
        return await client.read_holding_registers(address=address, count=count, slave=target_id)
    except TypeError:
        pass
    try:
        return await client.read_holding_registers(address=address, count=count, unit=target_id)
    except TypeError:
        pass
    return await client.read_holding_registers(address=address, count=count, device_id=target_id)


async def _modbus_write_register(client, address, value, target_id):
    """Write one register across supported pymodbus keyword variants."""
    try:
        return await client.write_register(address=address, value=value, slave=target_id)
    except TypeError:
        pass
    try:
        return await client.write_register(address=address, value=value, unit=target_id)
    except TypeError:
        pass
    return await client.write_register(address=address, value=value, device_id=target_id)


async def _modbus_write_registers(client, address, values, target_id):
    """Write multiple registers across supported pymodbus keyword variants."""
    try:
        return await client.write_registers(address=address, values=values, slave=target_id)
    except TypeError:
        pass
    try:
        return await client.write_registers(address=address, values=values, unit=target_id)
    except TypeError:
        pass
    return await client.write_registers(address=address, values=values, device_id=target_id)


class PylontechCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Modbus data from the inverter."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.client = self._new_client()
        self._modbus_lock = asyncio.Lock()
        self._last_client_reset: float | None = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def _new_client(self) -> AsyncModbusTcpClient:
        """Create a fresh Modbus TCP client."""
        return AsyncModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=5,
            retries=1,
            reconnect_delay=0.5,
            reconnect_delay_max=5,
        )

    async def _ensure_connected(self) -> None:
        """Ensure the Modbus TCP client is connected."""
        if self.client.connected:
            return

        if self._last_client_reset is not None:
            elapsed = asyncio.get_running_loop().time() - self._last_client_reset
            if elapsed < MODBUS_RECONNECT_SETTLE_SECONDS:
                await asyncio.sleep(MODBUS_RECONNECT_SETTLE_SECONDS - elapsed)
            self._last_client_reset = None

        if not await self.client.connect():
            raise ModbusException(f"Failed to connect to {self.host}:{self.port}")
        if not self.client.connected:
            raise ModbusException(f"Connected client is not ready for {self.host}:{self.port}")

    def _reset_client(self) -> None:
        """Close and recreate the Modbus client after protocol desync/errors."""
        try:
            self.client.close()
        finally:
            self.client = self._new_client()
            self._last_client_reset = asyncio.get_running_loop().time()

    async def async_close(self) -> None:
        """Close the Modbus client safely."""
        async with self._modbus_lock:
            self.client.close()

    async def safe_read(self, address, count, slave):
        
        # 100ms pause
        await asyncio.sleep(0.1) 
        res = await _modbus_read(self.client, address, count, slave)
        if res.isError():
            _LOGGER.warning("error while reading adress %s (Slave %s): %s", address, slave, res)
            return None
        return res.registers

    async def _async_update_data(self):
        """Fetch data from the inverter via Modbus with serialized access."""
        async with self._modbus_lock:
            return await self._async_update_data_locked()

    async def _async_update_data_locked(self):
        """Fetch data from the inverter via Modbus."""
        try:
            await self._ensure_connected()

            data = {}

            
            # AC & Grid Power (30100 - 30101 en 30108 - 30109)
            r_ac = await self.safe_read(30100, 2, 2)
            if r_ac: data["ac_total_power"] = get_32bit_int(r_ac, 0)
            
            r_grid = await self.safe_read(30108, 2, 2)
            if r_grid: data["grid_total_power"] = get_32bit_int(r_grid, 0)

            #virtual sensor that combines ac power out of battery with grid power and thus get the load power.
            if "ac_total_power" in data and "grid_total_power" in data:
                data["load_power"] = data["ac_total_power"] + data["grid_total_power"]


            # Inverter Status (30115)
            r_status = await self.safe_read(30115, 1, 2)
            if r_status: data["inverter_status"] = get_16bit_uint(r_status, 0)

            # PV voltage & current (30119 t/m 30124)
            r_pv = await self.safe_read(30119, 6, 2)
            if r_pv:
                data["pv1_voltage"] = get_16bit_uint(r_pv, 0) * 0.1
                data["pv1_current"] = get_16bit_uint(r_pv, 1) * 0.1
                data["pv2_voltage"] = get_16bit_uint(r_pv, 2) * 0.1
                data["pv2_current"] = get_16bit_uint(r_pv, 3) * 0.1
                data["pv3_voltage"] = get_16bit_uint(r_pv, 4) * 0.1
                data["pv3_current"] = get_16bit_uint(r_pv, 5) * 0.1
            
            #virtual sensor to calculate pv1,2,3 power
            if r_pv:
                data["pv1_power"] = data["pv1_voltage"] * data["pv1_current"]
                data["pv2_power"] = data["pv2_voltage"] * data["pv2_current"]
                data["pv3_power"] = data["pv3_voltage"] * data["pv3_current"]


            # PV Power & Energy (30127 t/m 30130)
            r_pv_tot = await self.safe_read(30127, 4, 2)
            if r_pv_tot:
                data["pv_total_power"] = get_32bit_int(r_pv_tot, 0)
                data["pv_total_energy"] = get_32bit_float(r_pv_tot, 2)

            # Grid Voltages & Freq (30131 t/m 30140)
            r_grid_v = await self.safe_read(30131, 10, 2)
            if r_grid_v:
                data["grid_voltage_r"] = get_16bit_uint(r_grid_v, 0) * 0.1
                data["grid_voltage_s"] = get_16bit_uint(r_grid_v, 2) * 0.1
                data["grid_voltage_t"] = get_16bit_uint(r_grid_v, 4) * 0.1
                data["ac_frequency"] = get_16bit_uint(r_grid_v, 9) * 0.01

            # Temperature (30146)
            r_temp = await self.safe_read(30146, 2, 2)
            if r_temp: 
                data["inverter_temperature"] = get_16bit_int(r_temp, 0) * 0.1
                data["heatsink_temperature"] = get_16bit_int(r_temp, 1) * 0.1


            # Grid Energy In/Out (30156 t/m 30159)
            r_grid_e = await self.safe_read(30156, 4, 2)
            if r_grid_e:
                data["total_grid_import"] = get_32bit_float(r_grid_e, 0)
                data["total_grid_export"] = get_32bit_float(r_grid_e, 2)


            r_active = await self.safe_read(40400, 3, 2)
            if r_active:
                # 40400: Active power control mode (U16)
                data["active_power_control_mode"] = get_16bit_uint(r_active, 0)
                # 40401: Meter limit power (S32, 2 registers)
                data["meter_export_power_max"] = get_32bit_int(r_active, 1)


            BATTERY_STATUS_MAP = {
                            0: "Sleep",
                            1: "Charging",
                            2: "Discharging",
                            3: "Idle",
                            4: "Standby",
                            5: "Run",
                            6: "Fault",
                            7: "Offline",
                        }
            
            # Battery Status, Power, Voltage, Current (30161 t/m 30165)
            r_batt = await self.safe_read(30161, 5, 2)
            if r_batt:

                raw_status = get_16bit_uint(r_batt, 0)
                data["battery_status"] = BATTERY_STATUS_MAP.get(raw_status, f"Unknown ({raw_status})")

                data["battery_power"] = get_32bit_int(r_batt, 1)
                data["battery_voltage"] = get_16bit_uint(r_batt, 3) * 0.1
                data["battery_current"] = get_16bit_int(r_batt, 4) * 0.1

            # Load Power (30172)
            r_load = await self.safe_read(30172, 2, 2)
            if r_load: data["eps_power"] = get_32bit_int(r_load, 0)



            # Battery Energy (30174 t/m 30177)
            r_batt_e = await self.safe_read(30174, 4, 2)
            if r_batt_e:
                data["total_battery_charge"] = get_32bit_float(r_batt_e, 0)
                data["total_battery_discharge"] = get_32bit_float(r_batt_e, 2)

            # SOC & CT Currents (30182 t/m 30185)
            r_soc = await self.safe_read(30182, 4, 2)
            if r_soc:
                data["battery_soc"] = get_16bit_uint(r_soc, 0)


            # =========================================================
            # SLAVE 2 (inverter) - EMS Settings 
            # =========================================================
            r_ems = await self.safe_read(40901, 7, 2)
            if r_ems:
                # 40901 is S16 (Signed)
                data["charge_discharge_power"] = get_16bit_int(r_ems, 0)
                
                # De rest is U16 (Unsigned)
                data["charge_limit_soc"] = get_16bit_uint(r_ems, 1) #40902
                data["discharge_limit_soc"] = get_16bit_uint(r_ems, 2) #40903
                data["ems_mode"] = str(get_16bit_uint(r_ems, 6)) #40907


            #heatpump 
            r_hp = await self.safe_read(40848, 1, 2)
            if r_hp:
                data["heat_pump"] = get_16bit_uint(r_hp, 0)

            # charge / discharge periods
            r_p1 = await self.safe_read(40908, 1, 2)
            if r_p1:
                data["period_1"] = get_16bit_uint(r_p1, 0)

            r_p2 = await self.safe_read(40914, 1, 2)
            if r_p2:
                data["period_2"] = get_16bit_uint(r_p2, 0)

            r_p3 = await self.safe_read(40920, 1, 2)
            if r_p3:
                data["period_3"] = get_16bit_uint(r_p3, 0)

            r_p4 = await self.safe_read(40926, 1, 2)
            if r_p4:
                data["period_4"] = get_16bit_uint(r_p4, 0)


            # =========================================================
            # SLAVE 1 (BMS) 
            # =========================================================
            
            # BMS Voltage (5123 / 0x1403)
            r_bms_v = await self.safe_read(5123, 1, 1)
            if r_bms_v: data["bms_voltage"] = get_16bit_uint(r_bms_v, 0) * 0.1

            # BMS Temp, SOC, Cycles (5126 / 0x1406 t/m 0x1408)
            r_bms_t = await self.safe_read(5126, 3, 1)
            if r_bms_t:
                data["bms_temperature"] = get_16bit_int(r_bms_t, 0) * 0.1
                data["bms_soc"] = get_16bit_uint(r_bms_t, 1)
                data["bms_cycles"] = get_16bit_uint(r_bms_t, 2)

            # BMS Cell Volts (5136 / 0x1410 t/m 0x1411)
            r_bms_cv = await self.safe_read(5136, 2, 1)
            if r_bms_cv:
                data["bms_cell_voltage_max"] = get_16bit_uint(r_bms_cv, 0) * 0.001
                data["bms_cell_voltage_min"] = get_16bit_uint(r_bms_cv, 1) * 0.001

            # BMS SOH (5152 / 0x1420)
            r_bms_soh = await self.safe_read(5152, 1, 1)
            if r_bms_soh: data["bms_soh"] = get_16bit_uint(r_bms_soh, 0)

            
            if not data:
                raise UpdateFailed("No data received out of inverter.")

            return data

        except ModbusException as err:
            self._reset_client()
            raise UpdateFailed(f"error with modbus communication: {err}")
        except Exception as err:
            self._reset_client()
            raise UpdateFailed(f"unexpected error: {err}")

    async def async_write_register(
        self,
        address: int,
        value: int,
        slave: int = 2,
        signed: bool = False,
        refresh: bool = False,
    ) -> bool:
        """Write one 16-bit register.

        Pylontech documents register 40901 as S16: positive discharges and
        negative charges. pymodbus writes a Modbus register word, so signed
        values are encoded explicitly as two's-complement U16 words.

        The H3X can echo a duplicate write response after the acknowledged
        write. Reconnect after every write so the next read cannot consume
        stale write frames from the same TCP socket.
        """
        try:
            register_value = (
                encode_16bit_int(value) if signed else encode_16bit_uint(value)
            )

        except ValueError as err:
            _LOGGER.error("Invalid value for register %s: %s", address, err)
            return False

        success = False
        async with self._modbus_lock:
            for attempt in range(1, MODBUS_WRITE_ATTEMPTS + 1):
                try:
                    await self._ensure_connected()
                    res = await _modbus_write_register(
                        self.client, address, register_value, slave
                    )

                    self._reset_client()

                    if res.isError():
                        _LOGGER.error(
                            "Error writing register %s raw=%s encoded=%s signed=%s: %s",
                            address,
                            value,
                            register_value,
                            signed,
                            res,
                        )
                        return False

                    success = True
                    break

                except ModbusException as err:
                    self._reset_client()
                    if attempt == MODBUS_WRITE_ATTEMPTS:
                        _LOGGER.error(
                            "Modbus error while writing register %s after %s attempts: %s",
                            address,
                            attempt,
                            err,
                        )
                        return False
                    _LOGGER.warning(
                        "Modbus write register %s failed on attempt %s/%s; retrying: %s",
                        address,
                        attempt,
                        MODBUS_WRITE_ATTEMPTS,
                        err,
                    )
                except Exception as err:
                    self._reset_client()
                    if attempt == MODBUS_WRITE_ATTEMPTS:
                        _LOGGER.error(
                            "Unexpected error while writing register %s after %s attempts: %s",
                            address,
                            attempt,
                            err,
                        )
                        return False
                    _LOGGER.warning(
                        "Unexpected write failure for register %s on attempt %s/%s; retrying: %s",
                        address,
                        attempt,
                        MODBUS_WRITE_ATTEMPTS,
                        err,
                    )

        if success and refresh:
            await self.async_request_refresh()
        return success
        
    async def async_write_register_32bit(
        self,
        address: int,
        value: int,
        slave: int = 2,
        refresh: bool = False,
    ) -> bool:
        """Write a 32-bit signed value (S32) as two consecutive 16-bit registers."""
        # Pack S32 into two U16 registers (big-endian)
        packed = struct.pack('>i', value)
        high, low = struct.unpack('>HH', packed)

        success = False
        async with self._modbus_lock:
            for attempt in range(1, MODBUS_WRITE_ATTEMPTS + 1):
                try:
                    await self._ensure_connected()
                    res = await _modbus_write_registers(
                        self.client, address, [high, low], slave
                    )

                    self._reset_client()

                    if res.isError():
                        _LOGGER.error("Error writing 32-bit register %s: %s", address, res)
                        return False

                    success = True
                    break

                except ModbusException as err:
                    self._reset_client()
                    if attempt == MODBUS_WRITE_ATTEMPTS:
                        _LOGGER.error(
                            "Modbus error while writing 32-bit register %s after %s attempts: %s",
                            address,
                            attempt,
                            err,
                        )
                        return False
                    _LOGGER.warning(
                        "Modbus write 32-bit register %s failed on attempt %s/%s; retrying: %s",
                        address,
                        attempt,
                        MODBUS_WRITE_ATTEMPTS,
                        err,
                    )
                except Exception as err:
                    self._reset_client()
                    if attempt == MODBUS_WRITE_ATTEMPTS:
                        _LOGGER.error(
                            "Unexpected error writing 32-bit register %s after %s attempts: %s",
                            address,
                            attempt,
                            err,
                        )
                        return False
                    _LOGGER.warning(
                        "Unexpected write failure for 32-bit register %s on attempt %s/%s; retrying: %s",
                        address,
                        attempt,
                        MODBUS_WRITE_ATTEMPTS,
                        err,
                    )

        if success and refresh:
            await self.async_request_refresh()
        return success
