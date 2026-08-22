"""Normalize KiCad command opcodes from the backend."""

from __future__ import annotations

from typing import Any

OP_ALIASES = {
    "modify_component": "add_component",
    "replace_component": "add_component",
    "update_component": "add_component",
    "change_component": "add_component",
}

STRIPPED_COMMAND_MARKERS = (
    "지원되지 않거나 안전하지 않은 명령",
    "unsupported opcode",
)


def normalize_command(command: dict[str, Any]) -> dict[str, Any]:
    mapped = dict(command)
    op = str(mapped.get("op") or "").strip()
    mapped["op"] = OP_ALIASES.get(op, op)
    return mapped


def normalize_commands(commands: list[Any]) -> list[dict[str, Any]]:
    return [normalize_command(item) for item in commands if isinstance(item, dict)]


def commands_were_stripped(content: str, commands: list[Any]) -> bool:
    if commands:
        return False
    text = content or ""
    return any(marker in text for marker in STRIPPED_COMMAND_MARKERS)
