#!/usr/bin/env python3
"""Validate the dedicated Force H3X charge/discharge command path."""

from __future__ import annotations

import ast
from pathlib import Path


COORDINATOR_PATH = Path("custom_components/force_h3x_bridge/coordinator.py")


def find_method(tree: ast.AST, class_name: str, method_name: str) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"Missing {class_name}.{method_name}")


def literal_call_arg(call: ast.Call, index: int):
    return ast.literal_eval(call.args[index])


def main() -> None:
    tree = ast.parse(COORDINATOR_PATH.read_text(), filename=str(COORDINATOR_PATH))
    method = find_method(tree, "PylontechCoordinator", "async_set_charge_discharge_power")

    calls: list[ast.Call] = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_write_register_locked"
    ]

    if len(calls) < 2:
        raise AssertionError("charge/discharge command must write EMS mode and 40901")

    source = ast.unparse(method)
    if 'data.get("ems_mode")' in source or "data.get('ems_mode')" in source:
        raise AssertionError("charge command must not trust cached ems_mode")

    if "REGISTER_EMS_MODE" not in source or "EMS_MODE_USER" not in source:
        raise AssertionError("charge command must force EMS User mode")

    if "REGISTER_CHARGE_DISCHARGE_POWER" not in source:
        raise AssertionError("charge command must write the charge/discharge register")

    if "encode_16bit_int(value)" not in source:
        raise AssertionError("charge/discharge value must be encoded as signed S16")

    if "reset_after=False" not in source:
        raise AssertionError(
            "EMS mode and charge/discharge setpoint must be one command sequence"
        )


if __name__ == "__main__":
    main()
