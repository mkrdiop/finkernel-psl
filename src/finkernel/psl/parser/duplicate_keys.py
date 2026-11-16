"""Chargeur YAML strict pour le PSL (blueprint §4.1).

Écarts volontaires avec ``yaml.SafeLoader`` (YAML 1.1) :

* clés dupliquées rejetées, clés non-chaînes rejetées ;
* ancres/alias rejetés (pas d'expansion exponentielle, pas de merge ``<<``) ;
* ``yes/no/on/off`` restent des chaînes (problème « NO » = faux) ;
* les dates ISO non citées sont typées comme dates YAML et rejetées : PSL exige des dates citées ;
* les entiers sont en base 10 stricte (``010`` n'est PAS 8) ;
* les nombres décimaux sont lus comme ``Decimal`` depuis leur littéral exact,
  jamais comme ``float``.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

import yaml

from finkernel.core.errors import PSLSyntaxError

_STR_TAG = "tag:yaml.org,2002:str"


class StrictPSLLoader(yaml.SafeLoader):
    # Table de résolution implicite vide : on la reconstruit explicitement ci-dessous.
    yaml_implicit_resolvers = {}

    def compose_node(self, parent, index):
        event = self.peek_event()
        if getattr(event, "anchor", None) is not None:
            raise PSLSyntaxError(
                "YAML anchors and aliases are not allowed in PSL.",
                line=event.start_mark.line + 1,
                column=event.start_mark.column + 1,
            )
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            line, col = key_node.start_mark.line + 1, key_node.start_mark.column + 1
            if key_node.tag != _STR_TAG:
                raise PSLSyntaxError(
                    f"Mapping keys must be strings, got '{key_node.value}'.", line=line, column=col
                )
            key = key_node.value
            if key in seen:
                raise PSLSyntaxError(f"Duplicate key detected: '{key}' at line {line}", line=line, column=col)
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


_add = StrictPSLLoader.add_implicit_resolver
_add("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))
_add("tag:yaml.org,2002:null", re.compile(r"^(?:~|null|Null|NULL|)$"), ["~", "n", "N", ""])
_add("tag:yaml.org,2002:timestamp", re.compile(r"^\d{4}-\d{2}-\d{2}$"), list("0123456789"))
_add("tag:yaml.org,2002:int", re.compile(r"^[-+]?(?:0|[1-9][0-9]*)$"), list("-+0123456789"))
_add(
    "tag:yaml.org,2002:float",
    re.compile(r"^[-+]?(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+(?=[eE]))(?:[eE][-+]?[0-9]+)?$"),
    list("-+0123456789."),
)


def _construct_int(loader: yaml.Loader, node: yaml.Node) -> int:
    text = loader.construct_scalar(node)
    try:
        return int(text, 10)
    except ValueError:
        raise PSLSyntaxError(
            f"Invalid integer literal '{text}'.",
            line=node.start_mark.line + 1, column=node.start_mark.column + 1,
        )


def _construct_decimal(loader: yaml.Loader, node: yaml.Node) -> Decimal:
    text = loader.construct_scalar(node)
    try:
        value = Decimal(text)
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite():
        raise PSLSyntaxError(
            f"Invalid or non-finite numeric literal '{text}'.",
            line=node.start_mark.line + 1, column=node.start_mark.column + 1,
        )
    return value


def _reject_unquoted_date(loader: yaml.Loader, node: yaml.Node):
    raise PSLSyntaxError(
        "Date literals must be quoted using YYYY-MM-DD format.",
        line=node.start_mark.line + 1,
        column=node.start_mark.column + 1,
    )


StrictPSLLoader.add_constructor("tag:yaml.org,2002:timestamp", _reject_unquoted_date)
StrictPSLLoader.add_constructor("tag:yaml.org,2002:int", _construct_int)
StrictPSLLoader.add_constructor("tag:yaml.org,2002:float", _construct_decimal)

# Compatibilité avec l'ancien nom.
SafeDuplicateKeyLoader = StrictPSLLoader
