"""Diagnostics structurés (blueprint §4.1, §4.4, §4.5).

Un diagnostic porte un code stable, une sévérité (erreur bloquante ou
avertissement), un chemin logique dans le document (``contract.notional.amount``)
et, quand la source est disponible, la ligne/colonne.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional, Tuple


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    path: str = ""
    line: Optional[int] = None
    column: Optional[int] = None

    def format(self) -> str:
        where = f" at '{self.path}'" if self.path else ""
        loc = f" (line {self.line}, col {self.column})" if self.line is not None else ""
        return f"[{self.code}] {self.message}{where}{loc}"


Locator = Callable[[str], Optional[Tuple[int, int]]]


class DiagnosticBag:
    """Collecteur de diagnostics; résout les positions via un ``Locator``."""

    def __init__(self, locator: Optional[Locator] = None) -> None:
        self._items: List[Diagnostic] = []
        self.locator = locator

    def _add(self, severity: Severity, code: str, message: str, path: str,
             line: Optional[int], column: Optional[int]) -> None:
        if line is None and self.locator is not None:
            pos = self.locator(path)
            if pos is not None:
                line, column = pos
        self._items.append(Diagnostic(code, severity, message, path, line, column))

    def error(self, code: str, message: str, path: str = "", *,
              line: Optional[int] = None, column: Optional[int] = None) -> None:
        self._add(Severity.ERROR, code, message, path, line, column)

    def warning(self, code: str, message: str, path: str = "", *,
                line: Optional[int] = None, column: Optional[int] = None) -> None:
        self._add(Severity.WARNING, code, message, path, line, column)

    @property
    def items(self) -> List[Diagnostic]:
        return list(self._items)

    @property
    def errors(self) -> List[Diagnostic]:
        return [d for d in self._items if d.severity is Severity.ERROR]

    @property
    def warnings(self) -> List[Diagnostic]:
        return [d for d in self._items if d.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return any(d.severity is Severity.ERROR for d in self._items)
