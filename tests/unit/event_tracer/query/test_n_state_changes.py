"""Unit tests for the NStateChangesQuery class."""


import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event.storage import EventStorage
from ska_tango_testing.integration.query.n_state_changes import (
    NStateChangesQuery,
)

from ..testing_utils.delayed_store_event import delayed_store_event
from ..testing_utils.received_event_mock import create_test_event
from .utils import (
    assert_n_events_match_query_failed,
    assert_n_events_match_query_succeeded,
    assert_timeout_and_duration_consistency,
)


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
        # create the event with the previous value
        create_test_event(value=41, store=storage)
        # create the event with the new value (matching the query)
        matching_event = create_test_event(value=42, store=storage)
        # create some non-matching events
        create_test_event(device_name="test/device/2", store=storage)
        create_test_event(attr_name="other_attr", store=storage)

        query.evaluate(storage)

        assert_n_events_match_query_succeeded(query, [matching_event])

    @staticmethod
    def test_query_succeeds_with_multiple_matching_events() -> None:
        """Test that the query succeeds with multiple matching events."""
        storage = EventStorage()
        query = NStateChangesQuery(
            device_name="test/device/1",
            attribute_name="test_attr",
            attribute_value=42,
            target_n_events=2,
            timeout=5,
        )
        event1 = create_test_event(store=storage)
        event2 = create_test_event()
        delayed_store_event(storage, event2, delay=1)

        query.evaluate(storage)

        assert_n_events_match_query_succeeded(query, [event1, event2])
        assert_timeout_and_duration_consistency(query, 5, 1)

    @staticmethod
    def test_query_fails_when_no_event_matches_when_prev_value_miss() -> None:
        """Test that the query fails when no event matches."""
        storage = EventStorage()
        query = NStateChangesQuery(
            attribute_value=42,
            previous_value=41,
        )
        # potentially matching event that will not match because of previous
        create_test_event(value=42, store=storage)

        query.evaluate(storage)

        assert_n_events_match_query_failed(query)

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
        # a fake previous value that should not match
        create_test_event(value=41, store=storage)
        # the real previous value (different than expected)
        create_test_event(value=40, store=storage)
        # some noise (diff device, diff attr)
        create_test_event(device_name="test/device/2", value=41, store=storage)
        create_test_event(attr_name="test_attr2", value=41, store=storage)
        # the event that will not match because of the previous value
        create_test_event(value=42, store=storage)

        query.evaluate(storage)

        assert_n_events_match_query_failed(query)

    @staticmethod
    def test_query_applies_custom_matcher() -> None:
        """Test that the query applies a custom matcher."""
        storage = EventStorage()
        query = NStateChangesQuery(
            device_name="test/device/1",
            attribute_name="test_attr",
            custom_matcher=lambda e: str(e.attribute_value).endswith("2"),
        )
        # non-matching event because of the custom matcher
        create_test_event(value=41, store=storage)
        # matching event
        event = create_test_event(value=42, store=storage)
        # non-matching events because of device name and attribute name
        create_test_event(device_name="test/device/2", value=42, store=storage)
        create_test_event(attr_name="test_attr2", value=42, store=storage)

        query.evaluate(storage)

        assert_n_events_match_query_succeeded(query, [event])

    @staticmethod
    def test_query_description_includes_passed_criteria() -> None:
        """The query description includes the passed criteria."""
        query = NStateChangesQuery(
            device_name="test/device/1",
            attribute_name="test_attr",
            attribute_value=42,
        )

        description = query.describe()
        assert_that(description).described_as(
            "Query description should include the passed criteria"
        ).contains("device_name='test/device/1'").contains(
            "attribute_name=test_attr"
        ).contains(
            "attribute_value=42"
        ).described_as(
            "Query description should not include the non-passed criteria"
        ).does_not_contain(
            "previous_value="
        ).does_not_contain(
            "custom matcher"
        )
