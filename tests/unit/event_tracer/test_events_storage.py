"""Unit tests for :py:class:`EventsStorage`.

This set of tests covers the basic functionality of the
:py:class:`EventsStorage` class, focusing on thread safety
and correct event handling.
"""

from typing import Any

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.events_storage import EventsStorage

from .testing_utils import create_eventdata_mock


def create_test_event(
    device_name: str = "test/device/1",
    attr_name: str = "test_attr",
    value: Any = 42,
) -> ReceivedEvent:
    """Create a test event with given parameters.

    :param device_name: Name of the device
    :param attr_name: Name of the attribute
    :param value: Value for the event
    :return: A ReceivedEvent instance
    """
    event_data = create_eventdata_mock(device_name, attr_name, value)
    return ReceivedEvent(event_data)


@pytest.mark.integration_tracer
class TestEventsStorage:
    """Unit tests for the EventsStorage class."""

    @staticmethod
    def test_store_adds_event() -> None:
        """Test that storing an event adds it to storage."""
        storage = EventsStorage()
        event = create_test_event()
        storage.store(event)

        assert_that(storage.events).described_as(
            "Storage should contain exactly one event"
        ).is_length(1)

        assert_that(storage.events[0]).described_as(
            "Stored event should match the original"
        ).is_equal_to(event)

    @staticmethod
    def test_clear_events_removes_all() -> None:
        """Test that clearing events removes all stored events."""
        storage = EventsStorage()
        event = create_test_event()
        storage.store(event)
        storage.store(event)
        storage.clear_events()

        assert_that(storage.events).described_as(
            "Storage should be empty after clearing"
        ).is_empty()

    @staticmethod
    def test_events_returns_copy() -> None:
        """Test that events property returns a copy of the events list."""
        storage = EventsStorage()
        event = create_test_event()
        storage.store(event)
        events = storage.events
        events.clear()  # Modify the copy

        assert_that(storage.events).described_as(
            "Original storage should still contain the event"
        ).is_length(1)
