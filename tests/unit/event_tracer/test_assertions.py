"""Unit tests for `TangoEventTracer` custom assertions."""

from datetime import datetime

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.tracer import TangoEventTracer

from .testing_utils.populate_tracer import add_event, delayed_add_event


@pytest.mark.integration_tracer
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
        """Check that a custom assertion is accessible and callable.

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
    def _expected_error_message_has_event(
        detected_n_events: int = 0,
        expected_n_events: int = 1,
        timeout: int | None = None,
    ) -> str:
        """Create a regular expression for error message validation.

        This method returns a regex pattern fragment intended
        to match the start of an error message when an event assertion fails.
        It is parametrized with the number of detected events (defaults to
        0, since it is the most common case), the number of expected events
        (defaults to 1, since it is the most common case) and the timeout
        value (defaults to None, since in most of the tests it is not
        specified).

        :param detected_n_events: The number of events detected.
        :param expected_n_events: The number of events expected.
        :param timeout: The timeout value. By default, it is not specified.
        :return: The regex pattern fragment to match the start of
            the error message.
        """
        res = rf"(?:Expected to find {expected_n_events} event\(s\) "
        res += "matching the predicate "

        if timeout is not None:
            res += f"within {timeout} seconds"
        else:
            res += "in already existing events"
        res += f", but only {detected_n_events} found.)"

        return res

    def test_assert_that_event_occurred_fails_when_no_event(
        self,
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails when no matching event occurs.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device2", 100, 5, attr_name="attrname")
        add_event(tracer, "device1", 100.1, 4, attr_name="attrname")
        add_event(tracer, "device1", 100, 3, attr_name="attrname2")

        with pytest.raises(
            AssertionError, match=self._expected_error_message_has_event()
        ):
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_name="attrname",
                attribute_value=100,
            )

    def test_assert_that_event_occurred_fails_when_no_event_within_timeout(
        self,
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails when no matching event occurs within timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 100, 3)

        start_time = datetime.now()
        with pytest.raises(
            AssertionError,
            match=self._expected_error_message_has_event(timeout=2),
        ):
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

    def test_assert_that_evt_occurred_fails_when_not_all_events_within_timeout(
        self,
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails when not all event occur within a timeout.

        When there is a set of events, asserted within the same timeout,
        all of them must occur within that timeout. If one of them doesn't
        occur, the assertion should fail.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 100, 1)
        delayed_add_event(tracer, "device1", 200, 2)
        delayed_add_event(tracer, "device1", 400, 4)

        start_time = datetime.now()
        with pytest.raises(
            AssertionError,
            match=self._expected_error_message_has_event(timeout=3),
        ):
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

    def test_assert_that_n_events_occurred_fails_when_less_than_n_events(
        self,
        tracer: TangoEventTracer,
    ) -> None:
        """The assertion fails if less than N events occurs.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 3)
        add_event(tracer, "device1", 5, 2)
        delayed_add_event(tracer, "device1", 100, 2)

        with pytest.raises(
            AssertionError,
            match=self._expected_error_message_has_event(
                detected_n_events=2, expected_n_events=3, timeout=3
            ),
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
        """The hasnt assertion verifies that no event occurs within timeout.

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

    # ##########################################################
    # Tests: assert hasnt change events occurred (n events)

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
    def _expected_error_message_hasnt_event(
        detected_n_events: int = 1,
        expected_n_events: int = 1,
        timeout: int | None = None,
    ) -> str:
        """Generate (a piece of) the err msg when hasnt event assertion fails.

        :param detected_n_events: The number of events detected.
        :param expected_n_events: The number of events expected. It is intended
            as "less than" expected_n_events, so it defaults to 1 (because
            most of the times you want no events).
        :param timeout: The timeout value. By default, it is not specified.
        :return: The regex pattern fragment to match the start of
            the error message.
        """
        res = rf"(?:Expected to NOT find {expected_n_events} event\(s\) "
        res += "matching the predicate "

        if timeout is not None:
            res += f"within {timeout} seconds"
        else:
            res += "in already existing events"
        res += f", but {detected_n_events} were found.)"

        return res

    def test_assert_that_n_events_havent_occurred_captures_n_events_within_timeout(  # pylint: disable=line-too-long # noqa: E501
        self,
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
            match=self._expected_error_message_hasnt_event(
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

    # ##########################################################
    # Tests: assert has/hasnt events with previous value

    def test_assert_that_event_occurred_handles_previous(
        self,
        tracer: TangoEventTracer,
    ) -> None:
        """The hasnt assertion handles correctly the previous value.

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

        with pytest.raises(
            AssertionError, match=self._expected_error_message_hasnt_event()
        ):
            assert_that(tracer).hasnt_change_event_occurred(
                device_name="device1",
                attribute_value=200,
                previous_value=120,
            )

        # ----------------------------------------------------
        # previous value is not caught when it does not exist

        with pytest.raises(
            AssertionError, match=self._expected_error_message_has_event()
        ):
            # When there is no previous value, it should fail
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
                previous_value=100,
            )

        with pytest.raises(
            AssertionError, match=self._expected_error_message_has_event()
        ):  # Again, when there is no previous value, it should fail
            assert_that(tracer).has_change_event_occurred(
                device_name="device2",
                previous_value=44,
            )

        with pytest.raises(
            AssertionError, match=self._expected_error_message_has_event()
        ):
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
        with pytest.raises(
            AssertionError, match=self._expected_error_message_has_event()
        ):
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

    # ##########################################################
    # Tests: assert has/hasnt events with custom matchers

    def test_has_event_custom_matcher_matches_event(
        self,
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

        with pytest.raises(
            AssertionError, match=self._expected_error_message_has_event()
        ):
            assert_that(tracer).described_as(
                "The custom matcher should match the event"
            ).has_change_event_occurred(
                device_name="device1",
                attribute_name="attrname",
                custom_matcher=lambda e: e.attribute_value > 150,
            )

    def test_hasnt_event_custom_matcher_matches_events(
        self,
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
            AssertionError, match=self._expected_error_message_hasnt_event()
        ):
            assert_that(tracer).described_as(
                "The custom matcher should match the event"
            ).hasnt_change_event_occurred(
                device_name="device1",
                attribute_name="attrname",
                custom_matcher=lambda e: e.attribute_value > 50,
            )
