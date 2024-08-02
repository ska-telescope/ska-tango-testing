"""Unit tests for `TangoEventTracer` custom assertions."""

from datetime import datetime

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.tracer import TangoEventTracer
from tests.unit.event_tracer.testing_utils.populate_tracer import (
    add_event,
    delayed_add_event,
)


class TestCustomAssertions:
    """Test the custom assertions for the :py:class:`TangoEventTracer`.

    Ensure that the custom assertions for the :py:class:`TangoEventTracer`
    work as expected, matching the correct events and values, passing
    when they should and raising an ``AssertionError`` when they should
    fail.

    Verify tricky cases, such as delayed events, correct use of timeouts,
    partial matches, correct evaluation of previous event and so on.
    """

    @staticmethod
    def _assert_exposes(tracer: TangoEventTracer, assertion_name: str) -> None:
        """Check that a custom assertion is exposed.

        :param tracer: The `TangoEventTracer` instance.
        :param assertion_name: The name of the custom assertion.
        """
        custom = getattr(assert_that(tracer), assertion_name, None)
        assert_that(custom).described_as(
            f"Expected the custom assertion '{assertion_name}' "
            "to be exposed."
        ).is_not_none()
        assert_that(callable(custom)).described_as(
            f"Expected the custom assertion '{assertion_name}' "
            "to be a callable."
        ).is_true()

    def test_assert_that_exposes_custom_assertions(
        self, tracer: TangoEventTracer
    ) -> None:
        """The custom assertions are exposed.

        :param tracer: The `TangoEventTracer` instance.
        """
        self._assert_exposes(tracer, "has_change_event_occurred")
        self._assert_exposes(tracer, "hasnt_change_event_occurred")
        self._assert_exposes(tracer, "within_timeout")

    # ##########################################################
    # Tests: assert has change events occurred

    @staticmethod
    def test_assert_that_event_occurred_captures_past_event(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion for previous value.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5, attr_name="attrname")

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the previous value matches."
            # match with all attributes work as expected
        ).has_change_event_occurred(
            device_name="device1",
            attribute_name="attrname",
            attribute_value=100,
            # match with just some attributes work as expected
        ).has_change_event_occurred(
            device_name="device1",
        ).has_change_event_occurred(
            attribute_name="attrname",
        ).has_change_event_occurred(
            attribute_value=100,
        )

    @staticmethod
    def test_assert_that_event_occurred_captures_future_event_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion for future value within timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 100, 2)

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).within_timeout(3).has_change_event_occurred(
            device_name="device1",
            attribute_value=100,
        )

    # ##########################################################
    # Tests: assert has change events occurred (n events)

    @staticmethod
    def test_assert_that_n_events_occurred_captures_n_events(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion checks that at least N events occurred.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        add_event(tracer, "device1", 100, 1)

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=100,
            min_n_events=2,
        )

    @staticmethod
    def test_assert_that_n_events_occurred_captures_n_events_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion waits for N events within the timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        delayed_add_event(tracer, "device1", 100, 2)

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).within_timeout(3).has_change_event_occurred(
            device_name="device1",
            attribute_value=100,
            min_n_events=2,
        )

    # ##########################################################
    # Tests: assert has change events occurred fails

    @staticmethod
    def test_assert_that_event_occurred_fails_when_no_event(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion fails when no matching event occurs.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device2", 100, 5, attr_name="attrname")
        add_event(tracer, "device1", 100.1, 4, attr_name="attrname")
        add_event(tracer, "device1", 100, 3, attr_name="attrname2")

        with pytest.raises(AssertionError):
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_name="attrname",
                attribute_value=100,
            )

    @staticmethod
    def test_assert_that_event_occurred_fails_when_no_event_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom ass. fails when no matching event occurs within timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 100, 3)

        start_time = datetime.now()
        with pytest.raises(AssertionError):
            assert_that(tracer).within_timeout(2).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
            )

        assert_that(
            (datetime.now() - start_time).total_seconds()
        ).described_as(
            "Expected wait time to be >=2s and <3s"
        ).is_greater_than_or_equal_to(
            2
        ).is_less_than(
            3
        )

    @staticmethod
    def test_assert_that_n_events_occurred_fails_when_less_than_n_events(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion fails if less than N events occurs.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        delayed_add_event(tracer, "device1", 100, 2)

        with pytest.raises(
            AssertionError,
            match="Expected to find 3 event(s) matching the predicate",
        ):
            assert_that(tracer).described_as(
                "The event should match the predicate"
                " if the future value matches within the timeout."
            ).within_timeout(3).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
                min_n_events=3,
            )

    # ##########################################################
    # Tests: assert hasnt change events occurred

    @staticmethod
    def test_assert_that_event_hasnt_occurred_pass_when_no_matching(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion pass when no event is matching.

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
        """The custom assertion waits for the timeout to pass.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device0", 100, 1)
        delayed_add_event(tracer, "device1", 100, 3)

        start_time = datetime.now()
        assert_that(tracer).described_as(
            "Expected no matching event to occur within 2 seconds"
        ).within_timeout(2).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=100,
        )

        assert_that(
            (datetime.now() - start_time).total_seconds()
        ).described_as(
            "Expected wait time to be >=2 and <3"
        ).is_greater_than_or_equal_to(
            2
        ).is_less_than(
            3
        )

    # ##########################################################
    # Tests: assert hasnt change events occurred (n events)

    @staticmethod
    def test_assert_that_n_events_havent_occurred(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion checks that N events didn't occur.

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
        """The custom assertion waits to checks that N events don't occur.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        add_event(tracer, "device1", 100, 1)
        add_event(tracer, "device1", 200)
        delayed_add_event(tracer, "device1", 100, 5)

        assert_that(tracer).described_as(
            "The event should match the predicate"
            " if the future value matches within the timeout."
        ).within_timeout(3).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=100,
            max_n_events=3,
        )

    @staticmethod
    def test_assert_that_n_events_havent_occurred_captures_n_events_within_timeout(  # pylint: disable=line-too-long # noqa: E501
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion fails when more than N events occur.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        add_event(tracer, "device1", 100, 1)
        add_event(tracer, "device1", 200)
        delayed_add_event(tracer, "device1", 100, 5)

        with pytest.raises(AssertionError):
            assert_that(tracer).described_as(
                "The event should match the predicate"
                " if the future value matches within the timeout."
            ).within_timeout(6).hasnt_change_event_occurred(
                device_name="device1",
                attribute_value=100,
                max_n_events=3,
            )

    # ##########################################################
    # Tests: assert has/hasnt events with previous value

    @staticmethod
    def test_assert_that_event_occurred_handles_previous(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion handles correctly the previous value.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 10)
        add_event(tracer, "device1", 120, 9)
        add_event(tracer, "device2", 44, 8)
        add_event(tracer, "device1", 66, 7, attr_name="other_attr")
        add_event(tracer, "device1", 200, 6)

        # ----------------------------------------------------
        # previous value is correctly caught when it exists
        assert_that(tracer).described_as(
            "Previous value is correctly caught when it exists"
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=120,
            previous_value=100,
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=200,
            previous_value=120,
        )

        with pytest.raises(AssertionError):
            assert_that(tracer).hasnt_change_event_occurred(
                device_name="device1",
                attribute_value=200,
                previous_value=120,
            )

        # ----------------------------------------------------
        # previous value is not caught when it does not exist

        with pytest.raises(AssertionError):
            # When there is no previous value, it should fail
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
                previous_value=100,
            )

        with pytest.raises(AssertionError):
            # Again, when there is no previous value, it should fail
            assert_that(tracer).has_change_event_occurred(
                device_name="device2",
                previous_value=44,
            )

        with pytest.raises(AssertionError):
            # Again a third time,
            # when there is no previous value, it should fail
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_name="other_attr",
                previous_value=66,
            )

        assert_that(tracer).described_as(
            "Previous value does not exist but it's still caught"
        ).hasnt_change_event_occurred(
            device_name="device2",
            previous_value=120,
        ).hasnt_change_event_occurred(
            attribute_name="other_attr",
            previous_value=120,
        ).hasnt_change_event_occurred(
            previous_value=44,
        ).hasnt_change_event_occurred(
            previous_value=66,
        )

        # previous value is not tricked by intermediate events
        with pytest.raises(AssertionError):
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_value=200,
                previous_value=100,
            )
        assert_that(tracer).described_as(
            "Previous value is not tricked by intermediate events"
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=200,
            previous_value=100,
        )
