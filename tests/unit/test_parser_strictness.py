import pytest

from finkernel.core.errors import PSLSyntaxError
from finkernel.psl.parser.yaml_parser import parse_yaml_strict
from decimal import Decimal


@pytest.mark.parametrize("text,line", [
    ("a: 1\na: 2\n", 2),
    ("x:\n  y: 1\n  z: 2\n  y: 3\n", 4),
])
def test_duplicate_keys_rejected_with_line(text, line):
    with pytest.raises(PSLSyntaxError) as e:
        parse_yaml_strict(text)
    assert "Duplicate key" in str(e.value) and e.value.line == line


@pytest.mark.parametrize("text", [
    "",                                   # vide
    "- a\n- b\n",                         # racine non mapping
    "a:\n\t- b\n",                        # tabulation
    "a: &x 1\nb: *x\n",                   # alias
    "base: &b {k: 1}\nd:\n  <<: *b\n",    # merge key
    "1: x\n",                             # clé non-chaîne
    "true: x\n",
    "a: 1\n---\nb: 2\n",                  # multi-documents
    'a: !!python/object/apply:os.system ["echo pwned"]\n',  # exécution de code
])
def test_invalid_documents_rejected(text):
    with pytest.raises(PSLSyntaxError):
        parse_yaml_strict(text)


def test_yaml11_pitfalls_are_not_silently_coerced():
    d = parse_yaml_strict("id: NO\\nlag: 010\\nflag: yes\\nnum: 1e3\\nx: 100000.00\\n").data
    assert d["id"] == "NO"            # pas False
    assert d["lag"] == "010"          # pas 8 (octal)
    assert d["flag"] == "yes"         # pas True
    assert d["num"] == Decimal("1000")
    assert d["x"] == Decimal("100000.00") and isinstance(d["x"], Decimal)  # pas float


def test_unquoted_iso_date_is_rejected_by_parser():
    with pytest.raises(PSLSyntaxError, match="must be quoted"):
        parse_yaml_strict("day: 2027-01-15\\n")


def test_source_map_locates_nested_paths():
    pd = parse_yaml_strict("a:\n  b:\n    - x: 1\n    - x: 2\n")
    assert pd.source_map.locate("a.b[1].x") == (4, 7)
    assert pd.source_map.locate("a.b[9].zzz") == (2, 3)   # retombe sur l'ancêtre connu (a.b)
