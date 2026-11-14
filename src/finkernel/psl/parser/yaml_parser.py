from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import yaml

from finkernel.core.errors import PSLSyntaxError
from finkernel.psl.parser.duplicate_keys import StrictPSLLoader
from finkernel.psl.parser.source_map import SourceMap


@dataclass(frozen=True)
class ParsedDocument:
    data: Dict[str, Any]
    source_map: SourceMap


def parse_yaml_strict(yaml_content: str) -> ParsedDocument:
    """Analyse strictement un document PSL.

    Lève ``PSLSyntaxError`` (avec ligne/colonne quand elles sont connues).
    Aucun code arbitraire n'est exécuté (SafeLoader + tags non sûrs rejetés).
    """
    loader = StrictPSLLoader(yaml_content)
    try:
        node = loader.get_single_node()
        if node is None:
            raise PSLSyntaxError("PSL specification is empty.", line=1, column=1)
        if not isinstance(node, yaml.MappingNode):
            raise PSLSyntaxError(
                "Root of PSL specification must be a YAML mapping.",
                line=node.start_mark.line + 1, column=node.start_mark.column + 1,
            )
        source_map = SourceMap.from_node(node)
        data = loader.construct_document(node)
        return ParsedDocument(data=data, source_map=source_map)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        if mark is not None:
            problem = getattr(e, "problem", None) or str(e)
            raise PSLSyntaxError(f"YAML Syntax Error: {problem}", line=mark.line + 1, column=mark.column + 1)
        raise PSLSyntaxError(f"YAML Parsing Error: {e}")
    finally:
        loader.dispose()
