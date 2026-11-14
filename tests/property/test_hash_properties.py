from decimal import Decimal

from hypothesis import HealthCheck, given, settings, strategies as st

from finkernel.fir.canonicalizer import canonical_decimal, canonical_json
from finkernel.psl.compiler.compiler import PSLCompiler
from helpers import dump
import copy
import yaml
import os

_PHOENIX = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "phoenix_autocall_worst_of",
                        "phoenix_autocall.yaml")
_BASE = yaml.safe_load(open(_PHOENIX, encoding="utf-8").read())
_COMPILER = PSLCompiler()
_BASE_HASH = _COMPILER.compile(dump(_BASE)).fir.contract_hash


@given(st.decimals(allow_nan=False, allow_infinity=False, min_value=-10**12, max_value=10**12, places=6),
       st.integers(min_value=0, max_value=6))
def test_canonical_decimal_ignores_trailing_zeros(d, extra):
    padded = d.quantize(Decimal(1).scaleb(-(6 + extra)))
    assert canonical_decimal(d) == canonical_decimal(padded)
    assert "e" not in canonical_decimal(d).lower()


@given(st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), min_size=1, max_size=8), st.randoms())
def test_canonical_json_invariant_to_key_order(d, rnd):
    items = list(d.items())
    rnd.shuffle(items)
    assert canonical_json(dict(items)) == canonical_json(d)


@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(st.permutations([0, 1, 2]), st.permutations([0, 1, 2]), st.randoms())
def test_contract_hash_invariant_under_non_significant_orderings(p_ul, p_ref, rnd):
    d = copy.deepcopy(_BASE)
    d["underlyings"] = [d["underlyings"][i] for i in p_ul]
    d["reference"]["underlyings"] = [d["reference"]["underlyings"][i] for i in p_ref]
    keys = list(d.keys())
    rnd.shuffle(keys)
    d = {k: d[k] for k in keys}
    r = _COMPILER.compile(dump(d))
    assert r.success and r.fir.contract_hash == _BASE_HASH


@settings(max_examples=40, deadline=None)
@given(st.integers(min_value=1, max_value=10**9))
def test_notional_is_hash_sensitive(n):
    d = copy.deepcopy(_BASE)
    d["contract"]["notional"]["amount"] = n
    h = _COMPILER.compile(dump(d)).fir.contract_hash
    assert (h == _BASE_HASH) == (n == 100000)
