import yaml
from finkernel.core.errors import PSLSyntaxError

class SafeDuplicateKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise PSLSyntaxError(
                    f"Duplicate key detected: '{key}' at line {key_node.start_mark.line + 1}",
                    line=key_node.start_mark.line + 1,
                    column=key_node.start_mark.column + 1
                )
            mapping.append(key)
        return super().construct_mapping(node, deep=deep)
