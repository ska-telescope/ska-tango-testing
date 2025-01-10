"""Unit tests for the NEventsMatchQuery class."""

import time
from unittest.mock import MagicMock

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event.storage import EventStorage
from ska_tango_testing.integration.query.n_events_match import (
    NEventsMatchQuery,
)

from ..testing_utils.delayed_store_event import delayed_store_event
from ..testing_utils.received_event_mock import create_test_event
from .utils import (
    assert_n_events_are_collected,
    assert_n_events_match_query_failed,
    assert_n_events_match_query_succeeded,
    assert_query_failed,
)


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
        event = create_test_event(store=storage)

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
        event = create_test_event(store=storage)

        query.evaluate(storage)

        assert_n_events_match_query_succeeded(query, [event])

    @staticmethod
    def test_query_fails_when_no_event_matches() -> None:
        """Test that the query fails when no event matches."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
        )
        create_test_event(device_name="test/device/2", store=storage)

        query.evaluate(storage)

        assert_n_events_match_query_failed(query)

    @staticmethod
    def test_query_succeeds_with_multiple_matching_events() -> None:
        """Test that the query succeeds with multiple matching events."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            target_n_events=2,
            timeout=3,
        )
        event1 = create_test_event(store=storage)
        event2 = create_test_event()
        delayed_store_event(storage, event2, delay=1)

        query.evaluate(storage)

        assert_n_events_match_query_succeeded(query, [event1, event2])

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
        # one matching event is already stored
        matching_event = create_test_event(store=storage)
        # one non-matching event is stored within the timeout
        non_matching_event = create_test_event(device_name="test/device/2")
        delayed_store_event(storage, non_matching_event, delay=0.5)
        # one matching event is stored after the timeout (too late)
        late_matching_event = create_test_event()
        delayed_store_event(storage, late_matching_event, delay=1.5)

        query.evaluate(storage)
        time.sleep(0.3)

        assert_query_failed(query)
        assert_n_events_are_collected(query, [matching_event])

    @staticmethod
    def test_query_describe_includes_n_matching_events() -> None:
        """The query description includes the number of matching events."""
        storage = EventStorage()
        query = NEventsMatchQuery(
            predicate=lambda e, _: e.has_device("test/device/1")
            and e.has_attribute("test_attr")
            and e.attribute_value == 42,
            target_n_events=2,
        )
        event1 = create_test_event(store=storage)
        query.evaluate(storage)

        description = query.describe()

        assert_that(description).described_as(
            "Query description should include the expected "
            " number of matching events"
        ).contains("Looking for 2 events").described_as(
            "Query description should include the actual "
            " number of matching events"
        ).contains(
            "Observed 1 events"
        ).described_as(
            "The query description should include a string "
            "representation of the matching events"
        ).contains(
            str(event1)
        )
