"""Unit tests for the QueryWithFailCondition class."""

import time
from unittest.mock import MagicMock

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event.storage import EventStorage
from ska_tango_testing.integration.query.n_events_match import (
    NEventsMatchQuery,
)
from ska_tango_testing.integration.query.with_fail_condition import (
    QueryWithFailCondition,
)
from tests.unit.event_tracer.query.utils import (
    assert_n_events_are_collected,
    assert_query_failed,
    assert_query_succeeded,
)

from ..testing_utils.delayed_store_event import delayed_store_event
from ..testing_utils.received_event_mock import create_test_event


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
        event = create_test_event(store=storage)

        query.evaluate(storage)

        assert_query_succeeded(query)
        assert_that(wrapped_query.succeeded()).described_as(
            "Wrapped query should succeed too"
        ).is_true()
        assert_n_events_are_collected(wrapped_query, [event])

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
        create_test_event(store=storage)
        # this event will trigger the stop condition
        fail_event = create_test_event(
            device_name="test/device/2", store=storage
        )

        query.evaluate(storage)

        assert_query_failed(query)
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
            timeout=2,  # this timeout will be used
        )
        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: False,
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

        assert_query_succeeded(query)
        assert_that(wrapped_query.succeeded()).described_as(
            "Wrapped query should succeed"
        ).is_true()
        assert_n_events_are_collected(wrapped_query, [event])

    @staticmethod
    def test_query_fails_with_delayed_stop_event() -> None:
        """The query should fail when the stop condition is met (delayed)."""
        storage = EventStorage()
        wrapped_query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            timeout=3,  # this timeout will be used
        )
        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: e.has_device("test/device/2"),
        )
        # this event will trigger the stop condition
        fail_event = create_test_event(device_name="test/device/2")
        delayed_store_event(storage, fail_event, delay=1)
        # this event could match the query but it will not be evaluated
        # because the stop condition will be met first
        event = create_test_event()
        delayed_store_event(storage, event, delay=1.5)

        query.evaluate(storage)

        assert_query_failed(query)
        assert_that(query.failed_event).described_as(
            "Query should store the event that caused the failure"
        ).is_equal_to(fail_event)
        assert_that(wrapped_query.matching_events).described_as(
            "Wrapped query should not collect any events"
        ).is_empty()
        assert_that(query.remaining_timeout()).described_as(
            "Query remaining timeout should be nearly 2 seconds "
            "since the stop condition was met 2 seconds "
            " before the expected end"
        ).is_close_to(2, 0.1)

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
        delayed_store_event(storage, create_test_event(), delay=1.2)

        query.evaluate(storage)
        time.sleep(0.5)

        assert_query_failed(query)
        assert_that(query.failed_event).described_as(
            "Query should not store any event that caused the failure"
        ).is_none()
        assert_that(wrapped_query.matching_events).described_as(
            "Wrapped query should not collect any events"
        ).is_empty()
        assert_that(query.remaining_timeout()).described_as(
            "Query remaining timeout should be 0 when it times out"
        ).is_equal_to(0)

    @staticmethod
    def test_query_describe_includes_wrapped_query_info() -> None:
        """The query description includes info from the wrapped query."""
        storage = EventStorage()
        wrapped_query = MagicMock()
        # pylint: disable=protected-access
        wrapped_query._describe_criteria = MagicMock(
            return_value="Wrapped query criteria"
        )
        # pylint: disable=protected-access
        wrapped_query._describe_results = MagicMock(
            return_value="Wrapped query results"
        )

        query = QueryWithFailCondition(
            wrapped_query=wrapped_query,
            stop_condition=lambda e: False,
        )
        create_test_event(store=storage)
        query.evaluate(storage)

        description = query.describe()

        assert_that(description).described_as(
            "Query description should include the wrapped query criteria"
        ).contains("Wrapped query criteria").described_as(
            "Query description should include the wrapped query results"
        ).contains(
            "Wrapped query results"
        ).described_as(
            "An additional message should tell that an early stop "
            "condition was applied to the criteria"
        ).contains(
            "An early stop condition is set"
        )

    @staticmethod
    def test_query_describe_includes_event_that_triggered_early_stop() -> None:
        """The query description includes the event that triggered the stop."""
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
        create_test_event(store=storage)
        fail_event = create_test_event(
            device_name="test/device/2", store=storage
        )
        query.evaluate(storage)

        description = query.describe()

        assert_that(description).described_as(
            "Query description must report that the query was stopped early"
        ).contains("triggered an early stop").described_as(
            "Query description should include the event "
            "that triggered the early stop"
        ).contains(
            str(fail_event)
        )
