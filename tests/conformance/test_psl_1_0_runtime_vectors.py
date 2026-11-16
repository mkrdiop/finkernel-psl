"""Independent standard-library oracle for PSL 1.0 runtime conformance vectors.

These pure reference functions test the published contract. They are not production
runtime code and intentionally fail closed where PSL 1.0 does not define economics.
"""
from __future__ import annotations

import calendar
import hashlib
import itertools
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import unittest

VECTORS = json.loads(
    (Path(__file__).parent / "psl_1_0_runtime_vectors.json").read_text(encoding="utf-8")
)


class ContractError(ValueError):
    pass


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def calendar_hash(bundle: dict) -> str:
    payload = {key: bundle[key] for key in ("id", "version", "weekend", "holidays", "range")}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_calendar(bundle: dict | None, supplied_hash: str | None = None) -> dict:
    if bundle is None:
        raise ContractError("REJECT_CALENDAR_MISSING")
    actual = calendar_hash(bundle)
    expected = supplied_hash or bundle.get("expected_hash")
    if not expected or actual != expected:
        raise ContractError("REJECT_CALENDAR_HASH_MISMATCH")
    return {
        "weekend": set(bundle["weekend"]),
        "holidays": {date.fromisoformat(item) for item in bundle["holidays"]},
        "start": date.fromisoformat(bundle["range"][0]),
        "end": date.fromisoformat(bundle["range"][1]),
    }


def in_range(day: date, cal: dict) -> None:
    if not cal["start"] <= day <= cal["end"]:
        raise ContractError("REJECT_CALENDAR_OUT_OF_RANGE")


def is_business_day(day: date, cal: dict) -> bool:
    in_range(day, cal)
    return day.weekday() not in cal["weekend"] and day not in cal["holidays"]


def adjust_date(day: date, convention: str, cal: dict) -> date:
    in_range(day, cal)
    if convention == "unadjusted":
        return day
    if convention not in {"following", "preceding", "modified_following", "modified_preceding"}:
        raise ContractError("REJECT_UNSUPPORTED_CONVENTION")
    if is_business_day(day, cal):
        return day

    def walk(step: int) -> date:
        candidate = day
        while True:
            candidate += timedelta(days=step)
            if is_business_day(candidate, cal):
                return candidate

    if convention in {"following", "modified_following"}:
        candidate = walk(1)
        if convention == "modified_following" and candidate.month != day.month:
            return walk(-1)
        return candidate
    candidate = walk(-1)
    if convention == "modified_preceding" and candidate.month != day.month:
        return walk(1)
    return candidate


def anchored_schedule(anchor: date, count: int, interval_months: int) -> list[str]:
    if count < 1 or interval_months not in {1, 3, 6, 12}:
        raise ContractError("REJECT_UNSUPPORTED_FREQUENCY")
    anchor_eom = anchor.day == calendar.monthrange(anchor.year, anchor.month)[1]
    result = []
    for index in range(count):
        month_index = anchor.year * 12 + anchor.month - 1 + index * interval_months
        year, month0 = divmod(month_index, 12)
        month = month0 + 1
        last = calendar.monthrange(year, month)[1]
        day = last if anchor_eom else min(anchor.day, last)
        result.append(date(year, month, day).isoformat())
    return result


def adjusted_schedule(nominal: list[date], convention: str, cal: dict) -> list[date]:
    adjusted = [adjust_date(item, convention, cal) for item in nominal]
    if len(adjusted) != len(set(adjusted)):
        raise ContractError("REJECT_SCHEDULE_COLLISION")
    return adjusted


def settlement_date(anchor: date, lag: int, unit: str, convention: str, cal: dict) -> date:
    if lag < 0 or unit not in {"business_days", "calendar_days"}:
        raise ContractError("REJECT_INVALID_PAYMENT_LAG")
    in_range(anchor, cal)
    current = anchor
    if unit == "calendar_days":
        current += timedelta(days=lag)
        in_range(current, cal)
    else:
        added = 0
        while added < lag:
            current += timedelta(days=1)
            in_range(current, cal)
            if is_business_day(current, cal):
                added += 1
    return adjust_date(current, convention, cal)


def fixing_key(record: dict) -> tuple:
    return (record["underlying"], record["date"], record["price_field"], record["source"])


def admit_fixing(requested: dict, records: list[dict]) -> str:
    matches = [record for record in records if fixing_key(record) == fixing_key(requested)]
    if not matches:
        return "REJECT_MISSING_FIXING"
    if len(matches) != 1:
        return "REJECT_DUPLICATE_FIXING"
    Decimal(matches[0]["value"])
    return "ACCEPT"


def admit_basket(required: list[str], records: list[dict], requested_date: str,
                 price_field: str, source: str) -> str:
    admitted = {}
    for underlying in required:
        request = {"underlying": underlying, "date": requested_date,
                   "price_field": price_field, "source": source}
        candidates = [record for record in records if record["underlying"] == underlying]
        result = admit_fixing(request, candidates)
        if result != "ACCEPT":
            return "REJECT_INCOMPLETE_BASKET" if result == "REJECT_MISSING_FIXING" else result
        admitted[underlying] = next(record for record in candidates if fixing_key(record) == fixing_key(request))
    return "ACCEPT" if len(admitted) == len(required) else "REJECT_INCOMPLETE_BASKET"


PHASE = {
    "INITIAL_FIXING": 0, "OBSERVATION_FIXING": 0,
    "COUPON_EVALUATION": 1, "COUPON_PAYMENT": 1,
    "AUTOCALL_EVALUATION": 1, "AUTOCALL_REDEMPTION": 1,
    "MATURITY_EVALUATION": 1, "MATURITY_REDEMPTION": 1,
    "CASHFLOW_SETTLEMENT": 2,
}


def order_events(events: list[dict], same_date_priority: list[str]) -> list[dict]:
    required = {"coupon", "autocall", "capital_redemption"}
    if len(same_date_priority) != 3 or set(same_date_priority) != required:
        raise ContractError("REJECT_INVALID_SAME_DATE_PRIORITY")
    rank = {component: index for index, component in enumerate(same_date_priority)}
    def key(event):
        phase = PHASE[event["kind"]]
        component_rank = rank.get(event.get("component"), -1)
        return (event["date"], phase, event.get("observation_index", -1), component_rank,
                event.get("component_id", ""), event.get("event_id", ""))
    return sorted(events, key=key)


def reduce_same_date(vector: dict) -> dict:
    priority = vector["priority"]
    if len(priority) != 3 or set(priority) != {"coupon", "autocall", "capital_redemption"}:
        raise ContractError("REJECT_INVALID_SAME_DATE_PRIORITY")
    memory = Decimal(vector["memory_before"])
    coupon_obligation = Decimal("0")
    principal_obligation = Decimal("0")
    processed = []
    state = "ACTIVE"
    for component in priority:
        if state != "ACTIVE":
            break
        if component == "coupon":
            processed.append("coupon")
            current = Decimal(vector["current_coupon"])
            if vector["coupon_eligible"]:
                coupon_obligation += memory + current
                memory = Decimal("0")
            else:
                memory += current
        elif component == "autocall" and vector["autocall_triggers"]:
            processed.append("autocall")
            if vector["autocall_unpaid_coupon_policy"] == "pay_all":
                coupon_obligation += memory
            memory = Decimal("0")
            principal_obligation = Decimal(vector["principal_amount"])
            state = "TERMINATED_AUTOCALL"
        elif component == "capital_redemption" and vector["capital_redemption_triggers"]:
            processed.append("capital_redemption")
            principal_obligation = Decimal(vector["principal_amount"])
            state = "MATURED"
    return {
        "processed": processed, "state": state,
        "coupon": format(coupon_obligation, "f"),
        "principal": format(principal_obligation, "f"),
        "memory": format(memory, "f"),
    }


def lifecycle_transition(current: str, event: str) -> str:
    if current == "FAILED":
        return "REJECT_FAILED_RUN"
    if current in {"TERMINATED_AUTOCALL", "MATURED"}:
        return "REJECT_POST_TERMINAL"
    if current == "PENDING" and event == "PREFLIGHT_PASS":
        return "ACTIVE"
    if current == "PENDING" and event == "TECHNICAL_ERROR":
        return "FAILED"
    if current == "ACTIVE" and event == "AUTOCALL_REDEMPTION":
        return "TERMINATED_AUTOCALL"
    if current == "ACTIVE" and event == "MATURITY_REDEMPTION":
        return "MATURED"
    if current == "ACTIVE" and event == "TECHNICAL_ERROR":
        return "FAILED"
    if current == "ACTIVE" and event == "CONTRACTUAL_EVENT":
        return "ACTIVE"
    raise ContractError("REJECT_INVALID_LIFECYCLE_TRANSITION")


def deterministic_event_id(event: dict) -> str:
    required = ("contract_hash", "schema", "kind", "component", "observation_index",
                "nominal_date", "effective_date", "payment_date", "calendar_hash", "fixing_hash")
    if any(key not in event for key in required):
        raise ContractError("REJECT_INCOMPLETE_EVENT_IDENTITY")
    return hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()


class IdempotencyLedger:
    def __init__(self):
        self.events = {}
        self.actions = set()

    def apply(self, event_id: str, content: dict, action_key: tuple) -> str:
        encoded = canonical_json(content)
        if event_id in self.events:
            if self.events[event_id] == encoded:
                return "IDEMPOTENT_NOOP"
            return "REJECT_EVENT_ID_COLLISION"
        if action_key in self.actions:
            return "REJECT_DUPLICATE_ACTION"
        self.events[event_id] = encoded
        self.actions.add(action_key)
        return "APPLIED"


def execution_eligibility(features: dict) -> str:
    if features["day_count"] == "30_360" or features["stub_required"]:
        return "REJECT_PSL1_EXECUTION_INELIGIBLE"
    if any(features[key] for key in ("independent_fixing_calendar", "per_currency_quanto",
                                     "fallback_hierarchy", "discretionary_early_termination",
                                     "unsupported_event")):
        return "REJECT_PSL1_EXECUTION_INELIGIBLE"
    rounding = features["rounding"]
    if not isinstance(rounding.get("precision"), int) or rounding["precision"] < 0:
        return "REJECT_PSL1_EXECUTION_INELIGIBLE"
    if rounding.get("mode") not in {"half_even", "half_up", "down"}:
        return "REJECT_PSL1_EXECUTION_INELIGIBLE"
    quantum = Decimal(1).scaleb(-rounding["precision"])
    # If every contractual amount is already exactly representable at the declared
    # precision, the unresolved stage cannot change the result. Otherwise fail closed.
    if any(Decimal(amount) != Decimal(amount).quantize(quantum)
           for amount in rounding["exact_amounts"]):
        return "REJECT_PSL1_EXECUTION_INELIGIBLE"
    return "ELIGIBLE"


class RuntimeContractVectors(unittest.TestCase):
    def setUp(self):
        self.bundle = VECTORS["calendar"]
        self.cal = validate_calendar(self.bundle)

    def test_schedule_generation_and_frequency_vectors(self):
        for vector in VECTORS["schedule_vectors"]:
            with self.subTest(vector=vector["id"]):
                if "frequency_months" in vector:
                    actual = anchored_schedule(date.fromisoformat(vector["anchor"]),
                                                vector["count"], vector["frequency_months"])
                    self.assertEqual(actual, vector["expected"])
                elif vector["id"] == "SCH-COLLISION-001":
                    nominal = [date.fromisoformat(item) for item in vector["nominal"]]
                    with self.assertRaisesRegex(ContractError, "REJECT_SCHEDULE_COLLISION"):
                        adjusted_schedule(nominal, vector["convention"], self.cal)
                elif vector["id"] == "SCH-RANGE-001":
                    with self.assertRaisesRegex(ContractError, vector["expected"]):
                        adjust_date(date.fromisoformat(vector["date"]), "following", self.cal)

    def test_calendar_adjustment_vectors(self):
        for vector in VECTORS["adjustment_vectors"]:
            with self.subTest(vector=vector["id"]):
                if vector["expected"].startswith("REJECT"):
                    if vector["expected"] == "REJECT_CALENDAR_MISSING":
                        with self.assertRaisesRegex(ContractError, vector["expected"]):
                            validate_calendar(None)
                    else:
                        with self.assertRaisesRegex(ContractError, vector["expected"]):
                            validate_calendar(self.bundle, vector["provided_hash"])
                else:
                    actual = adjust_date(date.fromisoformat(vector["date"]),
                                         vector["convention"], self.cal)
                    self.assertEqual(actual.isoformat(), vector["expected"])

    def test_settlement_vectors(self):
        for vector in VECTORS["settlement_vectors"]:
            with self.subTest(vector=vector["id"]):
                actual = settlement_date(date.fromisoformat(vector["anchor"]),
                                         vector["lag"], vector["unit"],
                                         vector["convention"], self.cal)
                self.assertEqual(actual.isoformat(), vector["expected"])

    def test_observation_and_settlement_calendars_are_independent(self):
        roles = VECTORS["calendar_roles"]
        with self.subTest(vector=roles["id"], rule=roles["rule"]):
            observation = validate_calendar(roles["observation"])
            settlement = validate_calendar(roles["settlement"])
            self.assertNotEqual(calendar_hash(roles["observation"]), calendar_hash(roles["settlement"]))
            day = date.fromisoformat(roles["date"])
            self.assertEqual(adjust_date(day, "following", observation).isoformat(),
                             roles["observation_adjusted"])
            self.assertEqual(adjust_date(day, "following", settlement).isoformat(),
                             roles["settlement_adjusted"])

    def test_exact_fixing_key_and_basket_vectors(self):
        for vector in VECTORS["fixing_vectors"]:
            with self.subTest(vector=vector["id"]):
                if "requested" in vector:
                    actual = admit_fixing(vector["requested"], vector["records"])
                else:
                    actual = admit_basket(vector["required_underlyings"], vector["records"],
                                          vector["requested_date"], vector["price_field"],
                                          vector["source"])
                self.assertEqual(actual, vector["expected"])

    def test_phase_order_vector(self):
        vector = VECTORS["phase_vectors"][0]
        actual = sorted(vector["input"], key=lambda event: (PHASE[event], vector["input"].index(event)))
        self.assertEqual(actual, vector["expected"])

    def test_same_date_priority_is_applied_to_event_queue(self):
        for vector in VECTORS["event_sort_vectors"]:
            with self.subTest(vector=vector["id"]):
                actual = order_events(vector["events"], vector["priority"])
                self.assertEqual([item["event_id"] for item in actual], vector["expected"])

    def test_all_six_priorities_execute_through_reducer(self):
        vectors = VECTORS["event_vectors"]
        actual_permutations = {tuple(item["priority"]) for item in vectors}
        self.assertEqual(actual_permutations,
                         set(itertools.permutations(("coupon", "autocall", "capital_redemption"))))
        for vector in vectors:
            with self.subTest(vector=vector["id"]):
                actual = reduce_same_date(vector)
                self.assertEqual(actual["processed"], vector["expected_processed"])
                self.assertEqual(actual["state"], vector["expected_state"])
                self.assertEqual(actual["coupon"], vector["expected_coupon_obligation"])
                self.assertEqual(actual["principal"], vector["expected_principal_obligation"])
                self.assertEqual(actual["memory"], vector["expected_memory_after"])

    def test_lifecycle_transition_vectors(self):
        for vector in VECTORS["lifecycle_vectors"]:
            with self.subTest(vector=vector["id"]):
                actual = lifecycle_transition(vector["from"], vector["event"])
                self.assertEqual(actual, vector["expected"])

    def test_event_identity_and_idempotency_vectors(self):
        for vector in VECTORS["identity_vectors"]:
            with self.subTest(vector=vector["id"]):
                event = vector["event"]
                event_id = deterministic_event_id(event)
                self.assertEqual(event_id, vector["expected_event_id"])
                ledger = IdempotencyLedger()
                action = (event["component"], event["observation_index"], event["kind"])
                self.assertEqual(ledger.apply(event_id, event, action), "APPLIED")
                if vector["id"] == "IDEMP-REPLAY-001":
                    self.assertEqual(ledger.apply(event_id, event, action), vector["expected"])
                elif vector["id"] == "IDEMP-COLLISION-001":
                    self.assertEqual(ledger.apply(event_id, vector["changed_event"], action), vector["expected"])
                else:
                    self.assertEqual(ledger.apply(event_id + "-distinct", event, action), vector["expected"])

    def test_execution_eligibility_vectors(self):
        for vector in VECTORS["eligibility_vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(execution_eligibility(vector["features"]), vector["expected"])

    def test_vector_ids_and_rule_coverage_are_unique(self):
        groups = ("schedule_vectors", "adjustment_vectors", "settlement_vectors",
                  "fixing_vectors", "event_vectors", "event_sort_vectors", "phase_vectors",
                  "lifecycle_vectors", "identity_vectors", "eligibility_vectors")
        vectors = [item for group in groups for item in VECTORS[group]] + [VECTORS["calendar_roles"]]
        ids = [item["id"] for item in vectors]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item.get("rule") for item in vectors))


if __name__ == "__main__":
    unittest.main()
