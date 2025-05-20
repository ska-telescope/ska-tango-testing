"""Utilities for populating a `TangoEventTracer` instance with test events."""

import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ska_tango_testing.integration.event import ReceivedEvent, TypedEvent
from ska_tango_testing.integration.tracer import TangoEventTracer

from .eventdata_mock import create_eventdata_mock


def add_event(
    tracer: TangoEventTracer,
    device: str,
    value: Any,
    seconds_ago: float = 0,
    attr_name: str = "test_attribute",
) -> ReceivedEvent:
    """Add an event to the tracer.

    :param tracer: The `TangoEventTracer` instance.
    :param device: The device name.
    :param value: The current value.
    :param seconds_ago: How many seconds ago the event occurred,
        default is 0.
    :param attr_name: The attribute name, default is "test_attribute".
    :return: The event that was added.
    """
    test_event = ReceivedEvent(create_eventdata_mock(device, attr_name, value))

    # Set the timestamp to the past (if needed)
    if seconds_ago > 0:
        test_event.reception_time = datetime.now() - timedelta(
            seconds=seconds_ago
        )

    tracer._add_event(test_event)  # pylint: disable=protected-access

    return test_event


def add_typed_event(
    tracer: TangoEventTracer,
    device: str,
    value: Any,
    attr_name: str = "test_attribute",
    event_type: type[Enum] | None = None,
) -> ReceivedEvent:
    """Add a typed event to the tracer.

    :param tracer: The `TangoEventTracer` instance.
    :param device: The device name.
    :param value: The current value.
    :param attr_name: The attribute name, default is "test_attribute".
    :param event_type: The type of the attribute, default is None.
        If None, the event is not typed.
    :return: The event that was added.
    """
    # eventually type the event
    event_data = create_eventdata_mock(device, attr_name, value)
    test_event = (
        ReceivedEvent(event_data)
        if event_type is None
        else TypedEvent(event_data, event_type)
    )

    tracer._add_event(test_event)  # pylint: disable=protected-access

    return test_event


def delayed_add_event(
    tracer: TangoEventTracer, device: str, value: Any, delay: float
) -> None:
    """Add an event to the tracer after a delay.

    :param tracer: The `TangoEventTracer` instance.
    :param device: The device name.
    :param value: The current value.
    :param delay: The delay in seconds.
    """

    def _add_event() -> None:
        """Add an event after a delay."""
        time.sleep(delay)
        add_event(tracer, device, value)

    threading.Thread(target=_add_event).start()
