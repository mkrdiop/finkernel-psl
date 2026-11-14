import yaml
from typing import Dict, Any
from finkernel.psl.parser.duplicate_keys import SafeDuplicateKeyLoader
from finkernel.core.errors import PSLSyntaxError

def parse_yaml_strict(yaml_content: str) -> Dict[str, Any]:
    try:
        data = yaml.load(yaml_content, Loader=SafeDuplicateKeyLoader)
        if not isinstance(data, dict):
            raise PSLSyntaxError("Root of PSL specification must be a YAML mapping.")
        return data
    except yaml.YAMLError as e:
        if hasattr(e, 'problem_mark') and e.problem_mark:
            raise PSLSyntaxError(f"YAML Syntax Error: {e.problem}", line=e.problem_mark.line+1, column=e.problem_mark.column+1)
        raise PSLSyntaxError(f"YAML Parsing Error: {str(e)}")
