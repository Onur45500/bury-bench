"""Validate result JSON files against the bury-bench result contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RESULT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://bury-bench.dev/schemas/result.json",
    "title": "bury-bench result",
    "type": "object",
    "required": ["model", "provider", "fixtures", "aggregate"],
    "properties": {
        "model": {"type": "string"},
        "provider": {"type": "string"},
        "timestamp": {"type": "string"},
        "ruleset": {"type": "string"},
        "fixtures": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "category", "score", "rules"],
                "properties": {
                    "id": {"type": "string"},
                    "category": {"type": "string"},
                    "response_text": {"type": "string"},
                    "score": {"type": "number"},
                    "rules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "status"],
                            "properties": {
                                "name": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["passed", "failed", "not_applicable"],
                                },
                                "evidence": {"type": ["string", "null"]},
                                "weight": {"type": "number"},
                            },
                        },
                    },
                },
            },
        },
        "aggregate": {
            "type": "object",
            "required": ["overall"],
            "properties": {
                "overall": {"type": "number"},
                "per_category": {"type": "object"},
                "per_rule_fail_counts": {"type": "object"},
            },
        },
    },
}


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _check_type(value: Any, expected: str | list[str]) -> bool:
    options = expected if isinstance(expected, list) else [expected]
    actual = _type_name(value)
    if "number" in options and actual in {"number", "integer"}:
        return True
    if "integer" in options and actual == "integer":
        return True
    return actual in options


def validate_result_dict(data: Any, *, source: str = "<unknown>") -> list[str]:
    """Return a list of validation errors (empty means valid). No external JSON Schema lib."""
    errors: list[str] = []

    if not isinstance(data, dict):
        return [f"{source}: root must be an object"]

    for key in RESULT_SCHEMA["required"]:
        if key not in data:
            errors.append(f"{source}: missing required field {key!r}")

    if "model" in data and not isinstance(data["model"], str):
        errors.append(f"{source}: model must be a string")
    if "provider" in data and not isinstance(data["provider"], str):
        errors.append(f"{source}: provider must be a string")

    fixtures = data.get("fixtures")
    if fixtures is not None:
        if not isinstance(fixtures, list):
            errors.append(f"{source}: fixtures must be an array")
        else:
            for i, fx in enumerate(fixtures):
                prefix = f"{source}: fixtures[{i}]"
                if not isinstance(fx, dict):
                    errors.append(f"{prefix}: must be an object")
                    continue
                for req in ("id", "category", "score", "rules"):
                    if req not in fx:
                        errors.append(f"{prefix}: missing {req!r}")
                if "score" in fx and not _check_type(fx["score"], "number"):
                    errors.append(f"{prefix}: score must be a number")
                rules = fx.get("rules")
                if rules is not None:
                    if not isinstance(rules, list):
                        errors.append(f"{prefix}: rules must be an array")
                    else:
                        for j, rule in enumerate(rules):
                            rprefix = f"{prefix}.rules[{j}]"
                            if not isinstance(rule, dict):
                                errors.append(f"{rprefix}: must be an object")
                                continue
                            if "name" not in rule or "status" not in rule:
                                errors.append(f"{rprefix}: missing name/status")
                            status = rule.get("status")
                            if status is not None and status not in {
                                "passed",
                                "failed",
                                "not_applicable",
                            }:
                                errors.append(f"{rprefix}: invalid status {status!r}")

    aggregate = data.get("aggregate")
    if aggregate is not None:
        if not isinstance(aggregate, dict):
            errors.append(f"{source}: aggregate must be an object")
        elif "overall" not in aggregate:
            errors.append(f"{source}: aggregate.overall is required")
        elif not _check_type(aggregate["overall"], "number"):
            errors.append(f"{source}: aggregate.overall must be a number")

    return errors


def validate_result_file(path: Path | str) -> list[str]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON ({exc})"]
    return validate_result_dict(data, source=str(path))
