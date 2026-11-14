"""Sérialisation canonique (blueprint §4.6).

Règles : clés triées, aucun ``float`` (TypeError), décimaux normalisés en chaîne
sans exposant ni zéros inutiles (``100000.00`` et ``100000`` sont identiques),
dates en ISO-8601, enums par valeur, JSON compact ASCII.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("Non-finite decimal cannot be canonicalized.")
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def to_canonical(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return to_canonical(obj.model_dump(mode="python"))
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Decimal):
        return canonical_decimal(obj)
    if isinstance(obj, date):  # inclut datetime
        return obj.isoformat()
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        raise TypeError("Floats are forbidden in canonical content; use Decimal.")
    if isinstance(obj, dict):
        if not all(isinstance(k, str) for k in obj):
            raise TypeError("Canonical mappings must have string keys.")
        return {k: to_canonical(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [to_canonical(v) for v in obj]
    raise TypeError(f"Cannot canonicalize value of type {type(obj).__name__}.")


def canonical_json(obj: Any) -> str:
    return json.dumps(to_canonical(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
