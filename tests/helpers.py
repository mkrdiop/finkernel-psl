import re
from typing import Any

import yaml

DELETE = object()
_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _tokens(path: str):
    return [(m.group(1) if m.group(1) is not None else int(m.group(2))) for m in _TOKEN.finditer(path)]


def mutate(data: Any, path: str, value: Any) -> Any:
    """Modifie (ou supprime avec DELETE) data['a']['b'][1]['c'] depuis 'a.b[1].c'. Retourne data."""
    toks = _tokens(path)
    node = data
    for t in toks[:-1]:
        node = node[t]
    last = toks[-1]
    if value is DELETE:
        del node[last]
    else:
        node[last] = value
    return data


def dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def codes(result, severity=None):
    return [d.code for d in result.diagnostics if severity is None or d.severity.value == severity]
