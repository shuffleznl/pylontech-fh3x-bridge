#!/usr/bin/env python3
"""Validate Force H3X time-slot protocol helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import ast
import importlib.util
import sys


PROTOCOL_PATH = Path("custom_components/pylontech_h3x_bridge/protocol.py")
COORDINATOR_PATH = Path("custom_components/pylontech_h3x_bridge/coordinator.py")


def load_protocol():
    spec = importlib.util.spec_from_file_location(
        "pylontech_h3x_protocol", PROTOCOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def find_method(tree: ast.AST, class_name: str, method_name: str) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"Missing {class_name}.{method_name}")


def main() -> None:
    protocol = load_protocol()

    slot4 = protocol.time_slot_registers(4)
    assert slot4.enable == 40926
    assert slot4.start_time == 40927
    assert slot4.end_time == 40928
    assert slot4.mode == 40929
    assert slot4.power == 40930
    assert slot4.weekday == 40931

    start = datetime(2026, 5, 13, 10, 30, 5)
    end = datetime(2026, 5, 13, 11, 45, 5)
    assert protocol.encode_time_slot_values(
        start,
        end,
        mode=protocol.SLOT_MODE_CHARGE,
        power_percent=10,
        weekday_mask=protocol.WEEKDAY_ALL,
    ) == [0x0A1E, 0x0B2D, 0, 100, 0x7F]
    assert protocol.encode_realtime_registers(start) == [
        2026,
        0x050D,
        0x0A1E,
        0x0503,
    ]

    tree = ast.parse(COORDINATOR_PATH.read_text(), filename=str(COORDINATOR_PATH))
    method = find_method(tree, "PylontechCoordinator", "async_program_charge_slot")
    source = ast.unparse(method)

    required_tokens = [
        "REGISTER_REALTIME_YEAR",
        "registers.enable",
        "registers.start_time",
        "REGISTER_EMS_MODE",
        "settle_after=False",
        "SLOT_MODE_CHARGE",
    ]
    for token in required_tokens:
        if token not in source:
            raise AssertionError(f"Missing time-slot command token: {token}")


if __name__ == "__main__":
    main()
