"""Propriétés exigées par blueprint §4.6 / ADR-003 pour le hash de la FIR."""
import copy
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from finkernel.fir.canonicalizer import canonical_decimal, canonical_json
from finkernel.psl.compiler.compiler import PSLCompiler
from helpers import DELETE, dump, mutate


def h(compiler, data):
    r = compiler.compile(dump(data))
    assert r.success, [d.format() for d in r.errors]
    return r.fir


def test_hash_is_full_sha256(compiler, phoenix_yaml):
    assert len(compiler.compile(phoenix_yaml).fir.contract_hash) == 64


def test_hash_independent_of_compilation_time_and_id(phoenix_yaml):
    a = PSLCompiler(clock=lambda: datetime(2020, 1, 1, tzinfo=timezone.utc), id_factory=lambda: "a").compile(phoenix_yaml).fir
    b = PSLCompiler(clock=lambda: datetime(2030, 1, 1, tzinfo=timezone.utc), id_factory=lambda: "b").compile(phoenix_yaml).fir
    assert a.contract_hash == b.contract_hash and a.provenance != b.provenance


# Ce qui DOIT changer le hash : tout terme économique du contrat (dont ceux oubliés par la v1).
@pytest.mark.parametrize("path,value", [
    ("contract.notional.amount", 200000),
    ("contract.settlement.payment_lag", 5),                       # absent du hash v1
    ("contract.settlement.payment_lag_unit", "calendar_days"),    # absent du hash v1
    ("product.category", "other_category"),                       # absent du hash v1
    ("product.currency", "USD"),                                   # + devises alignées ci-dessous
    ("payoff.components[0].annual_rate", 0.08),
    ("payoff.components[0].condition.threshold", 0.65),
    ("payoff.components[2].barrier.level", 0.55),
    ("schedule.observation_schedule.business_day_convention", "following"),
    ("underlyings[0].market_identifier.value", "XX0000000000"),
])
def test_economic_terms_change_contract_hash(compiler, phoenix_data, path, value):
    base = h(compiler, phoenix_data).contract_hash
    d = copy.deepcopy(phoenix_data)
    mutate(d, path, value)
    if path == "product.currency":
        mutate(d, "contract.notional.currency", "USD")
        mutate(d, "contract.settlement.currency", "USD")
    assert h(compiler, d).contract_hash != base


# Ce qui NE DOIT PAS changer le hash du contrat (ADR-003) : valorisation, risque, métadonnées.
@pytest.mark.parametrize("path,value", [
    ("valuation.model.paths", 500000),
    ("valuation.model.method", "pde"),
    ("risk.measures", ["vega"]),
])
def test_pricing_and_risk_do_not_change_contract_hash(compiler, phoenix_data, path, value):
    base = h(compiler, phoenix_data)
    d = copy.deepcopy(phoenix_data)
    mutate(d, path, value)
    new = h(compiler, d)
    assert new.contract_hash == base.contract_hash
    # ... mais ils ont leurs propres empreintes
    if path.startswith("valuation"):
        assert new.valuation_hash != base.valuation_hash and new.risk_hash == base.risk_hash
    else:
        assert new.risk_hash != base.risk_hash and new.valuation_hash == base.valuation_hash


def test_metadata_does_not_change_contract_hash(compiler, phoenix_data):
    base = h(compiler, phoenix_data)
    d = copy.deepcopy(phoenix_data)
    d["metadata"] = {"author": "someone", "note": "free text"}
    new = h(compiler, d)
    assert new.contract_hash == base.contract_hash and new.metadata == d["metadata"]


def test_non_significant_orders_do_not_change_hash(compiler, phoenix_data):
    base = h(compiler, phoenix_data).contract_hash
    d = copy.deepcopy(phoenix_data)
    d["underlyings"].reverse()
    d["reference"]["underlyings"].reverse()
    d = {k: d[k] for k in reversed(list(d))}   # ordre des clés racine
    assert h(compiler, d).contract_hash == base


def test_decimal_formatting_does_not_change_hash(compiler, phoenix_yaml):
    a = compiler.compile(phoenix_yaml).fir.contract_hash
    b = compiler.compile(phoenix_yaml.replace("amount: 100000.00", "amount: 100000")).fir.contract_hash
    c = compiler.compile(phoenix_yaml.replace("amount: 100000.00", "amount: 1.0e5")).fir.contract_hash
    assert a == b == c


def test_source_hash_tracks_exact_source_but_normalizes_newlines(compiler, phoenix_yaml):
    a = compiler.compile(phoenix_yaml).fir.provenance.source_hash
    assert compiler.compile(phoenix_yaml.replace("\n", "\r\n")).fir.provenance.source_hash == a
    assert compiler.compile(phoenix_yaml + "\n# comment\n").fir.provenance.source_hash != a


def test_fir_contains_no_pricing_parameters(compiler, phoenix_yaml):
    blob = canonical_json(compiler.compile(phoenix_yaml).fir.contract)
    for forbidden in ("monte_carlo", "paths", "correlation", "value_at_risk", "valuation"):
        assert forbidden not in blob


def test_canonical_json_rejects_floats():
    with pytest.raises(TypeError):
        canonical_json({"x": 0.1})


@pytest.mark.parametrize("raw,expected", [
    ("100000.00", "100000"), ("1.0e5", "100000"), ("0.10", "0.1"), ("-0.0", "0"), ("0.000", "0"), ("12.5", "12.5"),
])
def test_canonical_decimal(raw, expected):
    assert canonical_decimal(Decimal(raw)) == expected
