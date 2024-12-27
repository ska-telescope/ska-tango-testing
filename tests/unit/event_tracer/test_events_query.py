"""Unit tests for :py:class:`EventQuery`.

This set of tests covers the basic functionality of the
:py:class:`EventQuery` class, focusing on thread safety
and correct event handling.
"""

import threading
import time
from typing import Any, List, SupportsFloat

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.event_query import (
    EventQuery,
    EventQueryStatus,
)
from ska_tango_testing.integration.event_storage import EventStorage

from .testing_utils.received_event_mock import create_test_event


class SimpleEventQuery(EventQuery):
    """A simple query that checks if any event matches a given criteria."""

    def __init__(
        self,
        device_name: str,
        attr_name: str,
        value: Any,
        timeout: SupportsFloat = 0,
    ):
        """Initialize the query with the criteria.

        :param timeout: The timeout for the query in seconds.
        :param device_name: The device name to match.
        :param attr_name: The attribute name to match.
        :param value: The attribute value to match.
        """
        super().__init__(timeout)
        self.device_name = device_name
        self.attr_name = attr_name
        self.value = value
        self.match_found = False

    def _succeeded(self) -> bool:
        """Check if the query succeeded.

        :return: True if the query succeeded, False otherwise.
        """
        return self.match_found

    def _evaluate_events(self, events: List[ReceivedEvent]) -> None:
        """Evaluate the query based on the current events.

        :param events: The updated list of events.
        """
        for event in events:
            if (
                event.has_device(self.device_name)
                and event.has_attribute(self.attr_name)
                and event.attribute_value == self.value
            ):
                self.match_found = True
                break


@pytest.mark.integration_tracer
class TestEventQuery:
    """Unit tests for the EventQuery class."""

    @staticmethod
    def delayed_store_event(
        storage: EventStorage, event: ReceivedEvent, delay: float
    ) -> None:
        """Add an event to the storage after a delay.

        :param storage: The storage to add the event to
        :param event: The event to add
        :param delay: The delay in seconds
        """

        def add_event_after_delay() -> None:
            """Add the event to the storage after the delay."""
            time.sleep(delay)
            storage.store(event)

        threading.Thread(target=add_event_after_delay).start()

    @staticmethod
    def test_query_succeeds_when_event_matches() -> None:
        """Test that the query succeeds when an event matches."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        event = create_test_event()
        storage.store(event)

        storage.subscribe(query)
        query.evaluate()

        assert_that(query.status()).described_as(
            "Query should succeed when an event matches"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(query.match_found).described_as(
            "Query should indicate a match was found"
        ).is_true()

    @staticmethod
    def test_query_fails_when_no_event_matches() -> None:
        """Test that the query fails when no event matches."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        event = create_test_event(device_name="test/device/2")
        storage.store(event)

        storage.subscribe(query)
        query.evaluate()

        assert_that(query.status()).described_as(
            "Query should fail when no event matches"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(query.match_found).described_as(
            "Query should indicate no match was found"
        ).is_false()

    def test_query_succeeds_with_delayed_event(self) -> None:
        """The query should succeed when an event is delayed but matches."""
        storage = EventStorage()
        query = SimpleEventQuery(
            timeout=2,
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        self.delayed_store_event(storage, create_test_event(), delay=1)

        storage.subscribe(query)
        query.evaluate()

        assert_that(query.status()).described_as(
            "Query should succeed when an event is received during evaluation"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(query.match_found).described_as(
            "Query should indicate a match was found"
        ).is_true()

    def test_query_timeout(self) -> None:
        """The query times out when no event matches within timeout."""
        storage = EventStorage()
        query = SimpleEventQuery(
            timeout=1,
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        self.delayed_store_event(storage, create_test_event(), delay=2)

        storage.subscribe(query)
        query.evaluate()

        time.sleep(1.5)

        assert_that(query.status()).described_as(
            "Query should fail when it times out"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(query.match_found).described_as(
            "Query should indicate no match was found"
        ).is_false()
