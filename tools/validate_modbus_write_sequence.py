#!/usr/bin/env python3
"""Validate Force H3X Modbus write sequencing against the local emulator."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from h3x_modbus_emulator import build_registers, handle_client  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


protocol = load_module(
    "pylontech_h3x_protocol",
    ROOT / "custom_components" / "pylontech_h3x_bridge" / "protocol.py",
)
transport = load_module(
    "pylontech_h3x_transport",
    ROOT / "custom_components" / "pylontech_h3x_bridge" / "transport.py",
)


async def connect_client(port: int):
    client = transport.H3XModbusTcpClient(
        host="127.0.0.1",
        port=port,
        timeout=1,
    )
    if not await client.connect():
        raise AssertionError("Modbus test client failed to connect")
    return client


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
        client = await connect_client(port)
        try:
            await client.write_register(40907, 4, slave=2)

            await asyncio.sleep(0.2)

            await client.write_register(
                40901,
                protocol.encode_16bit_int(-500),
                slave=2,
            )
            result = await client.read_holding_registers(40901, 7, slave=2)
            if result[0] != protocol.encode_16bit_int(-500):
                raise AssertionError(f"40901 was {result[0]!r}")
            if result[6] != 4:
                raise AssertionError(f"40907 was {result[6]!r}")
        finally:
            client.close()
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
