"""Test the custom predicates for the :py:class:`TangoEventTracer`.

Ensure that the custom predicates for the :py:class:`TangoEventTracer` work
as expected, matching the correct events and values.
"""
from unittest.mock import MagicMock

import pytest
import tango
from assertpy import assert_that  # type: ignore
from pytest import fixture

from ska_tango_testing.integration.predicates import (
    event_has_previous_value,
    event_matches_parameters,
)
from ska_tango_testing.integration.tracer import TangoEventTracer
from tests.unit.event_tracer.testing_utils.received_event_mock import (
    create_dummy_event,
)


@pytest.mark.Tracer
class TestCustomPredicates:
    """Test the custom predicates for the :py:class:`TangoEventTracer`.

    Ensure that the custom predicates for the :py:class:`TangoEventTracer` work
    as expected, matching the correct events and values.
    """

    @fixture
    @staticmethod
    def tracer() -> MagicMock:
        """Mock a tracer with an empty and accessible list of events.

        :return: A mocked `TangoEventTracer` with a writable empty
            list of events.
        """
        tracer = MagicMock(spec=TangoEventTracer)
        tracer.events = []
        return tracer

    # #######################################################
    # Tests for the build_previous_value_predicate function

    @staticmethod
    def test_predicate_event_predicate_matches() -> None:
        """An event should match the predicate if all fields match."""
        event = create_dummy_event("test/device/1", "attr1", 10)

        assert_that(
            event_matches_parameters(
                target_event=event,
                device_name="test/device/1",
                attribute_name="attr1",
                attribute_value=10,
            )
        ).described_as(
            "The event should match the predicate if all fields match."
        ).is_true()

    @staticmethod
    def test_predicate_event_predicate_soft_match() -> None:
        """An event matches the predicate if specified fields match."""
        event = create_dummy_event("test/device/1", "attr1", 10)

        assert_that(
            event_matches_parameters(target_event=event, attribute_value=10)
        ).described_as(
            "The event should match the predicate"
            " if the specified fields match."
        ).is_true()

    @staticmethod
    def test_predicate_tango_state_matches() -> None:
        """An event match when attribute is a :py:class:`tango.DevState`."""
        event = create_dummy_event("test/device/1", "state", tango.DevState.ON)

        assert_that(
            event_matches_parameters(
                target_event=event,
                device_name="test/device/1",
                attribute_name="state",
                attribute_value=tango.DevState.ON,
            )
        ).described_as(
            "The event should match the predicate"
            " if the specified fields match."
        ).is_true()

    @staticmethod
    def test_predicate_event_predicate_does_not_match() -> None:
        """An event matches the predicate if any field does not match."""
        event = create_dummy_event("test/device/1", "attr1", 10)

        assert_that(
            event_matches_parameters(
                target_event=event,
                device_name="test/device/1",
                attribute_name="attr1",
                attribute_value=11,
            )
        ).described_as(
            "The event should not match the predicate if a specified "
            "field does not match."
        ).is_false()

    # #######################################################
    # Tests for the build_previous_value_predicate function

    @staticmethod
    def test_predicate_previous_value_predicate_matches(
        tracer: MagicMock,
    ) -> None:
        """An event matches the predicate if the previous value matches.

        :param tracer: A mock TangoEventTracer.
        """
        event = create_dummy_event("test/device/1", "attr1", 10)
        prev_event = create_dummy_event(
            "test/device/1", "attr1", 5, seconds_ago=2
        )
        tracer.events = [prev_event, event]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The event should match the predicate"
            " if the previous value matches."
        ).is_true()

    @staticmethod
    def test_predicate_previous_value_predicate_does_not_match(
        tracer: MagicMock,
    ) -> None:
        """An event matches the predicate if the previous value does not match.

        :param tracer: A mock TangoEventTracer.
        """
        event = create_dummy_event("test/device/1", "attr1", 10)
        prev_event = create_dummy_event(
            "test/device/1", "attr1", 5, seconds_ago=2
        )
        tracer.events = [prev_event, event]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=6
            )
        ).described_as(
            "The event should not match the predicate if the previous value "
            "does not match."
        ).is_false()

    @staticmethod
    def test_predicate_previous_value_predicate_no_previous_event(
        tracer: MagicMock,
    ) -> None:
        """An event doesn't match the predicate if there is no previous event.

        :param tracer: A mock TangoEventTracer.
        """
        event = create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [event]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=10
            )
        ).described_as(
            "The event should not match the predicate because there is no "
            "previous event. It may be predicate matched with the event "
            "itself."
        ).is_false()

    @staticmethod
    def test_predicate_previous_uses_most_recent(tracer: MagicMock) -> None:
        """An event previous value is the most recent of the past events.

        :param tracer: A mock TangoEventTracer.
        """
        event = create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            create_dummy_event("test/device/1", "attr1", 5, seconds_ago=10),
            create_dummy_event("test/device/1", "attr1", 7, seconds_ago=8),
            event,
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should check the most recent previous event, not "
            "just one of the previous events or just one which matches"
        ).is_false()

    @staticmethod
    def test_predicate_previous_doesnt_use_future_events(
        tracer: MagicMock,
    ) -> None:
        """An event previous value should not be from future events.

        :param tracer: A mock TangoEventTracer.
        """
        event = create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            event,
            create_dummy_event("test/device/1", "attr1", 5, seconds_ago=-1),
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should not consider future events."
        ).is_false()

    @staticmethod
    def test_predicate_previous_doesnt_use_other_devices(
        tracer: MagicMock,
    ) -> None:
        """An event previous value should not be from other devices.

        :param tracer: A mock TangoEventTracer.
        """
        event = create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            create_dummy_event("test/device/2", "attr1", 5, seconds_ago=1),
            event,
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should not consider events from other devices."
        ).is_false()

    @staticmethod
    def test_predicate_previous_doesnt_use_other_attributes(
        tracer: MagicMock,
    ) -> None:
        """An event previous value should not be from other attributes.

        :param tracer: A mock TangoEventTracer.
        """
        event = create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            create_dummy_event("test/device/1", "attr2", 5, seconds_ago=1),
            event,
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should not consider events from other attributes."
        ).is_false()
