"""Grille nominale (non ajustée) des dates d'observation."""
from __future__ import annotations

import calendar
from datetime import date
from typing import List

from finkernel.psl.ast.nodes import ObservationSchedule


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def observation_dates(schedule: ObservationSchedule, maturity: date) -> List[date]:
    """Dates ``first + k*step`` (ancrées sur la première date pour éviter la dérive) jusqu'à la maturité incluse.

    Les ajustements de jour ouvré (calendrier/convention) relèvent du module
    ``calendars`` et ne changent pas le nombre d'observations.
    """
    step = schedule.frequency.months
    out: List[date] = []
    k = 0
    while True:
        try:
            d = add_months(schedule.first_observation, k * step)
        except ValueError:  # an > 9999
            break
        if d > maturity:
            break
        out.append(d)
        k += 1
    return out
