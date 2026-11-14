"""Golden test : la FIR canonique du Phoenix et son hash sont figés.

Toute modification volontaire du schéma/de la sérialisation doit s'accompagner
d'une régénération explicite de ces fichiers (et d'un incrément de fir_version).
"""
import json
import os

from finkernel.fir.canonicalizer import canonical_json

HERE = os.path.dirname(__file__)


def test_phoenix_canonical_form_is_stable(compiler, phoenix_yaml):
    fir = compiler.compile(phoenix_yaml).fir
    expected = json.load(open(os.path.join(HERE, "phoenix_contract.canonical.json"), encoding="utf-8"))
    assert json.loads(canonical_json(fir.contract)) == expected


def test_phoenix_contract_hash_is_stable(compiler, phoenix_yaml):
    expected = open(os.path.join(HERE, "phoenix_contract.sha256"), encoding="utf-8").read().strip()
    assert compiler.compile(phoenix_yaml).fir.contract_hash == expected
