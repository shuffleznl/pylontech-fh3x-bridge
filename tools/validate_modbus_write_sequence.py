#!/usr/bin/env python3
"""Validate Force H3X Modbus write sequencing against the local emulator."""

from __future__ import annotations

import asyncio
import struct

from pymodbus.client import AsyncModbusTcpClient

from h3x_modbus_emulator import build_registers, handle_client


async def modbus_read(client, address: int, count: int, slave: int):
    try:
        return await client.read_holding_registers(
            address=address, count=count, slave=slave
        )
    except TypeError:
        pass
    try:
        return await client.read_holding_registers(
            address=address, count=count, unit=slave
        )
    except TypeError:
        pass
    return await client.read_holding_registers(
        address=address, count=count, device_id=slave
    )


async def modbus_write_register(client, address: int, value: int, slave: int):
    try:
        return await client.write_register(address=address, value=value, slave=slave)
    except TypeError:
        pass
    try:
        return await client.write_register(address=address, value=value, unit=slave)
    except TypeError:
        pass
    return await client.write_register(address=address, value=value, device_id=slave)


def encode_s16(value: int) -> int:
    return struct.unpack(">H", struct.pack(">h", value))[0]


async def connect_client(port: int) -> AsyncModbusTcpClient:
    client = AsyncModbusTcpClient(
        host="127.0.0.1",
        port=port,
        timeout=1,
        retries=1,
        reconnect_delay=0.1,
        reconnect_delay_max=0.2,
    )
    if not await client.connect():
        raise AssertionError("Modbus test client failed to connect")
    return client


async def write_and_reconnect(port: int, address: int, value: int) -> None:
    client = await connect_client(port)
    try:
        result = await modbus_write_register(client, address, value, slave=2)
        if result.isError():
            raise AssertionError(f"Write {address} failed: {result}")
    finally:
        client.close()

    await asyncio.sleep(0.75)


async def main() -> None:
    registers = build_registers()
    server = await asyncio.start_server(
        lambda reader, writer: handle_client(
            reader,
            writer,
            registers,
            duplicate_write_response=True,
            duplicate_delay=0.05,
        ),
        "127.0.0.1",
        0,
    )
    port = server.sockets[0].getsockname()[1]

    try:
        await write_and_reconnect(port, 40907, 4)
        await write_and_reconnect(port, 40901, encode_s16(-500))

        client = await connect_client(port)
        try:
            result = await modbus_read(client, 40901, 7, slave=2)
            if result.isError():
                raise AssertionError(f"Readback failed: {result}")
            if result.registers[0] != encode_s16(-500):
                raise AssertionError(f"40901 was {result.registers[0]!r}")
            if result.registers[6] != 4:
                raise AssertionError(f"40907 was {result.registers[6]!r}")
        finally:
            client.close()
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
