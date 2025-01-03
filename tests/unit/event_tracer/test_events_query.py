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
    def evaluate_on_separate_thread(query: EventQuery, storage: EventStorage) -> None:
        """Evaluate the query on a separate thread.

        :param query: The query to evaluate
        :param storage: The storage to evaluate the query against
        """

        def evaluate_query() -> None:
            """Evaluate the query."""
            query.evaluate(storage)

        threading.Thread(target=evaluate_query).start()

    # ----------------------------------------------------------------
    # Pre-start query status tests

    @staticmethod
    def test_query_initial_status_is_not_yet_started() -> None:
        """Test that the query's initial status is empty."""
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )

        assert_that(query.status()).described_as(
            "Query status should tell the query has not started yet"
        ).is_equal_to(EventQueryStatus.NOT_STARTED)
        assert_that(query.succeeded()).described_as(
            "Query should not have succeeded by default"
        ).is_false()
        assert_that(query.is_completed()).described_as(
            "Query should not be completed by default"
        ).is_false()
        assert_that(query.evaluation_duration()).described_as(
            "Unstarted query should not have an evaluation duration by default"
        ).is_none()
        assert_that(query.remaining_timeout()).described_as(
            "Query remaining timeout should be the one set"
        ).is_equal_to(10)

    # ----------------------------------------------------------------
    # Ongoing query status tests

    def test_query_ongoing_status_is_in_progress(self) -> None:
        """The query's status is in progress while it is being evaluated."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )
        self.evaluate_on_separate_thread(query, storage)

        assert_that(query.status()).described_as(
            "Query status should tell the query is running"
        ).is_equal_to(EventQueryStatus.IN_PROGRESS)
        assert_that(query.succeeded()).described_as(
            "Query should not have succeeded yet"
        ).is_false()
        assert_that(query.is_completed()).described_as(
            "Query should not be completed yet"
        ).is_false()
        assert_that(query.evaluation_duration()).described_as(
            "Query should have an evaluation duration close to 0 " 
            "since it just started"
        ).is_close_to(0, 0.1)
        assert_that(query.remaining_timeout()).described_as(
            "Query remaining timeout should be close to the initial timeout "
            "since the query just started"
        ).is_close_to(10, 0.1)

    def test_query_ongoing_decreases_remaining_timeout(self) -> None:
        """The remaining timeout decreases while the query is being evaluated."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )
        self.evaluate_on_separate_thread(query, storage)
        time.sleep(1)

        assert_that(query.remaining_timeout()).described_as(
            "Query remaining timeout should decrease as time goes by"
        ).is_close_to(9, 0.1)
        assert_that(query.evaluation_duration()).described_as(
            "Query should have an increasing duration"
        ).is_close_to(1, 0.1)


    # ----------------------------------------------------------------
    # Post-query status tests


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

        query.evaluate(storage)

        assert_that(query.status()).described_as(
            "Query should succeed when an event matches"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(query.match_found).described_as(
            "Query should indicate a match was found"
        ).is_true()
        assert_that(query.succeeded()).described_as(
            "Query should have succeeded"
        ).is_true()
        assert_that(query.evaluation_duration()).described_as(
            "Query should have an evaluation duration close to 0"
            "since no timeout was set"
        ).is_close_to(0, 0.1)

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

        query.evaluate(storage)

        assert_that(query.status()).described_as(
            "Query should fail when no event matches"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(query.match_found).described_as(
            "Query should indicate no match was found"
        ).is_false()
        assert_that(query.succeeded()).described_as(
            "Query should not have succeeded"
        ).is_false()
        assert_that(query.evaluation_duration()).described_as(
            "Query should have an evaluation duration close to 0"
            "since no timeout was set"
        ).is_close_to(0, 0.1)

    def test_query_succeeds_with_delayed_event(self) -> None:
        """The query should succeed when an event is delayed but matches."""
        storage = EventStorage()
        query = SimpleEventQuery(
            timeout=3,
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        self.delayed_store_event(storage, create_test_event(), delay=1)
        query.evaluate(storage)

        assert_that(query.status()).described_as(
            "Query should succeed when an event is received during evaluation"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(query.succeeded()).described_as(
            "Query should have succeeded"
        ).is_true()
        assert_that(query.match_found).described_as(
            "Query should indicate a match was found"
        ).is_true()
        assert_that(query.evaluation_duration()).described_as(
            "Query should have an evaluation duration close to 1 "
            "since the event was delayed by 1 second"
        ).is_close_to(1, 0.1)
        assert_that(query.remaining_timeout()).described_as(
            "Query remaining timeout should be close to 2 "
            "since the event was delayed by 1 second and the timeout is 3"
        ).is_close_to(2, 0.1)

    def test_query_timeout(self) -> None:
        """The query times out when no event matches within timeout."""
        storage = EventStorage()
        query = SimpleEventQuery(
            timeout=1,
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        self.delayed_store_event(storage, create_test_event(), delay=1.5)

        query.evaluate(storage)
        time.sleep(0.5)

        assert_that(query.status()).described_as(
            "Query should fail when it times out"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(query.succeeded()).described_as(
            "Query should not have succeeded"
        ).is_false()
        assert_that(query.match_found).described_as(
            "No event should have matched, since they "
            "all arrived after the timeout"
        ).is_false()
        assert_that(query.evaluation_duration()).described_as(
            "Query should have an evaluation duration close to the timeout"
        ).is_close_to(1, 0.1)
        assert_that(query.remaining_timeout()).described_as(
            "Query remaining timeout should be 0"
        ).is_equal_to(0)
