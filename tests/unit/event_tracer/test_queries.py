"""Unit tests for :py:class:`NEventsMatchQuery`.

This set of tests covers the basic functionality of the
:py:class:`NEventsMatchQuery` class, focusing on matching events
through a predicate and succeeding when a target number of events is reached.
"""

import time

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event_query import EventQueryStatus
from ska_tango_testing.integration.event_storage import EventStorage
from ska_tango_testing.integration.queries import NEventsMatchQuery

from .test_events_query import TestEventQuery
from .testing_utils.received_event_mock import create_test_event


@pytest.mark.integration_tracer
class TestNEventsMatchQuery:
    """Unit tests for the NEventsMatchQuery class."""

    @staticmethod
    def test_query_succeeds_when_event_matches() -> None:
        """Test that the query succeeds when an event matches."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
        )

        event = create_test_event()
        storage.store(event)

        storage.subscribe(query)
        query.evaluate()

        assert_that(query.succeeded()).described_as(
            "Query should succeed when an event matches"
        ).is_true()
        assert_that(query.status()).described_as(
            "Query status should be SUCCEEDED when an event matches"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(query.matching_events).described_as(
            "Query should collect the matching event"
        ).is_length(1)
        assert_that(query.matching_events[0]).described_as(
            "Query should collect the correct event"
        ).is_equal_to(event)

    @staticmethod
    def test_query_fails_when_no_event_matches() -> None:
        """Test that the query fails when no event matches."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
        )
        event = create_test_event(device_name="test/device/2")
        storage.store(event)

        storage.subscribe(query)
        query.evaluate()

        assert_that(query.succeeded()).described_as(
            "Query should fail when no event matches"
        ).is_false()
        assert_that(query.status()).described_as(
            "Query status should be FAILED when no event matches"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(query.matching_events).described_as(
            "Query should not collect any events"
        ).is_empty()

    @staticmethod
    def test_query_succeeds_with_multiple_matching_events() -> None:
        """Test that the query succeeds with multiple matching events."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            target_n_events=2,
            timeout=2,
        )
        event1 = create_test_event()
        event2 = create_test_event()
        storage.store(event1)
        TestEventQuery.delayed_store_event(storage, event2, delay=1)

        storage.subscribe(query)
        query.evaluate()

        assert_that(query.succeeded()).described_as(
            "Query should succeed when multiple events match"
        ).is_true()
        assert_that(query.status()).described_as(
            "Query status should be SUCCEEDED when multiple events match"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(query.matching_events).described_as(
            "Query should collect all matching events"
        ).is_length(2)
        assert_that(query.matching_events).described_as(
            "Query should collect the correct events"
        ).contains(event1, event2)

    @staticmethod
    def test_query_timeout() -> None:
        """Test that the query times out when not all events matches."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            target_n_events=2,
            timeout=1,
        )
        event1 = create_test_event()
        event2 = create_test_event()
        event3 = create_test_event(device_name="test/device/2")
        storage.store(event1)
        TestEventQuery.delayed_store_event(storage, event3, delay=0.5)
        TestEventQuery.delayed_store_event(storage, event2, delay=1.5)

        storage.subscribe(query)
        query.evaluate()

        time.sleep(1.5)
        assert_that(query.succeeded()).described_as(
            "Query should time out when no events match within timeout"
        ).is_false()
        assert_that(query.status()).described_as(
            "Query status should be FAILED when no events match within timeout"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(query.matching_events).described_as(
            "Query should not have collected all expected events"
        ).is_length(1)
