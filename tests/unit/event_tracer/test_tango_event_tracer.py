"""Basic unit tests for :py:class:`TangoEventTracer`.

This set of tests covers the basic individual methods of the
:py:class:`TangoEventTracer` class. The tests are designed to trigger
each single method in isolation and check that it behaves as expected.

Those tests are not exhaustive, because they do not cover the actual
capability of subscribing to events from a Tango device and capturing
those events correctly. For that, see `test_tracer_subscribe_event.py`.
"""

# import logging
from datetime import datetime
from typing import Any, SupportsFloat

import pytest
import tango
from assertpy import assert_that

import ska_tango_testing.context
from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.tracer import TangoEventTracer

from .testing_utils import create_eventdata_mock
from .testing_utils.patch_context_devproxy import patch_context_device_proxy
from .testing_utils.populate_tracer import add_event, delayed_add_event


@pytest.mark.integration_tracer
class TestTangoEventTracer:
    """Unit tests for the `TangoEventTracer` class."""

    # ############################
    # Fixtures and helper methods

    @staticmethod
    def _check_tracer_one_event(
        tracer: TangoEventTracer, device: str, attribute: str, value: Any
    ) -> None:
        """Check that tracer contains exactly one event with expected fields.

        :param tracer: The `TangoEventTracer` instance.
        :param device: The device name.
        :param attribute: The attribute name.
        :param value: The current value.
        """
        assert_that(tracer.events).described_as(
            "Event callback should add an event"
        ).is_not_empty()
        assert_that(tracer.events).described_as(
            "Event callback should add exactly one event"
        ).is_length(1)
        assert_that(tracer.events[0]).described_as(
            "The added event should be a ReceivedEvent instance"
        ).is_instance_of(ReceivedEvent)
        assert_that(tracer.events[0].device_name).described_as(
            "The device name in the event should match"
        ).is_equal_to(device)
        assert_that(tracer.events[0].attribute_name).described_as(
            "The attribute name in the event should match"
        ).is_equal_to(attribute)
        assert_that(tracer.events[0].attribute_value).described_as(
            "The current value in the event should be correct"
        ).is_equal_to(value)

    # ########################################
    # Test cases: event_callback method

    def test_event_callback_adds_event(self, tracer: TangoEventTracer) -> None:
        """Test that the event callback adds an event to the tracer.

        :param tracer: The `TangoEventTracer` instance.
        """
        test_event = create_eventdata_mock(
            "test_device", "test_attribute", 123
        )

        # pylint: disable=protected-access
        tracer._add_event(ReceivedEvent(test_event))

        self._check_tracer_one_event(
            tracer, "test_device", "test_attribute", 123
        )

    # ########################################
    # Test cases: subscribe method

    @staticmethod
    def test_patching_device_proxy_work_as_expected() -> None:
        """The patch of the DeviceProxy class works as expected (meta-test).

        NOTE: currently, because of
        https://gitlab.com/tango-controls/pytango/-/issues/459
        ``tango.DeviceProxy`` internally is not used directly but instead
        it is used ``ska_tango_testing.context.DeviceProxy``. That's why we
        have also this patch instead of just patching ``tango.DeviceProxy``
        in unit tests that delegate to the tracer the creation of the
        instance of the device proxy.

        This meta-test checks that the patch works as expected.
        """
        with patch_context_device_proxy() as mock_proxy:
            ska_tango_testing.context.DeviceProxy("test_device")
            mock_proxy.assert_called_with("test_device")

    @staticmethod
    def test_a_subscription_to_a_change_event_happens(
        tracer: TangoEventTracer,
    ) -> None:
        """Subscribe to a device and attribute.

        :param tracer: The `TangoEventTracer` instance.
        """
        device_name, attribute_name = "test_device", "test_attribute"

        with patch_context_device_proxy() as mock_proxy:
            tracer.subscribe_event(device_name, attribute_name)

            mock_proxy.assert_called_with(device_name)
            calls = mock_proxy.return_value.subscribe_event.call_args_list
            assert_that(calls).described_as(
                "Expected exactly one call to subscribe_event"
            ).is_length(1)
            assert_that(calls[0].args).described_as(
                "Expected the first call to subscribe_event to have "
                "the correct arguments"
            ).is_length(3)
            assert_that(calls[0].args[0]).described_as(
                "Expected the first argument to be the attribute name"
            ).is_equal_to(attribute_name)
            assert_that(calls[0].args[1]).described_as(
                "Expected the second argument to be the event type"
            ).is_equal_to(tango.EventType.CHANGE_EVENT)

    @staticmethod
    def test_clear_events(tracer: TangoEventTracer) -> None:
        """Test clearing the events from the tracer.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5)
        add_event(tracer, "device2", 100, 5)
        assert len(tracer.events) == 2

        tracer.clear_events()

        assert_that(tracer.events).described_as(
            "Expected the events list to be empty after clearing"
        ).is_empty()

    # ########################################
    # Test cases: query_events method
    # (timeout mechanism)

    @staticmethod
    def test_query_events_no_timeout_with_matching_event(
        tracer: TangoEventTracer,
    ) -> None:
        """Test that an event is found when no timeout is specified.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5)  # Adds an event 5 seconds ago
        result = tracer.query_events(
            lambda e: e.has_device("device1"), timeout=None
        )
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1', "
            "but none was found."
        ).is_length(1)

    @staticmethod
    def test_query_events_no_timeout_without_matching_event(
        tracer: TangoEventTracer,
    ) -> None:
        """No event is found when there isn't and no timeout is specified.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5)

        start_time = datetime.now()
        result = tracer.query_events(
            lambda e: e.has_device("device2"), timeout=None
        )

        assert_that(result).described_as(
            "Found an unexpected event for 'device2' when none should exist."
        ).is_empty()
        assert_that(
            (datetime.now() - start_time).total_seconds()
        ).described_as(
            "Expected the query to return immediately when no event is found."
        ).is_less_than(
            0.2
        )

    @staticmethod
    def test_query_events_with_timeout_event_occurs(
        tracer: TangoEventTracer,
    ) -> None:
        """Test that an event is found when max_age is large enough.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 2)  # Event 2 seconds ago
        result = tracer.query_events(
            lambda e: e.has_device("device1") and e.reception_age() < 5,
        )
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1' within "
            "5 seconds, but none was found."
        ).is_length(1)

    @staticmethod
    def test_query_events_with_timeout_event_does_not_occur(
        tracer: TangoEventTracer,
    ) -> None:
        """Test that an event is not found when it is too old.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 10)  # Event 10 seconds ago

        # query_events with a maximum age of 5 seconds
        result = tracer.query_events(
            lambda e: e.has_device("device1") and e.reception_age() < 5,
        )

        assert_that(result).described_as(
            "An event for 'device1' was found, but it should have been "
            "outside the 5-second timeout."
        ).is_length(0)

    @staticmethod
    def test_query_events_with_delayed_event(tracer: TangoEventTracer) -> None:
        """Test a delayed event is captured by the tracer.

        :param tracer: The `TangoEventTracer` instance.
        """
        # At this point, no event for 'device1' exists
        delayed_add_event(
            tracer, "device1", 100, 3
        )  # Add an event after 3 seconds

        # query_events with a timeout of 5 seconds
        result = tracer.query_events(
            lambda e: e.has_device("device1"), timeout=5
        )

        # Assert that the event is found within the timeout
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1' "
            "within 5 seconds, but none was found."
        ).is_length(1)

    @staticmethod
    def test_query_events_accepts_floatable_timeout(
        tracer: TangoEventTracer,
    ) -> None:
        """Test that the query accepts a floatable timeout.

        :param tracer: The `TangoEventTracer` instance.
        """
        # At this point, no event for 'device1' exists
        delayed_add_event(
            tracer, "device1", 100, 3
        )  # Add an event after 3 seconds

        class TestTimeout(SupportsFloat):
            """A test timeout class that can be converted to a float."""

            # pylint: disable=too-few-public-methods

            def __float__(self) -> float:
                """Convert to a float.

                :return: The timeout as a float value.
                """
                return 5.0

        # query_events with a timeout of 5 seconds
        result = tracer.query_events(
            lambda e: e.has_device("device1"), timeout=TestTimeout()
        )

        # Assert that the event is found within the timeout
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1' "
            "within 5 seconds, but none was found."
        ).is_length(1)

    # ########################################
    # Test cases: query_events method
    # (correct predicate evaluation)

    @staticmethod
    def test_query_events_within_multiple_devices_returns_just_the_right_ones(
        tracer: TangoEventTracer,
    ) -> None:
        """Test that the query select exactly the required events.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 10)  # Event 10 seconds ago
        add_event(tracer, "device1", 100, 25)  # Event 25 seconds ago
        add_event(tracer, "device2", 100, 20)  # Event 20 seconds ago
        add_event(tracer, "device2", 100, 15)  # Event 15 seconds ago
        add_event(tracer, "device2", 100, 30)  # Event 30 seconds ago
        add_event(tracer, "device3", 100, 30)  # Event 30 seconds ago

        result = tracer.query_events(lambda e: e.has_device("device2"))

        assert_that(result).described_as(
            "Expected to find 3 events for 'device2'"
        ).is_length(3)

        assert_that(result[0].device_name).described_as(
            "Expected the device name to be 'device2'"
        ).is_equal_to("device2")
        assert_that(result[1].device_name).described_as(
            "Expected the device name to be 'device2'"
        ).is_equal_to("device2")
        assert_that(result[2].device_name).described_as(
            "Expected the device name to be 'device2'"
        ).is_equal_to("device2")

    @staticmethod
    def test_query_events_within_multiple_devices_all_wrong_returns_none(
        tracer: TangoEventTracer,
    ) -> None:
        """Test that the query select exactly the required events.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 10)  # Event 10 seconds ago
        add_event(tracer, "device1", 100, 25)  # Event 25 seconds ago
        add_event(tracer, "device2", 100, 20)  # Event 20 seconds ago
        add_event(tracer, "device2", 100, 15)  # Event 15 seconds ago
        add_event(tracer, "device2", 100, 30)  # Event 30 seconds ago
        add_event(tracer, "device3", 100, 30)  # Event 30 seconds ago

        result = tracer.query_events(lambda e: e.has_device("device4"))

        assert_that(result).described_as(
            "Expected to find 0 events for 'device4'"
        ).is_length(0)

    @staticmethod
    def test_query_awaits_expected_target_n_events(
        tracer: TangoEventTracer,
    ) -> None:
        """The query is able to wait for the expected number of events.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5)
        add_event(tracer, "device1", 100, 3)
        # add a delayed event that should be caught by the query
        delayed_add_event(tracer, "device1", 100, 2)
        # add a delayed event that is not necessary for the query
        delayed_add_event(tracer, "device1", 100, 3)

        result = tracer.query_events(
            lambda e: e.has_device("device1"), timeout=5, target_n_events=3
        )

        assert_that(result).described_as(
            "Expected to find 3 events for 'device1', instead found "
            f"{'more' if len(result) > 3 else 'less'} ({len(result)})."
        ).is_length(3)

    @staticmethod
    def test_query_case_insensitive_attr_name(
        tracer: TangoEventTracer,
    ) -> None:
        """The query is case-insensitive for attribute names.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 5, attr_name="TestAttr")
        result = tracer.query_events(lambda e: e.has_attribute("TestAttr"))

        assert_that(result).described_as(
            "Expected to find a matching event for 'TestAttr', "
            "but none was found."
        ).is_length(1)

    @staticmethod
    def test_recursive_query_call_does_not_cause_deadlock(
        tracer: TangoEventTracer,
    ) -> None:
        """A recursive query call does not cause a deadlock.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 0)
        add_event(tracer, "device2", 100, 0)

        def match_even_only_if_another_event_from_diff_device_exists(
            event: ReceivedEvent,
        ) -> bool:
            # This could cause issues
            other_event = tracer.query_events(
                lambda e: e.device_name != event.device_name
                and e.attribute_name == event.attribute_name
                and e.attribute_value == event.attribute_value
            )
            return len(other_event) > 0

        result = tracer.query_events(
            match_even_only_if_another_event_from_diff_device_exists
        )

        assert_that(result).described_as(
            "Expected to find 2 events, but found "
            f"{'more' if len(result) > 2 else 'less'} ({len(result)})."
        ).is_length(2)

    @staticmethod
    def test_recursive_events_retrieval_does_not_cause_deadlock(
        tracer: TangoEventTracer,
    ) -> None:
        """A recursive events retrieval does not cause a deadlock.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 0)
        add_event(tracer, "device2", 100, 0)

        def match_event_only_if_2_or_more_events_exist(
            _: ReceivedEvent,
        ) -> bool:
            return len(tracer.events) >= 2

        result = tracer.query_events(
            match_event_only_if_2_or_more_events_exist
        )

        assert_that(result).described_as(
            "Expected to find 2 events, but found "
            f"{'more' if len(result) > 2 else 'less'} ({len(result)})."
        ).is_length(2)
