"""Unit tests for :py:class:`EventsStorage`.

This set of tests covers the basic functionality of the
:py:class:`EventsStorage` class, focusing on thread safety
and correct event handling.
"""

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.events_storage import (
    EventsStorage,
    EventsStorageObserver,
)

from .testing_utils.received_event_mock import create_test_event


# pylint: disable=too-few-public-methods
class MockEventsStorageObserver(EventsStorageObserver):
    """A mock observer for testing EventsStorage."""

    def __init__(self) -> None:
        """Initialize the mock observer with an empty events list."""
        super().__init__()
        self.events: list[ReceivedEvent] = []

    def on_events_change(self, events: list[ReceivedEvent]) -> None:
        """Store the received events for later inspection.

        :param events: The updated list of events
        """
        self.events = events


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

    @staticmethod
    def test_observer_is_notified_when_event_stored() -> None:
        """Test that observers are notified when an event is stored."""
        storage = EventsStorage()
        observer = MockEventsStorageObserver()
        storage.subscribe(observer)

        event = create_test_event()
        storage.store(event)

        assert_that(observer.events).described_as(
            "Observer should receive current events"
        ).is_length(1)
        assert_that(observer.events[0]).described_as(
            "Observer should receive the stored event"
        ).is_equal_to(event)

    @staticmethod
    def test_unsubscribed_observer_not_notified() -> None:
        """Test that unsubscribed observers are not notified."""
        storage = EventsStorage()
        observer = MockEventsStorageObserver()

        storage.subscribe(observer)
        storage.unsubscribe(observer)

        event = create_test_event()
        storage.store(event)

        assert_that(observer.events).described_as(
            "Unsubscribed observer should not receive any events"
        ).is_empty()

    @staticmethod
    def test_multiple_observers_notified() -> None:
        """Test that multiple observers are notified."""
        storage = EventsStorage()
        observer1 = MockEventsStorageObserver()
        observer2 = MockEventsStorageObserver()

        storage.subscribe(observer1)
        storage.subscribe(observer2)

        event = create_test_event()
        storage.store(event)

        assert_that(observer1.events).described_as(
            "First observer should receive the stored event"
        ).is_length(1)
        assert_that(observer2.events).described_as(
            "Second observer should receive the stored event"
        ).is_length(1)

        assert_that(observer1.events).described_as(
            "Both observers should receive the same events"
        ).is_equal_to(observer2.events)

    @staticmethod
    def test_observer_notified_on_clear() -> None:
        """Test that observers are notified when events are cleared."""
        storage = EventsStorage()
        observer = MockEventsStorageObserver()

        storage.subscribe(observer)
        storage.clear_events()

        assert_that(observer.events).described_as(
            "Observer should receive an empty events list"
        ).is_empty()
