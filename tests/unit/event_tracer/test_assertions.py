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

    @staticmethod
    def test_assert_that_has_change_event_occurred_chain_under_same_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertions can be chained under the same timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5)
        delayed_add_event(tracer, "device1", 300, 1)
        delayed_add_event(tracer, "device1", 200, 2)

        assert_that(tracer).within_timeout(10).described_as(
            "The events should match the predicates"
            " if they occur within the same timeout."
        ).within_timeout(3).has_change_event_occurred(
            device_name="device1",
            attribute_value=100,
            # NOTE: here we show that order is clearly not important
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=200,
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=300,
        )

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
    def test_assert_that_evt_occurred_fails_when_not_all_events_within_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The a. fails when one of the events doesn't occur within a timeout.

        When there is a set of events, asserted within the same timeout,
        all of them must occur within that timeout. If one of them doesn't
        occur, the assertion should fail.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 100, 1)
        delayed_add_event(tracer, "device1", 200, 2)
        delayed_add_event(tracer, "device1", 400, 4)

        start_time = datetime.now()
        with pytest.raises(AssertionError):
            assert_that(tracer).within_timeout(3).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
            ).has_change_event_occurred(
                device_name="device1",
                attribute_value=200,
            ).has_change_event_occurred(
                device_name="device1",
                attribute_value=400,  # TODO: verify this is the one that fails
            )

        assert_that(
            (datetime.now() - start_time).total_seconds()
        ).described_as(
            "Expected wait time to be >=3s and <4s"
        ).is_greater_than_or_equal_to(
            3
        ).is_less_than(
            4
        )

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

    @staticmethod
    def test_assert_that_event_set_havent_occurred_waits_for_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom assertion verifies that no event occurs within timeout.

        When a certain set of event doesn't occur within a timeout,
        the assertion should pass.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 300, 3)
        delayed_add_event(tracer, "device1", 400, 4)

        start_time = datetime.now()
        assert_that(tracer).within_timeout(2).described_as(
            "Expected no matching event to occur within 3 seconds"
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=400,
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=300,
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
