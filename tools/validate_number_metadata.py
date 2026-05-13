#!/usr/bin/env python3
"""Validate critical Home Assistant number entity metadata."""

from __future__ import annotations

import ast
from pathlib import Path


NUMBER_PATH = Path("custom_components/force_h3x_bridge/number.py")


def literal_kw(call: ast.Call, name: str):
    for keyword in call.keywords:
        if keyword.arg == name:
            return ast.literal_eval(keyword.value)
    raise AssertionError(f"Missing keyword {name!r}")


def find_number_description(tree: ast.AST, key: str) -> ast.Call:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "PylontechNumberEntityDescription":
            continue
        if literal_kw(node, "key") == key:
            return node
    raise AssertionError(f"Missing number description for {key!r}")


def find_number_init(tree: ast.AST) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PylontechNumber":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    return item
    raise AssertionError("Missing PylontechNumber.__init__")


def find_method(tree: ast.AST, class_name: str, method_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == method_name
                ):
                    return item
    raise AssertionError(f"Missing {class_name}.{method_name}")


def has_call(node: ast.AST, method_name: str) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute) and func.attr == method_name:
            return True
    return False


def assigned_attr_name(node: ast.stmt) -> str | None:
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]

    for target in targets:
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            return target.attr

    if isinstance(node, ast.If):
        for child in node.body:
            if attr := assigned_attr_name(child):
                return attr

    return None


def main() -> None:
    tree = ast.parse(NUMBER_PATH.read_text(), filename=str(NUMBER_PATH))
    charge_ref = find_number_description(tree, "charge_discharge_power")

    assert literal_kw(charge_ref, "register_address") == 40901
    assert literal_kw(charge_ref, "native_min_value") == -100.0
    assert literal_kw(charge_ref, "native_max_value") == 100.0
    assert literal_kw(charge_ref, "native_step") == 1
    assert literal_kw(charge_ref, "scale") == 0.1
    assert literal_kw(charge_ref, "signed") is True
    assert literal_kw(charge_ref, "round_native_value") is True

    init = find_number_init(tree)
    attrs_before_super: set[str] = set()
    for statement in init.body:
        is_super_call = (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Attribute)
            and statement.value.func.attr == "__init__"
        )
        if is_super_call:
            break
        if attr := assigned_attr_name(statement):
            attrs_before_super.add(attr)

    expected = {
        "entity_description",
        "_attr_native_min_value",
        "_attr_native_max_value",
        "_attr_native_step",
        "_attr_native_unit_of_measurement",
        "_attr_mode",
    }
    missing = expected - attrs_before_super
    if missing:
        raise AssertionError(
            f"PylontechNumber.__init__ must assign before super(): {sorted(missing)}"
        )

    set_native_value = find_method(tree, "PylontechNumber", "async_set_native_value")
    if not has_call(set_native_value, "async_set_charge_discharge_power"):
        raise AssertionError(
            "charge_discharge_power must use the dedicated signed command path"
        )


if __name__ == "__main__":
    main()
