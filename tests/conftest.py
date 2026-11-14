import copy
import os
from datetime import datetime, timezone

import pytest
import yaml

from finkernel.psl.compiler.compiler import PSLCompiler

PHOENIX_PATH = os.path.join(os.path.dirname(__file__), "..", "examples", "phoenix_autocall_worst_of",
                            "phoenix_autocall.yaml")


@pytest.fixture(scope="session")
def phoenix_yaml() -> str:
    with open(PHOENIX_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture()
def phoenix_data(phoenix_yaml):
    """Dict modifiable du Phoenix (chargé avec le SafeLoader standard : seulement pour fabriquer des variantes)."""
    return copy.deepcopy(yaml.safe_load(phoenix_yaml))


@pytest.fixture()
def compiler() -> PSLCompiler:
    return PSLCompiler(clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc), id_factory=lambda: "test-compilation")
