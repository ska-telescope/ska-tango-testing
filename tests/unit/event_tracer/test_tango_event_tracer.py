"""Basic unit tests for :py:class:`TangoEventTracer`.

This set of tests covers the basic individual methods of the
:py:class:`TangoEventTracer` class. The tests are designed to trigger
each single method in isolation and check that it behaves as expected.

Those tests are not exhaustive, because they do not cover the actual
capability of subscribing to events from a Tango device and capturing
those events correctly. For that, see `test_tracer_subscribe_event.py`.
"""

# import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
import tango
from assertpy import assert_that  # type: ignore

from ska_tango_testing.integration.received_event import ReceivedEvent
from ska_tango_testing.integration.tango_event_tracer import TangoEventTracer
from tests.unit.event_tracer.testing_utils import create_mock_eventdata


@pytest.mark.Tracer
class TestTangoEventTracer:
    """Unit tests for the `TangoEventTracer` class."""

    # ############################
    # Fixtures and helper methods

    @pytest.fixture
    @staticmethod
    def tracer() -> TangoEventTracer:
        """Create a `TangoEventTracer` instance for testing.

        :return: a `TangoEventTracer` instance.
        """
        return TangoEventTracer()

    @staticmethod
    def add_event(
        tracer: TangoEventTracer,
        device: str,
        value: Any,
        seconds_ago: float = 0,
    ) -> None:
        """Add an event to the tracer.

        :param tracer: The `TangoEventTracer` instance.
        :param device: The device name.
        :param value: The current value.
        :param seconds_ago: How many seconds ago the event occurred,
            default is 0.
        """
        test_event = ReceivedEvent(
            create_mock_eventdata(device, "test_attribute", value)
        )

        # Set the timestamp to the past (if needed)
        if seconds_ago > 0:
            test_event.reception_time = datetime.now() - timedelta(
                seconds=seconds_ago
            )

        tracer._add_event(test_event)  # pylint: disable=protected-access

    def delayed_add_event(
        self, tracer: TangoEventTracer, device: str, value: Any, delay: float
    ) -> None:
        """Add an event to the tracer after a delay.

        :param tracer: The `TangoEventTracer` instance.
        :param device: The device name.
        :param value: The current value.
        :param delay: The delay in seconds.
        """

        def _add_event() -> None:
            """Add an event after a delay."""
            time.sleep(delay)
            self.add_event(tracer, device, value)

        threading.Thread(target=_add_event).start()

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
        test_event = create_mock_eventdata(
            "test_device", "test_attribute", 123
        )

        tracer._event_callback(test_event)  # pylint: disable=protected-access

        self._check_tracer_one_event(
            tracer, "test_device", "test_attribute", 123  # , 100
        )

    @staticmethod
    def test_event_callback_when_error_ignore_event(
        tracer: TangoEventTracer,
    ) -> None:
        """Test that the event callback ignores events with errors.

        :param tracer: The `TangoEventTracer` instance.
        """
        test_event = create_mock_eventdata(
            "test_device", "test_attribute", 123, error=True
        )

        tracer._event_callback(test_event)  # pylint: disable=protected-access

        assert_that(tracer.events).described_as(
            "Event callback should ignore events with errors"
        ).is_empty()

    # ########################################
    # Test cases: subscribe method

    @staticmethod
    def test_subscribe_event(tracer: TangoEventTracer) -> None:
        """Test subscribing to a device and attribute.

        :param tracer: The `TangoEventTracer` instance.
        """
        device_name = "test_device"
        attribute_name = "test_attribute"

        with patch("tango.DeviceProxy") as mock_proxy:
            tracer.subscribe_event(device_name, attribute_name)

            mock_proxy.assert_called_with(device_name)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                tracer._event_callback,  # pylint: disable=protected-access
            )

    @staticmethod
    def test_subscribe_event_passing_dev_factory(
        tracer: TangoEventTracer,
    ) -> None:
        """Test subscribing to a device and attribute passing a device factory.

        :param tracer: The `TangoEventTracer` instance.
        """
        device_name = "test_device"
        attribute_name = "test_attribute"

        def device_factory(device_name: str) -> tango.DeviceProxy:
            """Create a device proxy.

            :param device_name: The device name.

            :return: A device proxy.
            """
            return tango.DeviceProxy(device_name)

        with patch("tango.DeviceProxy") as mock_proxy:
            tracer.subscribe_event(
                device_name, attribute_name, dev_factory=device_factory
            )

            mock_proxy.assert_called_with(device_name)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                tracer._event_callback,  # pylint: disable=protected-access
            )

    def test_clear_events(self, tracer: TangoEventTracer) -> None:
        """Test clearing the events from the tracer.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(tracer, "device1", 100, 5)
        self.add_event(tracer, "device2", 100, 5)
        assert len(tracer.events) == 2

        tracer.clear_events()

        assert_that(tracer.events).described_as(
            "Expected the events list to be empty after clearing"
        ).is_empty()

    # ########################################
    # Test cases: query_events method
    # (timeout mechanism)

    def test_query_events_no_timeout_with_matching_event(
        self, tracer: TangoEventTracer
    ) -> None:
        """Test that an event is found when no timeout is specified.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(
            tracer, "device1", 100, 5
        )  # Adds an event 5 seconds ago
        result = tracer.query_events(
            lambda e: e.device_name == "device1", timeout=None
        )
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1', "
            "but none was found."
        ).is_length(1)

    # NOTE: this test cannot happen! Infinite wait...
    # def test_query_events_no_timeout_without_matching_event(
    #    self, tracer: TangoEventTracer):
    #     self.add_event(tracer, "device1", 100, 5)
    #     result = tracer.query_events(
    #           lambda e: e.device_name == "device2", None)
    #     assert_that(result).described_as(
    #         "Found an unexpected event for 'device2' when none should exist."
    #     ).is_false()
    def test_query_events_no_timeout_without_matching_event(
        self, tracer: TangoEventTracer
    ) -> None:
        """No event is found when there isn't and no timeout is specified.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(tracer, "device1", 100, 5)
        result = tracer.query_events(
            lambda e: e.device_name == "device2", timeout=None
        )
        assert_that(result).described_as(
            "Found an unexpected event for 'device2' when none should exist."
        ).is_empty()

    def test_query_events_with_timeout_event_occurs(
        self, tracer: TangoEventTracer
    ) -> None:
        """Test that an event is found when max_age is large enough.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(tracer, "device1", 100, 2)  # Event 2 seconds ago
        result = tracer.query_events(
            lambda e: e.device_name == "device1" and e.reception_age() < 5,
        )
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1' within "
            "5 seconds, but none was found."
        ).is_length(1)

    def test_query_events_with_timeout_event_does_not_occur(
        self, tracer: TangoEventTracer
    ) -> None:
        """Test that an event is not found when it is too old.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(tracer, "device1", 100, 10)  # Event 10 seconds ago

        # query_events with a maximum age of 5 seconds
        result = tracer.query_events(
            lambda e: e.device_name == "device1" and e.reception_age() < 5,
        )

        assert_that(result).described_as(
            "An event for 'device1' was found, but it should have been "
            "outside the 5-second timeout."
        ).is_length(0)

    def test_query_events_with_delayed_event(
        self, tracer: TangoEventTracer
    ) -> None:
        """Test a delayed event is captured by the tracer.

        :param tracer: The `TangoEventTracer` instance.
        """
        # At this point, no event for 'device1' exists
        self.delayed_add_event(
            tracer, "device1", 100, 3
        )  # Add an event after 5 seconds

        # query_events with a timeout of 10 seconds
        result = tracer.query_events(
            lambda e: e.device_name == "device1", timeout=5
        )

        # Assert that the event is found within the timeout
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1' "
            "within 10 seconds, but none was found."
        ).is_length(1)

    # ########################################
    # Test cases: query_events method
    # (correct predicate evaluation)

    def test_query_events_within_multiple_devices_returns_just_the_right_ones(
        self, tracer: TangoEventTracer
    ) -> None:
        """Test that the query select exactly the required events.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(tracer, "device1", 100, 10)  # Event 10 seconds ago
        self.add_event(tracer, "device1", 100, 25)  # Event 25 seconds ago
        self.add_event(tracer, "device2", 100, 20)  # Event 20 seconds ago
        self.add_event(tracer, "device2", 100, 15)  # Event 15 seconds ago
        self.add_event(tracer, "device2", 100, 30)  # Event 30 seconds ago
        self.add_event(tracer, "device3", 100, 30)  # Event 30 seconds ago

        result = tracer.query_events(lambda e: e.device_name == "device2")

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

    def test_query_events_within_multiple_devices_all_wrong_returns_none(
        self, tracer: TangoEventTracer
    ) -> None:
        """Test that the query select exactly the required events.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(tracer, "device1", 100, 10)  # Event 10 seconds ago
        self.add_event(tracer, "device1", 100, 25)  # Event 25 seconds ago
        self.add_event(tracer, "device2", 100, 20)  # Event 20 seconds ago
        self.add_event(tracer, "device2", 100, 15)  # Event 15 seconds ago
        self.add_event(tracer, "device2", 100, 30)  # Event 30 seconds ago
        self.add_event(tracer, "device3", 100, 30)  # Event 30 seconds ago

        result = tracer.query_events(lambda e: e.device_name == "device4")

        assert_that(result).described_as(
            "Expected to find 0 events for 'device4'"
        ).is_length(0)

    def test_query_awaits_expected_target_n_events(
        self, tracer: TangoEventTracer
    ) -> None:
        """The query is able to wait for the expected number of events.

        :param tracer: The `TangoEventTracer` instance.
        """
        self.add_event(tracer, "device1", 100, 5)
        self.add_event(tracer, "device1", 100, 3)
        # add a delayed event that should be caught by the query
        self.delayed_add_event(tracer, "device1", 100, 2)
        # add a delayed event that is not necessary for the query
        self.delayed_add_event(tracer, "device1", 100, 3)

        result = tracer.query_events(
            lambda e: e.device_name == "device1", timeout=5, target_n_events=3
        )

        assert_that(result).described_as(
            "Expected to find 3 events for 'device1', instead found "
            f"{'more' if len(result) > 3 else 'less'} ({len(result)})."
        ).is_length(3)
