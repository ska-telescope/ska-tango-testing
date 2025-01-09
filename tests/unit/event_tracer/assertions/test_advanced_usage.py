"""The assertions advanced features work as expected."""


from datetime import datetime

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.tracer import TangoEventTracer

from ..testing_utils.populate_tracer import add_event, delayed_add_event
from .utils import (
    assert_timeout_in_between,
    expected_error_message_has_event,
    expected_error_message_hasnt_event,
)


@pytest.mark.integration_tracer
class TestAssertionsAdvancedUsage:
    """Verify the advanced features of the custom assertions.

    This group of tests verifies a set of advanced use cases for the
    custom assertions of the ``TangoEventTracer``. It includes the following:

    - The custom assertions are able to evaluate the right previous value,
      without being tricked by intermediate events or events from
      other devices or attributes.
    - The custom assertions accepts a custom matchers to evaluate events
      and combine it correctly with the other parameters.
    - The custom assertions are able to stop early if during the evaluation
      of the assertions an early stop sentinel is triggered.
    """

    @staticmethod
    def generate_events(tracer: TangoEventTracer) -> None:
        """Generate a set of events for testing.

        The generated events are a a sequence of past events that
        involve mainly one device 'device1' and one attribute (the default
        one). Their value is integer and generally it increases over time
        (it goes from 100, to 120 to 200). There are added also "noise"
        events from other devices and attributes to try to trick the
        assertions.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 10)
        add_event(tracer, "device1", 120, 9)
        add_event(tracer, "device2", 44, 8)
        add_event(tracer, "device1", 66, 7, attr_name="other_attr")
        add_event(tracer, "device1", 200, 6)

    # ##########################################################
    # Tests: previous value exists and is evaluated correctly

    @staticmethod
    def test_assert_that_has_event_succeeds_when_previous_value_exists(
        tracer: TangoEventTracer,
    ) -> None:
        """The `has` assertion handles a previous value when it exists.

        :param tracer: The `TangoEventTracer` instance.
        """
        TestAssertionsAdvancedUsage.generate_events(tracer)

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

    @staticmethod
    def test_assert_that_hasnt_event_fails_when_previous_value_exists(
        tracer: TangoEventTracer,
    ) -> None:
        """The `hasnt` assertion handles a previous value when it exists.

        :param tracer: The `TangoEventTracer` instance.
        """
        TestAssertionsAdvancedUsage.generate_events(tracer)

        with pytest.raises(
            AssertionError, match=expected_error_message_hasnt_event()
        ):
            assert_that(tracer).hasnt_change_event_occurred(
                device_name="device1",
                attribute_value=200,
                previous_value=120,
            )

    # ##########################################################
    # Tests: previous value does not exist

    @staticmethod
    def test_assert_that_has_event_fails_when_previous_value_not_exists(
        tracer: TangoEventTracer,
    ) -> None:
        """The `has` assertion handles a previous value does not exist.

        :param tracer: The `TangoEventTracer` instance.
        """
        TestAssertionsAdvancedUsage.generate_events(tracer)

        with pytest.raises(
            AssertionError, match=expected_error_message_has_event()
        ):
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
                previous_value=100,
            )

        with pytest.raises(
            AssertionError, match=expected_error_message_has_event()
        ):
            assert_that(tracer).has_change_event_occurred(
                device_name="device2",
                previous_value=44,
            )

        with pytest.raises(
            AssertionError, match=expected_error_message_has_event()
        ):
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_name="other_attr",
                previous_value=66,
            )

    @staticmethod
    def test_assert_that_hasnt_event_succeeds_when_previous_value_not_exists(
        tracer: TangoEventTracer,
    ) -> None:
        """The `hasnt` assertion handles a previous value that does not exist.

        :param tracer: The `TangoEventTracer` instance.
        """
        TestAssertionsAdvancedUsage.generate_events(tracer)

        assert_that(tracer).described_as(
            "Previous value does not exist for device and attribute"
        ).hasnt_change_event_occurred(
            device_name="device2",
            previous_value=120,
        ).hasnt_change_event_occurred(
            attribute_name="other_attr",
            previous_value=120,
        ).described_as(
            "The given previous values have not a consecutive event "
            "for their device and attribute, so they cannot be "
            "previous values"
        ).hasnt_change_event_occurred(
            previous_value=44,
        ).hasnt_change_event_occurred(
            previous_value=66,
        )

    # ##########################################################
    # Tests: previous value is not tricked by intermediate events

    @staticmethod
    def test_assert_that_has_event_is_not_tricked_by_intermediate_events(
        tracer: TangoEventTracer,
    ) -> None:
        """The `has` assertion is not tricked by intermediate events.

        So it should fail when you ask to look for a previous value that
        is not the right one.

        :param tracer: The `TangoEventTracer` instance.
        """
        TestAssertionsAdvancedUsage.generate_events(tracer)

        with pytest.raises(
            AssertionError, match=expected_error_message_has_event()
        ):
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_value=200,
                previous_value=100,
            )

    @staticmethod
    def test_assert_that_hasnt_event_is_not_tricked_by_intermediate_events(
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion is not tricked by intermediate events.

        So it should pass when you ask to look for a previous value that
        is not the right one.

        :param tracer: The `TangoEventTracer` instance.
        """
        TestAssertionsAdvancedUsage.generate_events(tracer)

        assert_that(tracer).described_as(
            "Previous value is not tricked by intermediate events"
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_value=200,
            previous_value=100,
        )

    # ##########################################################
    # Tests: custom matcher

    @staticmethod
    def test_assert_that_has_event_custom_matcher_matches_event(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom matcher matches the event when it happened.

        (In the has_change_event_occurred assertion)

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5, attr_name="attrname")

        assert_that(tracer).described_as(
            "The custom matcher should match the event"
        ).has_change_event_occurred(
            device_name="device1",
            attribute_name="attrname",
            custom_matcher=lambda e: e.attribute_value > 50
            and e.attribute_value < 150,
        )

    @staticmethod
    def test_assert_that_hasnt_event_custom_matcher_matches_event(
        tracer: TangoEventTracer,
    ) -> None:
        """The custom matcher matches the event when it happened.

        (In the hasnt_change_event_occurred assertion)

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5, attr_name="attrname")

        assert_that(tracer).described_as(
            "The custom matcher should match the event"
        ).hasnt_change_event_occurred(
            device_name="device1",
            attribute_name="attrname",
            custom_matcher=lambda e: e.attribute_value > 150,
        )

        with pytest.raises(
            AssertionError, match=expected_error_message_hasnt_event()
        ):
            assert_that(tracer).described_as(
                "The custom matcher should match the event"
            ).hasnt_change_event_occurred(
                device_name="device1",
                attribute_name="attrname",
                custom_matcher=lambda e: e.attribute_value > 50,
            )

    # ##########################################################
    # Tests: early stop

    @staticmethod
    def test_assert_that_has_event_fails_with_early_stop(
        tracer: TangoEventTracer,
    ) -> None:
        """The 'has' assertion fails when the sentinel triggers early stop.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5)
        add_event(tracer, "device1", "STOP NOW", 4)

        # TODO: add message match
        with pytest.raises(AssertionError):
            assert_that(tracer).described_as(
                "The sentinel should trigger the early stop"
            ).with_early_stop(
                lambda e: e.attribute_value == "STOP NOW"
            ).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
            )

    @staticmethod
    def test_assert_hat_has_event_early_stop_interrupts_timeout_wait(
        tracer: TangoEventTracer,
    ) -> None:
        """The 'has' assertion with early stop interrupts the timeout wait.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", "STOP NOW", 0.5)
        delayed_add_event(tracer, "device1", 100, 1)

        start_time = datetime.now()
        with pytest.raises(AssertionError):
            assert_that(tracer).described_as(
                "The sentinel should interrupt the given timeout "
                "before the matching event may occur"
            ).within_timeout(2).with_early_stop(
                lambda e: e.attribute_value == "STOP NOW"
            ).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
            )

        assert_timeout_in_between(start_time, 0.5, 1)

    @staticmethod
    def test_assert_that_has_event_succeeds_if_sentinel_occurs_after_success(
        tracer: TangoEventTracer,
    ) -> None:
        """The 'has' assertion succeeds if success > sentinel.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 100, 0.5)
        delayed_add_event(tracer, "device1", "STOP NOW", 0.55)

        assert_that(tracer).described_as(
            "The sentinel should not trigger the early stop"
        ).with_early_stop(
            lambda e: e.attribute_value == "STOP NOW"
        ).within_timeout(
            1
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=100,
        )

    @staticmethod
    def test_assert_that_hasnt_event_stop_interrupts_timeout_wait(
        tracer: TangoEventTracer,
    ) -> None:
        """The 'hasnt' assertion with early stop interrupts the timeout wait.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", "STOP NOW", 0.5)

        start_time = datetime.now()
        with pytest.raises(AssertionError):
            assert_that(tracer).described_as(
                "The sentinel should interrupt the given timeout "
                "before any matching event may occur"
            ).within_timeout(1).with_early_stop(
                lambda e: e.attribute_value == "STOP NOW"
            ).hasnt_change_event_occurred(
                device_name="device1",
                attribute_value=100,
            )

        assert_timeout_in_between(start_time, 0.5, 1)

    @staticmethod
    def test_assert_that_among_multiple_early_stop_the_last_is_used(
        tracer: TangoEventTracer,
    ) -> None:
        """The last sentinel predicate is used when multiple are chained.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5)
        add_event(tracer, "device1", "STOP NOW", 4)

        assert_that(tracer).described_as(
            "The last sentinel predicate should be used"
        ).with_early_stop(
            lambda e: e.attribute_value == "STOP NOW"
        ).with_early_stop(
            lambda e: e.attribute_value == "STOP NOW (not really)"
        ).has_change_event_occurred(
            device_name="device1",
            attribute_value=100,
        )
