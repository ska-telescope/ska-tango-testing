"""The ``hasnt_change_event_occurred`` detects absence of events."""

from datetime import datetime

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.tracer import TangoEventTracer

from ..testing_utils.populate_tracer import add_event, delayed_add_event
from .utils import (
    assert_timeout_in_between,
    expected_error_message_hasnt_event,
)


@pytest.mark.integration_tracer
class TestAssertionsHasntEvent:
    """Verify the ``hasnt_change_event_occurred`` assertion detects events.

    This group of tests verifies that the ``hasnt_change_event_occurred``
    assertion correctly detects the absence of events in the tracer
    (within the timeout) or fails if it does not.
    In other words, this set of tests covers more simple use cases
    for the ``hasnt_change_event_occurred`` assertion.

    The happy path includes the following scenarios:

    - No event has occurred in the past.
    - No event occurs in the future within the timeout.
    - A N number of events can be detected.
    - A N number of events can be detected within a timeout.

    The unhappy path includes the following scenarios:

    - 3 events occur when the maximum expected is 2.

    """

    # ##########################################################
    # Happy Path Tests

    @staticmethod
    def test_assert_that_event_hasnt_occurred_pass_when_no_matching(
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion passes when no event is matching.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device2", 100, 5, attr_name="attrname")
        add_event(tracer, "device1", 100.1, 4, attr_name="attrname")
        add_event(tracer, "device1", 100, 3, attr_name="attrname2")

        assert_that(
            tracer
            # wrong attribute value
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_name="attrname",
            attribute_value=99,
            # wrong device name
        ).hasnt_change_event_occurred(
            device_name="device3",
            attribute_name="attrname",
            attribute_value=100,
            # wrong attribute name
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_name="attrname3",
            attribute_value=100,
            # wrong combination of device and attribute
        ).hasnt_change_event_occurred(
            device_name="device2",
            attribute_name="attrname2",
            # wrong combination of device and value
        ).hasnt_change_event_occurred(
            device_name="device2",
            attribute_value=100.1,
            # wrong combination of attribute and value
        ).hasnt_change_event_occurred(
            attribute_name="attrname2",
            attribute_value=100.1,
        )

    @staticmethod
    def test_assert_that_event_hasnt_occurred_waits_for_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion waits for the timeout before passing.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device0", 100, 1)
        delayed_add_event(tracer, "device1", 100, 2)

        start_time = datetime.now()
        assert_that(tracer).described_as(
            "Expected no matching event to occur within 2 seconds"
        ).within_timeout(1).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=100,
        )

        assert_timeout_in_between(start_time, 1, 2)

    @staticmethod
    def test_assert_that_event_set_havent_occurred_waits_for_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion verifies that no event occurs within timeout.

        When a certain set of event doesn't occur within a timeout,
        the assertion should pass.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 300, 2)
        delayed_add_event(tracer, "device1", 400, 3)

        start_time = datetime.now()
        assert_that(tracer).within_timeout(1).described_as(
            "Expected no matching event to occur within 3 seconds"
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=400,
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=300,
        )

        assert_timeout_in_between(start_time, 1, 2)

    @staticmethod
    def test_assert_that_n_events_havent_occurred(
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion checks that N events didn't occur.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        add_event(tracer, "device1", 100, 1)

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=100,
            max_n_events=3,
        )

    @staticmethod
    def test_assert_that_n_events_havent_occurred_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion waits to checks that N events don't occur.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        add_event(tracer, "device1", 100, 1)
        add_event(tracer, "device1", 200)
        delayed_add_event(tracer, "device1", 100, 2)

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).within_timeout(1).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=100,
            max_n_events=3,
        )

    # ##########################################################
    # Unhappy Path Tests

    @staticmethod
    def test_assert_that_n_events_havent_occurred_captures_n_events_within_timeout(  # pylint: disable=line-too-long # noqa: E501
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion fails when more than N events occur.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        add_event(tracer, "device1", 100, 1)
        add_event(tracer, "device1", 200)
        delayed_add_event(tracer, "device1", 100, 2)

        with pytest.raises(
            AssertionError,
            match=expected_error_message_hasnt_event(
                detected_n_events=3, expected_n_events=3, timeout=3
            ),
        ):
            assert_that(tracer).described_as(
                "The event should match the predicate"
                " if the future value matches within the timeout."
            ).within_timeout(3).hasnt_change_event_occurred(
                device_name="device1",
                attribute_value=100,
                max_n_events=3,
            )
