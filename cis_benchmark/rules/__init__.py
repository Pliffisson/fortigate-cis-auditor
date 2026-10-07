"""Public access to the current PDF-based benchmark controls."""
from ..benchmark import FAMILY
from .registry import get_all_rules as _get_rules


def get_all_rules(family=FAMILY, options=None):
    if family != FAMILY:
        raise ValueError("Unsupported benchmark family")
    return _get_rules(options)


def get_level1_rules(family=FAMILY, options=None):
    return [r for r in get_all_rules(family, options) if r.level.value == 1]


def get_level2_rules(family=FAMILY, options=None):
    return [r for r in get_all_rules(family, options) if r.level.value == 2]

__all__ = [
    "get_all_rules",
    "get_level1_rules",
    "get_level2_rules",
]
