"""Test the custom predicates for the :py:class:`TangoEventTracer`.

Ensure that the custom predicates for the :py:class:`TangoEventTracer` work
as expected, matching the correct events and values.
"""


from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
import tango
from assertpy import assert_that  # type: ignore
from pytest import fixture

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.predicates import (  # pylint: disable=line-too-long # noqa: E501
    event_has_previous_value,
    event_matches_parameters,
)
from ska_tango_testing.integration.tracer import TangoEventTracer


@pytest.mark.Tracer
class TestCustomPredicates:
    """Test the custom predicates for the :py:class:`TangoEventTracer`.

    Ensure that the custom predicates for the :py:class:`TangoEventTracer` work
    as expected, matching the correct events and values.
    """

    @staticmethod
    def create_dummy_event(
        device_name: str,
        attribute_name: str,
        attribute_value: Any,
        seconds_ago: float = 0,
    ) -> MagicMock:
        """Create a dummy :py:class:`ReceivedEvent` with the specified params.

        :param device_name: The device name.
        :param attribute_name: The attribute name.
        :param attribute_value: The attribute value.
        :param seconds_ago: The time in seconds since the event was received.

        :return: A dummy :py:class:`ReceivedEvent`.
        """
        event = MagicMock(spec=ReceivedEvent)
        event.device_name = device_name
        event.attribute_name = attribute_name
        event.attribute_value = attribute_value
        event.reception_time = datetime.now() - timedelta(seconds=seconds_ago)
        event.has_device = (
            lambda target_device_name: event.device_name == target_device_name
        )
        event.has_attribute = (
            lambda target_attribute_name: event.attribute_name
            == target_attribute_name
        )
        return event

    @fixture
    @staticmethod
    def tracer() -> MagicMock:
        """Mock a tracer with an empty and accessible list of events.

        :return: A mock TangoEventTracer.
        """
        tracer = MagicMock(spec=TangoEventTracer)
        tracer.events = []
        return tracer

    # #######################################################
    # Tests for the build_previous_value_predicate function

    def test_predicate_event_predicate_mock_matches(self) -> None:
        """An event should match the predicate if all fields match."""
        event = self.create_dummy_event("test/device/1", "attr1", 10)

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

    def test_predicate_event_predicate_soft_match(self) -> None:
        """An event matches the predicate if specified fields match."""
        event = self.create_dummy_event("test/device/1", "attr1", 10)

        assert_that(
            event_matches_parameters(target_event=event, attribute_value=10)
        ).described_as(
            "The event should match the predicate"
            " if the specified fields match."
        ).is_true()

    def test_predicate_tango_state_matches(self) -> None:
        """An event match when attribute is a :py:class:`tango.DevState`."""
        event = self.create_dummy_event(
            "test/device/1", "state", tango.DevState.ON
        )

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

    def test_predicate_event_predicate_does_not_match(self) -> None:
        """An event matches the predicate if any field does not match."""
        event = self.create_dummy_event("test/device/1", "attr1", 10)

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

    def test_predicate_previous_value_predicate_matches(
        self, tracer: MagicMock
    ) -> None:
        """An event matches the predicate if the previous value matches.

        :param tracer: A mock TangoEventTracer.
        """
        event = self.create_dummy_event("test/device/1", "attr1", 10)
        prev_event = self.create_dummy_event(
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

    def test_predicate_previous_value_predicate_does_not_match(
        self, tracer: MagicMock
    ) -> None:
        """An event matches the predicate if the previous value does not match.

        :param tracer: A mock TangoEventTracer.
        """
        event = self.create_dummy_event("test/device/1", "attr1", 10)
        prev_event = self.create_dummy_event(
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

    def test_predicate_previous_value_predicate_no_previous_event(
        self, tracer: MagicMock
    ) -> None:
        """An event doesn't match the predicate if there is no previous event.

        :param tracer: A mock TangoEventTracer.
        """
        event = self.create_dummy_event("test/device/1", "attr1", 10)

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

    def test_predicate_previous_uses_most_recent(
        self, tracer: MagicMock
    ) -> None:
        """An event previous value is the most recent of the past events.

        :param tracer: A mock TangoEventTracer.
        """
        event = self.create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            self.create_dummy_event(
                "test/device/1", "attr1", 5, seconds_ago=10
            ),
            self.create_dummy_event(
                "test/device/1", "attr1", 7, seconds_ago=8
            ),
            event,
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should check the most recent previous event, not "
            "just one of the previous events or just one which mathces"
        ).is_false()

    def test_predicate_previous_doesnt_use_future_events(
        self, tracer: MagicMock
    ) -> None:
        """An event previous value should not be from future events.

        :param tracer: A mock TangoEventTracer.
        """
        event = self.create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            event,
            self.create_dummy_event(
                "test/device/1", "attr1", 5, seconds_ago=-1
            ),
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should not consider future events."
        ).is_false()

    def test_predicate_previous_doesnt_use_other_devices(
        self, tracer: MagicMock
    ) -> None:
        """An event previous value should not be from other devices.

        :param tracer: A mock TangoEventTracer.
        """
        event = self.create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            self.create_dummy_event(
                "test/device/2", "attr1", 5, seconds_ago=1
            ),
            event,
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should not consider events from other devices."
        ).is_false()

    def test_predicate_previous_doesnt_use_other_attributes(
        self, tracer: MagicMock
    ) -> None:
        """An event previous value should not be from other attributes.

        :param tracer: A mock TangoEventTracer.
        """
        event = self.create_dummy_event("test/device/1", "attr1", 10)

        tracer.events = [
            self.create_dummy_event(
                "test/device/1", "attr2", 5, seconds_ago=1
            ),
            event,
        ]

        assert_that(
            event_has_previous_value(
                target_event=event, tracer=tracer, previous_value=5
            )
        ).described_as(
            "The predicate should not consider events from other attributes."
        ).is_false()
