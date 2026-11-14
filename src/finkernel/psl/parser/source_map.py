"""Table chemin logique -> (ligne, colonne), construite depuis l'arbre YAML composé."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import yaml


def _parent(path: str) -> str:
    if path.endswith("]"):
        return path[: path.rfind("[")]
    if "." in path:
        return path[: path.rfind(".")]
    return ""


class SourceMap:
    def __init__(self, positions: Dict[str, Tuple[int, int]]) -> None:
        self._pos = positions

    @classmethod
    def from_node(cls, root: yaml.Node) -> "SourceMap":
        out: Dict[str, Tuple[int, int]] = {"": (root.start_mark.line + 1, root.start_mark.column + 1)}
        cls._walk(root, "", out)
        return cls(out)

    @classmethod
    def _walk(cls, node: yaml.Node, path: str, out: Dict[str, Tuple[int, int]]) -> None:
        if isinstance(node, yaml.MappingNode):
            for key_node, value_node in node.value:
                key = str(key_node.value)
                p = f"{path}.{key}" if path else key
                out[p] = (key_node.start_mark.line + 1, key_node.start_mark.column + 1)
                cls._walk(value_node, p, out)
        elif isinstance(node, yaml.SequenceNode):
            for i, item in enumerate(node.value):
                p = f"{path}[{i}]"
                out[p] = (item.start_mark.line + 1, item.start_mark.column + 1)
                cls._walk(item, p, out)

    def locate(self, path: str) -> Optional[Tuple[int, int]]:
        """Position du chemin, ou de son plus proche ancêtre connu."""
        p = path
        while True:
            if p in self._pos:
                return self._pos[p]
            if not p:
                return None
            p = _parent(p)
