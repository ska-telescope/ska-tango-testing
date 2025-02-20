"""The ``has_change_event_occurred`` detects presence of events."""

from datetime import datetime

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.tracer import TangoEventTracer

from ..testing_utils.populate_tracer import add_event, delayed_add_event
from .utils import assert_elapsed_time, expected_error_message_has_event


@pytest.mark.integration_tracer
class TestAssertionsHasEvent:
    """Verify the ``has_change_event_occurred`` assertion detects events.

    This group of tests verifies that the ``has_change_event_occurred``
    assertion correctly detects the presence of events in the tracer
    (within the timeout) or fails if it does not.
    In other words, this set of tests covers more simple use cases
    for the ``has_change_event_occurred`` assertion.

    The happy path includes the following scenarios:

    - The event has occurred in the past.
    - The event occurs in the future within the timeout.
    - A N number of events can be detected.
    - A N number of events can be detected within a timeout.
    - A chain of different events may occur within the same timeout.

    The unhappy path includes the following scenarios:

    - The event has not occurred.
    - The event has not occurred within the timeout.
    - Not all events of a chain occur within the timeout.
    - Less than the expected N events occur.

    """

    # ##########################################################
    # Happy Path Tests

    @staticmethod
    def test_assert_that_event_occurred_captures_past_event(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion for previous value.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 101, 5, attr_name="attrname")

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the previous value matches."
            # match with all attributes work as expected
        ).has_change_event_occurred(
            device_name="device1",
            attribute_name="attrname",
            attribute_value=101,
            # match with just some attributes work as expected
        ).has_change_event_occurred(
            device_name="device1",
        ).has_change_event_occurred(
            attribute_name="attrname",
        ).has_change_event_occurred(
            attribute_value=101,
        )

    @staticmethod
    def test_assert_that_event_occurred_captures_future_event_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion for future value within timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 101, 1)

        start_time = datetime.now()
        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).within_timeout(3).has_change_event_occurred(
            device_name="device1",
            attribute_value=101,
        )

        assert_elapsed_time(start_time, 1)

    @staticmethod
    def test_assert_that_n_events_occurred_captures_n_events(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion checks that at least N events occurred.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 101, 3)
        add_event(tracer, "device1", 99, 2)
        add_event(tracer, "device1", 101, 1)

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=101,
            min_n_events=2,
        )

    @staticmethod
    def test_assert_that_n_events_occurred_captures_n_events_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion waits for N events within the timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 101, 3)
        add_event(tracer, "device1", 99, 2)
        delayed_add_event(tracer, "device1", 101, 1)

        start_time = datetime.now()
        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).within_timeout(3).has_change_event_occurred(
            device_name="device1",
            attribute_value=101,
            min_n_events=2,
        )

        assert_elapsed_time(start_time, 1)

    @staticmethod
    def test_assert_that_has_change_event_occurred_chain_under_same_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertions can be chained under the same timeout.

        The order is not important, as long as the events occur within
        the same timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 101, 5)
        delayed_add_event(tracer, "device1", 301, 1)
        delayed_add_event(tracer, "device1", 202, 2)

        start_time = datetime.now()
        assert_that(tracer).described_as(
            "The events should match the predicates"
            " if they occur within the same timeout."
        ).within_timeout(4).has_change_event_occurred(
            device_name="device1",
            attribute_value=101,
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=202,
            # NOTE: here we show that order is clearly not important
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=301,
        )

        assert_elapsed_time(start_time, 2)

    # ##########################################################
    # Unhappy Path Tests

    @staticmethod
    def test_assert_that_event_occurred_fails_when_no_event(
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails when no matching event occurs.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device2", 100.1, 5, attr_name="attrname")
        add_event(tracer, "device1", 100.2, 4, attr_name="attrname")
        add_event(tracer, "device1", 100.1, 3, attr_name="attrname2")

        with pytest.raises(
            AssertionError, match=expected_error_message_has_event()
        ):
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_name="attrname",
                attribute_value=100.1,
            )

    @staticmethod
    def test_assert_that_event_occurred_fails_when_no_event_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails when no matching event occurs within timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 101, 2)

        start_time = datetime.now()
        with pytest.raises(
            AssertionError,
            match=expected_error_message_has_event(timeout=1),
        ):
            assert_that(tracer).within_timeout(1).has_change_event_occurred(
                device_name="device1",
                attribute_value=101,
            )

        assert_elapsed_time(start_time, 1)

    @staticmethod
    def test_assert_that_evt_occurred_fails_when_not_all_events_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails when not all event occur within a timeout.

        When there is a set of events, asserted within the same timeout,
        all of them must occur within that timeout. If one of them doesn't
        occur, the assertion should fail.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 101, 0.5)
        delayed_add_event(tracer, "device1", 202, 1)
        delayed_add_event(tracer, "device1", 404, 2)

        start_time = datetime.now()
        with pytest.raises(
            AssertionError,
            match=expected_error_message_has_event(timeout=1.5),
        ):
            assert_that(tracer).within_timeout(1.5).has_change_event_occurred(
                device_name="device1",
                attribute_value=101,
            ).has_change_event_occurred(
                device_name="device1",
                attribute_value=202,
            ).has_change_event_occurred(
                device_name="device1",
                attribute_value=404,  # TODO: this one should fail
            )

        assert_elapsed_time(start_time, 1.5)

    @staticmethod
    def test_assert_that_n_events_occurred_fails_when_less_than_n_events(
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails if less than N events occurs.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 101, 3)
        add_event(tracer, "device1", 99, 2)
        delayed_add_event(tracer, "device1", 101, 1)

        start_time = datetime.now()
        with pytest.raises(
            AssertionError,
            match=expected_error_message_has_event(
                detected_n_events=2, expected_n_events=3, timeout=2
            ),
        ):
            assert_that(tracer).described_as(
                "The event should match the predicate"
                " if the future value matches within the timeout."
            ).within_timeout(2).has_change_event_occurred(
                device_name="device1",
                attribute_value=101,
                min_n_events=3,
            )

        assert_elapsed_time(start_time, 2)
