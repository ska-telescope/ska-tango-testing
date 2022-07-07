"""This module supports testing with mock Tango change event callbacks."""
import threading
import unittest.mock
from typing import Any, Callable, Optional

import pytest
import tango

from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup


@pytest.fixture()
def callback_group() -> MockTangoEventCallbackGroup:
    """
    Return the Tango event callback group under test.

    :return: the Tango event callback group under test.
    """
    return MockTangoEventCallbackGroup(
        "status", "progress", "a", "b", timeout=1.0
    )


@pytest.fixture(scope="session")
def schedule_event() -> Callable:
    """
    Return a callable used to schedule a call to a callback at a future time.

    :return: a callable.
    """

    def _schedule_event(
        delay: float,
        callback_to_call: Callable,
        name: str,
        value: Any,
        quality: Optional[tango.AttrQuality] = tango.AttrQuality.ATTR_VALID,
    ) -> Any:
        fake_event = unittest.mock.Mock()
        fake_event.err = False
        fake_event.attr_value.name = name
        fake_event.attr_value.value = value
        fake_event.attr_value.quality = quality

        threading.Timer(delay, callback_to_call, args=(fake_event,)).start()

    return _schedule_event
