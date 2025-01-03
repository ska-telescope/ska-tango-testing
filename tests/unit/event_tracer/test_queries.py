"""Unit tests for EventQuery concrete implementations.

Currently, the tested classes are:
:py:class:`NEventsMatchQuery`, :py:class:`QueryWithFailCondition`,
and :py:class:`NStateChangesQuery`.

This set of tests covers the basic functionality of the
:py:class:`NEventsMatchQuery`, :py:class:`QueryWithFailCondition`,
and :py:class:`NStateChangesQuery` classes, focusing on matching events
through a predicate and succeeding when a target number of events is reached,
and stopping early if a stop condition is met.
"""

import time
from unittest.mock import MagicMock

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event_query import EventQueryStatus
from ska_tango_testing.integration.event_storage import EventStorage
from ska_tango_testing.integration.queries import (
    NEventsMatchQuery,
    NStateChangesQuery,
    QueryWithFailCondition,
)

from .testing_utils.delayed_store_event import delayed_store_event
from .testing_utils.received_event_mock import create_test_event


@pytest.mark.integration_tracer
class TestNEventsMatchQuery:
    """Unit tests for the NEventsMatchQuery class."""

    @staticmethod
    def test_query_calls_predicate_and_pass_events() -> None:
        """The query calls the predicate with the correct arguments."""
        storage = EventStorage()
        mock_predicate = MagicMock()
        query = NEventsMatchQuery(
            predicate=mock_predicate,
        )
        event = create_test_event()
        storage.store(event)

        query.evaluate(storage)

        assert_that(mock_predicate.call_count).described_as(
            "Predicate should be called once per event"
        ).is_equal_to(1)
        assert_that(mock_predicate.call_args[0][0]).described_as(
            "Predicate should receive the event as first argument"
        ).is_equal_to(event)
        assert_that(mock_predicate.call_args[0][1]).described_as(
            "Predicate should receive the list of all "
            " events as second argument"
        ).is_equal_to([event])

    @staticmethod
    def test_query_succeeds_when_event_matches() -> None:
        """Test that the query succeeds when an event matches."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
        )

        event = create_test_event()
        storage.store(event)

        query.evaluate(storage)

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
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
        )
        event = create_test_event(device_name="test/device/2")
        storage.store(event)

        query.evaluate(storage)

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
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            target_n_events=2,
            timeout=2,
        )
        event1 = create_test_event()
        event2 = create_test_event()
        storage.store(event1)
        delayed_store_event(storage, event2, delay=1)

        query.evaluate(storage)

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
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            target_n_events=2,
            timeout=1,
        )
        event1 = create_test_event()
        event2 = create_test_event()
        event3 = create_test_event(device_name="test/device/2")
        storage.store(event1)
        delayed_store_event(storage, event3, delay=0.5)
        delayed_store_event(storage, event2, delay=1.5)

        query.evaluate(storage)

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


@pytest.mark.integration_tracer
class TestQueryWithFailCondition:
    """Unit tests for the QueryWithFailCondition class."""

    @staticmethod
    def test_query_succeeds_when_event_matches() -> None:
        """Test that the query succeeds when an event matches."""
        storage = EventStorage()
        wrapped_query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
        )
        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: False,
        )
        # this event will match the query
        event = create_test_event()
        storage.store(event)

        query.evaluate(storage)

        assert_that(query.succeeded()).described_as(
            "Query should succeed when an event matches"
        ).is_true()
        assert_that(query.status()).described_as(
            "Query status should be SUCCEEDED when an event matches"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(wrapped_query.succeeded()).described_as(
            "Wrapped query should succeed too"
        ).is_true()
        assert_that(wrapped_query.matching_events).described_as(
            "Wrapped query should collect the matching event"
        ).is_length(1)
        assert_that(wrapped_query.matching_events[0]).described_as(
            "Wrapped query should collect the correct event"
        ).is_equal_to(event)

    @staticmethod
    def test_query_stop_condition_makes_the_test_fail() -> None:
        """Test that the query fails when the stop condition is met."""
        storage = EventStorage()
        wrapped_query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
        )
        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: e.has_device("test/device/2"),
        )
        # this event could match the query but it will not be evaluated
        event = create_test_event()
        storage.store(event)
        # this event will trigger the stop condition
        fail_event = create_test_event(device_name="test/device/2")
        storage.store(fail_event)

        query.evaluate(storage)

        assert_that(query.succeeded()).described_as(
            "Query should fail when the stop condition is met"
        ).is_false()
        assert_that(query.status()).described_as(
            "Query status should be FAILED when the stop condition is met"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(wrapped_query.matching_events).described_as(
            "Wrapped query should not collect any events"
        ).is_empty()
        assert_that(query.failed_event).described_as(
            "Query should store the event that caused the failure"
        ).is_equal_to(fail_event)

    @staticmethod
    def test_query_succeeds_with_delayed_event() -> None:
        """The query should succeed when an event is delayed but matches."""
        storage = EventStorage()
        wrapped_query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            timeout=0,  # this timeout will be ignored
        )
        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: False,
            timeout=2,  # this timeout will be used
        )
        # this event will make the query succeed
        event = create_test_event()
        delayed_store_event(storage, event, delay=1)
        # this event could potentially make the query fail, but it will
        # arrive too late and the query will have already succeeded
        fail_event = create_test_event(device_name="test/device/2")
        delayed_store_event(storage, fail_event, delay=1.5)

        query.evaluate(storage)
        time.sleep(1)

        assert_that(wrapped_query.succeeded()).described_as(
            "Wrapped query should succeed"
        ).is_true()
        assert_that(query.succeeded()).described_as(
            "Query should succeed when an event is received during evaluation"
        ).is_true()
        assert_that(query.status()).described_as(
            "Query status should be SUCCEEDED when an event "
            "is received during evaluation"
        ).is_equal_to(EventQueryStatus.SUCCEEDED)
        assert_that(wrapped_query.matching_events).described_as(
            "Wrapped query should collect the matching event"
        ).is_length(1)
        assert_that(wrapped_query.matching_events[0]).described_as(
            "Wrapped query should collect the correct event"
        ).is_equal_to(event)

    @staticmethod
    def test_query_fails_with_delayed_stop_event() -> None:
        """The query should fail when the stop condition is met (delayed)."""
        storage = EventStorage()
        wrapped_query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            timeout=2,  # this timeout will be ignored
        )
        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: e.has_device("test/device/2"),
            timeout=1,  # this timeout will be used
        )
        # this event will trigger the stop condition
        fail_event = create_test_event(device_name="test/device/2")
        delayed_store_event(storage, fail_event, delay=1)
        # this event could match the query but it will not be evaluated
        # because the stop condition will be met first
        event = create_test_event()
        delayed_store_event(storage, event, delay=1.5)

        query.evaluate(storage)

        assert_that(query.succeeded()).described_as(
            "Query should fail when the stop condition "
            "is met with a delayed event"
        ).is_false()
        assert_that(query.status()).described_as(
            "Query status should be FAILED when the stop condition "
            "is met with a delayed event"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(wrapped_query.matching_events).described_as(
            "Wrapped query should not collect any events"
        ).is_empty()
        assert_that(query.failed_event).described_as(
            "Query should store the event that caused the failure"
        ).is_equal_to(fail_event)

    @staticmethod
    def test_query_timeout() -> None:
        """The query times out when no event matches within timeout."""
        storage = EventStorage()
        wrapped_query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            timeout=1,
        )
        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: False,
        )

        query.evaluate(storage)

        assert_that(query.succeeded()).described_as(
            "Query should fail when it times out"
        ).is_false()
        assert_that(query.status()).described_as(
            "Query status should be FAILED when it times out"
        ).is_equal_to(EventQueryStatus.FAILED)
        assert_that(wrapped_query.matching_events).described_as(
            "Wrapped query should not collect any events"
        ).is_empty()
        assert_that(query.failed_event).described_as(
            "Query should not store any event that caused the failure"
        ).is_none()


@pytest.mark.integration_tracer
class TestNStateChangesQuery:
    """Unit tests for the NStateChangesQuery class."""

    @staticmethod
    def test_query_succeeds_when_event_matches() -> None:
        """Test that the query succeeds when an event matches."""
        storage = EventStorage()
        query = NStateChangesQuery(
            device_name="test/device/1",
            attribute_name="test_attr",
            attribute_value=42,
            previous_value=41,
        )

        event1 = create_test_event(value=41)
        event2 = create_test_event(value=42)
        non_matching_event = create_test_event(device_name="test/device/2")
        other_non_matchig_event = create_test_event(attr_name="other_attr")
        storage.store(event1)
        storage.store(event2)
        storage.store(non_matching_event)
        storage.store(other_non_matchig_event)

        query.evaluate(storage)

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
        ).is_equal_to(event2)

    @staticmethod
    def test_query_fails_when_no_event_matches_when_prev_value_miss() -> None:
        """Test that the query fails when no event matches."""
        storage = EventStorage()
        query = NStateChangesQuery(
            attribute_value=42,
            previous_value=41,
        )

        event = create_test_event(value=42)
        storage.store(event)

        query.evaluate(storage)

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
    def test_query_fails_when_no_event_matches_for_diff_prev_value() -> None:
        """Test that the query fails when no event matches."""
        storage = EventStorage()
        query = NStateChangesQuery(
            device_name="test/device/1",
            attribute_name="test_attr",
            attribute_value=42,
            previous_value=41,
        )
        event0 = create_test_event(value=41)
        event1 = create_test_event(value=40)
        event_diff_device = create_test_event(
            device_name="test/device/2", value=41
        )
        event2 = create_test_event(value=42)

        storage.store(event0)
        storage.store(event1)
        storage.store(event_diff_device)
        storage.store(event2)

        query.evaluate(storage)

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
    def test_query_applies_custom_matcher() -> None:
        """Test that the query applies a custom matcher."""
        storage = EventStorage()
        query = NStateChangesQuery(
            device_name="test/device/1",
            attribute_name="test_attr",
            custom_matcher=lambda e: str(e.attribute_value).endswith("2"),
        )

        event1 = create_test_event(value=41)
        event2 = create_test_event(value=42)
        event3 = create_test_event(device_name="test/device/2", value=42)
        storage.store(event1)
        storage.store(event2)
        storage.store(event3)

        query.evaluate(storage)

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
        ).is_equal_to(event2)
