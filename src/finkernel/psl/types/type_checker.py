"""Contrôle de types sur les valeurs brutes du document (blueprint §4.3).

Chaque méthode retourne la valeur typée, ou ``None`` après avoir émis un
diagnostic. Une valeur absente (``MISSING``) retourne ``None`` sans bruit : le
champ manquant est déjà signalé par ``fields``.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar

from finkernel.core.diagnostics import DiagnosticBag

MISSING: Any = object()
E = TypeVar("E", bound=Enum)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")


def join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, Decimal):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "mapping"
    if isinstance(value, list):
        return "sequence"
    return type(value).__name__


class TypeChecker:
    def __init__(self, bag: DiagnosticBag) -> None:
        self.bag = bag

    # -- structure ---------------------------------------------------------
    def fields(self, raw: Any, path: str, required: Iterable[str] = (),
               optional: Iterable[str] = ()) -> Optional[Dict[str, Any]]:
        """Vérifie qu'on a un mapping, sans champ manquant ni champ inconnu."""
        if raw is MISSING:
            return None
        if not isinstance(raw, dict):
            self.bag.error("E-TYPE", f"Expected a mapping, got {type_name(raw)}.", path)
            return None
        required, optional = list(required), list(optional)
        for key in required:
            if key not in raw:
                self.bag.error("E-MISSING-FIELD", f"Missing required field '{key}'.", path)
        allowed = set(required) | set(optional)
        for key in raw:
            if key not in allowed:
                self.bag.error("E-UNKNOWN-FIELD",
                               f"Unknown field '{key}'. Allowed fields: {sorted(allowed)}.", join(path, key))
        return raw

    def free_mapping(self, raw: Any, path: str) -> Optional[Dict[str, Any]]:
        if raw is MISSING:
            return None
        if not isinstance(raw, dict):
            self.bag.error("E-TYPE", f"Expected a mapping, got {type_name(raw)}.", path)
            return None
        return raw

    def sequence(self, raw: Any, path: str, min_len: int = 1) -> Optional[List[Any]]:
        if raw is MISSING:
            return None
        if not isinstance(raw, list):
            self.bag.error("E-TYPE", f"Expected a sequence, got {type_name(raw)}.", path)
            return None
        if len(raw) < min_len:
            self.bag.error("E-EMPTY", f"Sequence must contain at least {min_len} item(s).", path)
            return None
        return raw

    # -- primitives ----------------------------------------------------------
    def string(self, raw: Any, path: str, hint: str = "") -> Optional[str]:
        if raw is MISSING:
            return None
        if not isinstance(raw, str):
            self.bag.error("E-TYPE", f"Expected a string, got {type_name(raw)}.{(' ' + hint) if hint else ''}", path)
            return None
        if not raw.strip():
            self.bag.error("E-EMPTY", "String must not be empty.", path)
            return None
        return raw

    def identifier(self, raw: Any, path: str) -> Optional[str]:
        value = self.string(raw, path)
        if value is None:
            return None
        if not _IDENTIFIER.match(value):
            self.bag.error("E-IDENTIFIER-FORMAT",
                           f"'{value}' is not a valid identifier (letters, digits, '_', '-', '.'; "
                           "must start with a letter or digit).", path)
            return None
        return value

    def boolean(self, raw: Any, path: str) -> Optional[bool]:
        if raw is MISSING:
            return None
        if not isinstance(raw, bool):
            self.bag.error("E-TYPE", f"Expected a boolean (true/false), got {type_name(raw)}.", path)
            return None
        return raw

    def integer(self, raw: Any, path: str, minimum: Optional[int] = None,
                maximum: Optional[int] = None) -> Optional[int]:
        if raw is MISSING:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int):
            self.bag.error("E-TYPE", f"Expected an integer, got {type_name(raw)}.", path)
            return None
        if (minimum is not None and raw < minimum) or (maximum is not None and raw > maximum):
            self.bag.error("E-RANGE", f"Value {raw} out of range [{minimum}, {maximum}].", path)
            return None
        return raw

    def decimal(self, raw: Any, path: str, *, minimum: Optional[Decimal] = None,
                maximum: Optional[Decimal] = None, exclusive_min: bool = False,
                hint: str = "") -> Optional[Decimal]:
        """Nombre décimal exact. Les chaînes et booléens sont refusés (pas de coercition)."""
        if raw is MISSING:
            return None
        if isinstance(raw, bool) or not isinstance(raw, (int, Decimal)):
            self.bag.error("E-TYPE", f"Expected a number, got {type_name(raw)}.", path)
            return None
        value = Decimal(raw)
        too_low = minimum is not None and (value <= minimum if exclusive_min else value < minimum)
        too_high = maximum is not None and value > maximum
        if too_low or too_high:
            lo = f"{'>' if exclusive_min else '>='} {minimum}" if minimum is not None else ""
            hi = f"<= {maximum}" if maximum is not None else ""
            bounds = " and ".join(b for b in (lo, hi) if b)
            self.bag.error("E-RANGE", f"Value {value} out of range: must be {bounds}.{(' ' + hint) if hint else ''}", path)
            return None
        return value

    def date(self, raw: Any, path: str) -> Optional[date]:
        """Date ISO-8601 stricte ``YYYY-MM-DD`` (jour/mois sur 2 chiffres, calendrier valide)."""
        if raw is MISSING:
            return None
        if not isinstance(raw, str):
            self.bag.error("E-TYPE", f"Expected a date string 'YYYY-MM-DD', got {type_name(raw)}.", path)
            return None
        if not _ISO_DATE.match(raw):
            self.bag.error("E-DATE-INVALID", f"'{raw}' is not an ISO-8601 date (expected YYYY-MM-DD).", path)
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            self.bag.error("E-DATE-INVALID", f"'{raw}' is not a valid calendar date.", path)
            return None

    def enum(self, raw: Any, path: str, cls: Type[E]) -> Optional[E]:
        if raw is MISSING:
            return None
        if not isinstance(raw, str):
            self.bag.error("E-TYPE", f"Expected a string, got {type_name(raw)}.", path)
            return None
        try:
            return cls(raw)
        except ValueError:
            allowed = [m.value for m in cls]
            self.bag.error("E-ENUM-VALUE", f"Unknown value '{raw}'. Allowed values: {allowed}.", path)
            return None
