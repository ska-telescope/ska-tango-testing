"""Dummy state enum class for testing typed events."""

from enum import Enum


class DummyStateEnum(Enum):
    """Dummy state enum class for testing."""

    STATE_0 = 0
    STATE_1 = 1
    STATE_2 = 2
    STATE_3 = 3


class DummyNonEnumClass:  # pylint: disable=too-few-public-methods
    """Dummy non-enum class for testing."""
