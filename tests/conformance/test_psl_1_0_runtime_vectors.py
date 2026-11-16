"""Executable checks for the published PSL 1.0 runtime conformance vectors.

This is a specification oracle, not production runtime code. It deliberately uses
only the Python standard library so the vectors can be run independently.
"""
from __future__ import annotations

import calendar
import itertools
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import unittest

VECTORS = json.loads(
    (Path(__file__).parent / "psl_1_0_runtime_vectors.json").read_text(encoding="utf-8")
)


def monthly_dates(anchor: date, count: int) -> list[str]:
    anchor_eom = anchor.day == calendar.monthrange(anchor.year, anchor.month)[1]
    result = []
    for offset in range(count):
        month_index = anchor.year * 12 + (anchor.month - 1) + offset
        year, month0 = divmod(month_index, 12)
        month = month0 + 1
        last = calendar.monthrange(year, month)[1]
        day = last if anchor_eom else min(anchor.day, last)
        result.append(date(year, month, day).isoformat())
    return result


def add_business_days(anchor: date, lag: int, holidays: set[date], weekend: set[int]) -> date:
    current = anchor
    added = 0
    while added < lag:
        current += timedelta(days=1)
        if current.weekday() not in weekend and current not in holidays:
            added += 1
    return current


def adjust_following(day: date, holidays: set[date], weekend: set[int]) -> date:
    while day.weekday() in weekend or day in holidays:
        day += timedelta(days=1)
    return day


def event_phase_order(events: list[str]) -> list[str]:
    phase = {
        "INITIAL_FIXING": 0, "OBSERVATION_FIXING": 0,
        "COUPON_EVALUATION": 1, "COUPON_PAYMENT": 1,
        "AUTOCALL_EVALUATION": 1, "AUTOCALL_REDEMPTION": 1,
        "MATURITY_EVALUATION": 1, "MATURITY_REDEMPTION": 1,
        "CASHFLOW_SETTLEMENT": 2,
    }
    return sorted(events, key=lambda event: (phase[event], events.index(event)))


class RuntimeContractVectors(unittest.TestCase):
    def test_all_schedule_vectors(self):
        for vector in VECTORS["date_vectors"]:
            with self.subTest(vector=vector["id"]):
                if vector["kind"].startswith("monthly_"):
                    actual = monthly_dates(date.fromisoformat(vector["anchor"]), vector["count"])
                    self.assertEqual(actual, vector["expected"])
                elif vector["kind"] == "adjusted_date_collision":
                    self.assertEqual(len(set(vector["adjusted"])), 1)
                    self.assertEqual(vector["expected"], "REJECT_SCHEDULE_COLLISION")
                elif vector["kind"] == "calendar_out_of_range":
                    start, end = map(date.fromisoformat, vector["supported_range"])
                    value = date.fromisoformat(vector["date"])
                    self.assertFalse(start <= value <= end)
                    self.assertEqual(vector["expected"], "REJECT_CALENDAR_OUT_OF_RANGE")

    def test_settlement_vectors(self):
        for vector in VECTORS["settlement_vectors"]:
            with self.subTest(vector=vector["id"]):
                anchor = date.fromisoformat(vector["anchor"])
                weekend = set(vector["weekend"])
                holidays = {date.fromisoformat(item) for item in vector.get("holidays", [])}
                if vector["kind"] == "business_day_lag":
                    lagged = add_business_days(anchor, vector["lag"], holidays, weekend)
                    self.assertEqual(lagged.isoformat(), vector["expected_lag_date"])
                else:
                    lagged = anchor + timedelta(days=vector["lag"])
                if vector["convention"] == "following":
                    lagged = adjust_following(lagged, holidays, weekend)
                self.assertEqual(lagged.isoformat(), vector["expected_payment_date"])

    def test_fixing_cardinality_and_basket_vectors(self):
        for vector in VECTORS["fixing_vectors"]:
            with self.subTest(vector=vector["id"]):
                if vector["kind"] == "exactly_one":
                    actual = "ACCEPT" if vector["matching_records"] == 1 else "REJECT"
                elif vector["kind"] in {"missing", "prior_date_only"}:
                    actual = "REJECT_MISSING_FIXING"
                elif vector["kind"] in {"duplicate_equal_values", "conflicting_values"}:
                    actual = "REJECT_DUPLICATE_FIXING" if vector["matching_records"] > 1 else "ACCEPT"
                elif vector["kind"] == "partial_basket":
                    actual = "ACCEPT" if set(vector["required_underlyings"]) <= set(vector["present_underlyings"]) else "REJECT_INCOMPLETE_BASKET"
                self.assertEqual(actual, vector["expected"])

    def test_event_phase_order(self):
        vector = next(v for v in VECTORS["event_order_vectors"] if v["kind"] == "phase_order")
        self.assertEqual(event_phase_order(vector["input"]), vector["expected"])

    def test_all_six_priority_permutations_are_present(self):
        vector = next(v for v in VECTORS["event_order_vectors"] if v["kind"] == "all_priority_permutations")
        expected = list(itertools.permutations(("coupon", "autocall", "capital_redemption")))
        actual = [tuple(item) for item in vector["permutations"]]
        self.assertEqual(len(actual), 6)
        self.assertEqual(set(actual), set(expected))

    def test_coupon_autocall_precedence_vectors(self):
        coupon_first = next(v for v in VECTORS["event_order_vectors"] if v["kind"] == "coupon_before_autocall")
        autocall_first = next(v for v in VECTORS["event_order_vectors"] if v["id"] == "EVT-AUTOCALL-FIRST-001")
        obligation = Decimal(coupon_first["memory_before"]) + Decimal(coupon_first["current_coupon"])
        self.assertEqual(obligation, Decimal(coupon_first["expected_coupon_obligation"]))
        self.assertEqual(coupon_first["expected_memory_after_coupon"], "0")
        self.assertEqual(autocall_first["autocall_unpaid_coupon_policy"], "forfeit")
        self.assertEqual(autocall_first["expected_coupon_obligation"], "0")
        self.assertEqual(autocall_first["expected_autocall_unpaid_coupon_obligation"], "0")
        self.assertEqual(autocall_first["expected_memory_forfeited"], autocall_first["memory_before"])
        pay_all = next(v for v in VECTORS["event_order_vectors"] if v["kind"] == "autocall_before_coupon_pay_all")
        self.assertEqual(pay_all["autocall_unpaid_coupon_policy"], "pay_all")
        self.assertEqual(Decimal(pay_all["expected_autocall_unpaid_coupon_obligation"]), Decimal(pay_all["memory_before"]))
        self.assertEqual(pay_all["expected_coupon_obligation"], "0")

    def test_lifecycle_vectors(self):
        allowed = {
            ("PENDING", "preflight_pass"): "ACTIVE",
            ("ACTIVE", "autocall_redemption"): "TERMINATED_AUTOCALL",
            ("ACTIVE", "maturity_redemption"): "MATURED",
            ("ACTIVE", "technical_error"): "FAILED",
            ("TERMINATED_AUTOCALL", "contractual_event"): "REJECT_POST_TERMINAL",
            ("FAILED", "any_event"): "REJECT_FAILED_RUN",
        }
        for vector in VECTORS["lifecycle_vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(allowed[(vector["from"], vector["condition"])], vector["expected"])

    def test_idempotency_vectors(self):
        expected_by_kind = {
            "same_id_same_content": "IDEMPOTENT_NOOP",
            "same_id_different_content": "REJECT_EVENT_ID_COLLISION",
            "different_id_same_component_observation_action": "REJECT_DUPLICATE_ACTION",
        }
        for vector in VECTORS["idempotency_vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(expected_by_kind[vector["kind"]], vector["expected"])

    def test_execution_ineligible_features_fail_closed(self):
        vectors = VECTORS["eligibility_vectors"]
        self.assertGreaterEqual(len(vectors), 7)
        for vector in vectors:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(vector["expected"], "REJECT_PSL1_EXECUTION_INELIGIBLE")
                self.assertEqual(vector["future"], "PSL 1.1")

    def test_every_vector_has_unique_id_and_rule(self):
        groups = (
            "date_vectors", "settlement_vectors", "fixing_vectors",
            "event_order_vectors", "lifecycle_vectors", "idempotency_vectors",
            "eligibility_vectors",
        )
        all_vectors = [item for group in groups for item in VECTORS[group]]
        ids = [item["id"] for item in all_vectors]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item.get("rule") for item in all_vectors))


if __name__ == "__main__":
    unittest.main()
