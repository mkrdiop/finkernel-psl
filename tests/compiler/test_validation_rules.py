"""Chaque entrée invalide relevée dans la revue de code doit produire un diagnostic précis."""
import pytest

from helpers import DELETE, codes, dump, mutate

COMP = "payoff.components"


def _compile(compiler, data, path, value):
    mutate(data, path, value)
    return compiler.compile(dump(data))


# (chemin, valeur, code d'erreur attendu)
CASES = [
    # --- structure / types ---
    ("contract.notional.amount", "100000", "E-TYPE"),
    ("contract.notional.amount", True, "E-TYPE"),
    ("psl_version", "2.0", "E-PSL-VERSION"),
    ("psl_version", DELETE, "E-MISSING-FIELD"),
    ("product", DELETE, "E-MISSING-FIELD"),
    ("contract.notional", DELETE, "E-MISSING-FIELD"),
    ("reference", DELETE, "E-MISSING-FIELD"),
    ("payoff.components", [], "E-EMPTY"),
    ("surprise_key", 1, "E-UNKNOWN-FIELD"),
    (f"{COMP}[1].typo_field", 1, "E-UNKNOWN-FIELD"),
    (f"{COMP}[0].annual_rate", "ten", "E-TYPE"),
    (f"{COMP}[0].memory.unpaid_coupon", DELETE, "E-MISSING-FIELD"),
    # --- dates ---
    ("contract.inception_date", "2027-13-45", "E-DATE-INVALID"),
    ("contract.maturity_date", "2027-1-5", "E-DATE-INVALID"),   # avant : jugé > "2027-01-15" par comparaison de chaînes
    ("contract.maturity_date", "2026-01-15", "E-DATE-ORDER"),
    ("schedule.observation_schedule.first_observation", "2026-12-01", "E-DATE-ORDER"),
    # --- vocabulaire fermé ---
    ("product.currency", "XYZ", "E-ENUM-VALUE"),
    ("schedule.observation_schedule.calendar", "MOON", "E-ENUM-VALUE"),
    ("schedule.observation_schedule.frequency", "whenever", "E-ENUM-VALUE"),
    ("reference.aggregation", "BEST_OFF", "E-ENUM-VALUE"),
    (f"{COMP}[0].type", "banana", "E-ENUM-VALUE"),
    ("risk.measures", ["delta", "astrology"], "E-ENUM-VALUE"),
    # --- domaines de valeurs ---
    ("contract.notional.amount", -5, "E-RANGE"),
    ("contract.notional.amount", 0, "E-RANGE"),
    ("contract.settlement.payment_lag", -3, "E-RANGE"),
    (f"{COMP}[0].condition.threshold", 7.0, "E-RANGE"),          # 700 %
    (f"{COMP}[0].condition.threshold", 0, "E-RANGE"),
    (f"{COMP}[0].annual_rate", 1.5, "E-RANGE"),
    (f"{COMP}[1].eligibility.start_observation", 0, "E-RANGE"),
    # --- devises ---
    ("contract.notional.currency", "USD", "E-CCY-MISMATCH"),
    ("contract.settlement.currency", "USD", "E-CCY-MISMATCH"),
    # --- identifiants / références ---
    ("underlyings[1].id", "SX5E", "E-DUPLICATE-ID"),
    (f"{COMP}[1].id", "coupon", "E-DUPLICATE-ID"),
    ("reference.underlyings[2]", "SX5E", "E-REF-DUPLICATE"),
    ("reference.underlyings[2]", "FOO", "E-REF-UNDECLARED"),
    (f"{COMP}[0].condition.reference", "best_of_performance", "E-REF-AGG-MISMATCH"),
    # --- règles contractuelles Phoenix ---
    (f"{COMP}[1]", DELETE, "E-CONTRACT-COMPONENTS"),                    # pas d'autocall
    (f"{COMP}[2]", DELETE, "E-CONTRACT-COMPONENTS"),                    # pas de remboursement : branche indéfinie
    (f"{COMP}[1].terminate_product", False, "E-AUTOCALL-NO-TERMINATION"),
    (f"{COMP}[1].eligibility.start_observation", 99, "E-AUTOCALL-START-RANGE"),
    (f"{COMP}[2].barrier.level", 1.5, "E-BARRIER-ORDER"),
]


@pytest.mark.parametrize("path,value,expected", CASES, ids=[f"{p}={v!r}"[:70] for p, v, _ in CASES])
def test_invalid_spec_is_rejected_with_expected_code(compiler, phoenix_data, path, value, expected):
    r = _compile(compiler, phoenix_data, path, value)
    assert not r.success and r.fir is None
    assert expected in codes(r, "error"), codes(r)
    assert "E-INTERNAL" not in codes(r)


def test_unquoted_dates_are_rejected(compiler, phoenix_yaml):
    assert '"2027-01-15"' in phoenix_yaml
    r = compiler.compile(phoenix_yaml.replace('"2027-01-15"', "2027-01-15").replace('"2032-01-15"', "2032-01-15"))
    assert not r.success and r.fir is None
    assert "E-SYNTAX" in codes(r, "error")


def test_unquoted_psl_version_gives_actionable_message(compiler, phoenix_yaml):
    r = compiler.compile(phoenix_yaml.replace('psl_version: "1.0"', "psl_version: 1.0"))
    assert "E-TYPE" in codes(r) and "Quote it" in r.errors[0].message


def test_maturity_off_grid_warns(compiler, phoenix_data):
    r = _compile(compiler, phoenix_data, "schedule.observation_schedule.first_observation", "2027-04-20")
    assert r.success and "W-SCHEDULE-GRID" in codes(r, "warning")


def test_unused_underlying_warns(compiler, phoenix_data):
    r = _compile(compiler, phoenix_data, "reference.underlyings", ["SX5E", "SPX"])
    assert r.success and "W-UL-UNUSED" in codes(r, "warning")


def test_unknown_subtype_is_rejected_for_execution(compiler, phoenix_data):
    r = _compile(compiler, phoenix_data, "product.subtype", "exotic_thing")
    assert not r.success and r.fir is None and "E-SUBTYPE-UNREGISTERED" in codes(r, "error")


def test_capital_barrier_above_coupon_barrier_warns(compiler, phoenix_data):
    r = _compile(compiler, phoenix_data, f"{COMP}[2].barrier.level", 0.8)
    assert r.success and "W-BARRIER-ORDER" in codes(r, "warning")


def test_valuation_and_risk_are_optional(compiler, phoenix_data):
    mutate(phoenix_data, "valuation", DELETE)
    mutate(phoenix_data, "risk", DELETE)
    r = compiler.compile(dump(phoenix_data))
    assert r.success and r.fir.valuation_hash is None and r.fir.risk_hash is None
