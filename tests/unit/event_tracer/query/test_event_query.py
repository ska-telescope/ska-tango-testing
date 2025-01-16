"""Unit tests for :py:class:`EventQuery`.

This set of tests covers the basic functionality of the
:py:class:`EventQuery` class, focusing on thread safety
and correct event handling.
"""

import threading
import time
from datetime import datetime
from typing import Any, List, SupportsFloat

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.assertions.timeout import (
    ChainedAssertionsTimeout,
)
from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.event.storage import EventStorage
from ska_tango_testing.integration.query.base import (
    EventQuery,
    EventQueryStatus,
)
from tests.unit.event_tracer.assertions.utils import assert_elapsed_time

from ..testing_utils.delayed_store_event import delayed_store_event
from ..testing_utils.received_event_mock import create_test_event
from .utils import (
    assert_query_succeeded,
    assert_timeout_and_duration_consistency,
)


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

    def _describe_results(self) -> str:
        """Describe the query results.

        :return: The description of the query results.
        """
        return "Match found: " + str(self.match_found)

    def _describe_criteria(self) -> str:
        """Describe the query criteria.

        :return: The description of the query criteria.
        """
        return (
            f"Device: {self.device_name}, "
            f"Attribute: {self.attr_name}, "
            f"Value: {self.value}"
        )


@pytest.mark.integration_tracer
class TestEventQuery:
    """Unit tests for the EventQuery class."""

    @staticmethod
    def evaluate_on_separate_thread(
        query: EventQuery, storage: EventStorage
    ) -> None:
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
        assert_timeout_and_duration_consistency(query, 10, None)

    @staticmethod
    def test_query_timeout_is_0_when_no_timeout_is_given() -> None:
        """Test that the query can handle no timeout value."""
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )

        assert_that(query.initial_timeout()).described_as(
            "Query should handle no timeout value"
        ).is_equal_to(0)

    @staticmethod
    def test_query_negative_timeout_values_are_0() -> None:
        """Test that the query can handle weird timeout values."""
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=-1,
        )

        assert_that(query.initial_timeout()).described_as(
            "Query should handle negative timeout values"
        ).is_equal_to(0)

    @staticmethod
    def test_query_infinite_timeout_values_are_0() -> None:
        """Test that the query can handle infinite timeout values."""
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=float("inf"),
        )

        assert_that(query.initial_timeout()).described_as(
            "Query should handle infinite timeout values"
        ).is_equal_to(0)

    @staticmethod
    def test_query_before_start_timeout_can_be_changed() -> None:
        """Test that the query can change the timeout before starting."""
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )
        query.set_timeout(5)

        assert_that(query.initial_timeout()).described_as(
            "Query should handle changing the timeout before starting"
        ).is_equal_to(5)

    # ----------------------------------------------------------------
    # Ongoing query status tests

    @staticmethod
    def test_query_after_start_timeout_cannot_be_changed() -> None:
        """Test that the query cannot change the timeout after starting."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )
        query.evaluate(storage)

        with pytest.raises(RuntimeError) as exc_info:
            query.set_timeout(5)

        assert_that(query.initial_timeout()).described_as(
            "Query should not allow changing the timeout after starting"
        ).is_equal_to(10)
        assert_that(str(exc_info.value)).described_as(
            "Query should raise an exception when trying to change the timeout"
        ).contains("Cannot change the timeout after the evaluation started")

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
        assert_timeout_and_duration_consistency(query, 10, 0)

    def test_query_ongoing_decreases_remaining_timeout(self) -> None:
        """The remaining timeout decreases while the query is evaluated."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )
        self.evaluate_on_separate_thread(query, storage)
        time.sleep(1)

        assert_timeout_and_duration_consistency(query, 10, 1)

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
        create_test_event(store=storage)

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
        assert_timeout_and_duration_consistency(query, 0, 0)

    @staticmethod
    def test_query_fails_when_no_event_matches() -> None:
        """Test that the query fails when no event matches."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        create_test_event(device_name="test/device/2", store=storage)

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
        assert_timeout_and_duration_consistency(query, 0, 0)

    @staticmethod
    def test_query_succeeds_with_delayed_event() -> None:
        """The query should succeed when an event is delayed but matches."""
        storage = EventStorage()
        query = SimpleEventQuery(
            timeout=5,
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        delayed_store_event(storage, create_test_event(), delay=1)
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
        assert_timeout_and_duration_consistency(query, 5, 1)

    @staticmethod
    def test_query_timeout() -> None:
        """The query times out when no event matches within timeout."""
        storage = EventStorage()
        query = SimpleEventQuery(
            timeout=1,
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        delayed_store_event(storage, create_test_event(), delay=1.2)

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
        assert_timeout_and_duration_consistency(query, 1, 1)

    # ----------------------------------------------------------------
    # Tests for the describe method

    @staticmethod
    def test_query_describe_initial_status() -> None:
        """Test the describe method for the initial status."""
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )

        description = query.describe()
        assert_that(description).described_as(
            "Description should contain the initial status"
        ).contains("Status=NOT_STARTED")
        assert_that(description).described_as(
            "Description should contain the initial timeout"
        ).contains("Initial timeout=")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Device: test/device/1")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Attribute: test_attr")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Value: 42")
        assert_that(description).described_as(
            "Description should contain the results"
        ).contains("Match found: False")

    def test_query_describe_ongoing_status(self) -> None:
        """Test the describe method for the ongoing status."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=10,
        )
        self.evaluate_on_separate_thread(query, storage)
        time.sleep(1)

        description = query.describe()
        assert_that(description).described_as(
            "Description should contain the ongoing status"
        ).contains("Status=IN_PROGRESS")
        assert_that(description).described_as(
            "Description should contain the remaining timeout"
        ).contains("Remaining timeout=")
        assert_that(description).described_as(
            "Description should contain the evaluation duration"
        ).contains("Evaluation duration=")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Device: test/device/1")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Attribute: test_attr")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Value: 42")
        assert_that(description).described_as(
            "Description should contain the results"
        ).contains("Match found: False")

    @staticmethod
    def test_query_describe_succeeded_status() -> None:
        """Test the describe method for the succeeded status."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        create_test_event(store=storage)

        query.evaluate(storage)

        description = query.describe()
        assert_that(description).described_as(
            "Description should contain the succeeded status"
        ).contains("Status=SUCCEEDED")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Device: test/device/1")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Attribute: test_attr")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Value: 42")
        assert_that(description).described_as(
            "Description should contain the results"
        ).contains("Match found: True")

    @staticmethod
    def test_query_describe_failed_status() -> None:
        """Test the describe method for the failed status."""
        storage = EventStorage()
        query = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
        )
        create_test_event(device_name="test/device/2", store=storage)

        query.evaluate(storage)

        description = query.describe()
        assert_that(description).described_as(
            "Description should contain the failed status"
        ).contains("Status=FAILED")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Device: test/device/1")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Attribute: test_attr")
        assert_that(description).described_as(
            "Description should contain the criteria"
        ).contains("Value: 42")
        assert_that(description).described_as(
            "Description should contain the results"
        ).contains("Match found: False")

    # ----------------------------------------------------------------
    # Test for shared timeout concept

    @staticmethod
    def test_multiple_queries_can_share_a_timeout_object() -> None:
        """A timeout object can be shared among different queries."""
        storage = EventStorage()
        timeout = ChainedAssertionsTimeout(5)

        delayed_store_event(storage, create_test_event(), delay=1)
        delayed_store_event(
            storage, create_test_event(device_name="test/device/2"), delay=1
        )
        delayed_store_event(
            storage, create_test_event(device_name="test/device/3"), delay=3
        )

        start_time = datetime.now()
        query1 = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=timeout,
        )
        query1.evaluate(storage)
        query2 = SimpleEventQuery(
            device_name="test/device/2",
            attr_name="test_attr",
            value=42,
            timeout=timeout,
        )
        query2.evaluate(storage)
        query3 = SimpleEventQuery(
            device_name="test/device/3",
            attr_name="test_attr",
            value=42,
            timeout=timeout,
        )
        query3.evaluate(storage)

        assert_query_succeeded(query1)
        assert_query_succeeded(query2)
        assert_query_succeeded(query3)
        assert_timeout_and_duration_consistency(query1, 5, 1)
        assert_timeout_and_duration_consistency(query2, 4, 0)
        assert_timeout_and_duration_consistency(query3, 4, 2)
        assert_elapsed_time(start_time, 3)

    @staticmethod
    def test_multiple_queries_handle_weird_event_order() -> None:
        """A timeout object can be shared among different queries."""
        storage = EventStorage()
        timeout = ChainedAssertionsTimeout(5)

        delayed_store_event(storage, create_test_event(), delay=1)
        delayed_store_event(
            storage, create_test_event(device_name="test/device/3"), delay=2
        )
        delayed_store_event(
            storage, create_test_event(device_name="test/device/2"), delay=3
        )

        start_time = datetime.now()
        query1 = SimpleEventQuery(
            device_name="test/device/1",
            attr_name="test_attr",
            value=42,
            timeout=timeout,
        )
        query1.evaluate(storage)
        query2 = SimpleEventQuery(
            device_name="test/device/2",
            attr_name="test_attr",
            value=42,
            timeout=timeout,
        )
        query2.evaluate(storage)
        query3 = SimpleEventQuery(
            device_name="test/device/3",
            attr_name="test_attr",
            value=42,
            timeout=timeout,
        )
        query3.evaluate(storage)

        assert_query_succeeded(query1)
        assert_query_succeeded(query2)
        assert_query_succeeded(query3)
        assert_timeout_and_duration_consistency(query1, 5, 1)
        assert_timeout_and_duration_consistency(query2, 4, 2)
        assert_timeout_and_duration_consistency(query3, 2, 0)
        assert_elapsed_time(start_time, 3)
