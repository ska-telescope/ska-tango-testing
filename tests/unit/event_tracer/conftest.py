"""Fixtures for the `TangoEventTracer` unit tests."""

import pytest

from ska_tango_testing.integration.tracer import TangoEventTracer


@pytest.fixture
def tracer() -> TangoEventTracer:
    """Create a `TangoEventTracer` instance for testing.

    :return: a `TangoEventTracer` instance.
    """
    return TangoEventTracer()
