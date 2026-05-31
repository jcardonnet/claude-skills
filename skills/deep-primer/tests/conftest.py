"""pytest bootstrap for the deep-primer skill.

Puts `scripts/` on sys.path so tests import the skill's modules the same way the registry
refers to them (`ir.schema`, `utils.parse_primer`, `checks.*`, ...). Keeps the skill
self-contained — no install step, no cross-skill imports.
"""
import sys
from pathlib import Path

import pytest

_SKILL_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _SKILL_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES
