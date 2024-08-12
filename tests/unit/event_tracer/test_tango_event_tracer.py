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
from typing import Any
from unittest.mock import patch

import pytest
import tango
from assertpy import assert_that

import ska_tango_testing.context
from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.tracer import TangoEventTracer
from tests.unit.event_tracer.testing_utils import create_eventdata_mock
from tests.unit.event_tracer.testing_utils.dev_proxy_mock import (
    DeviceProxyMock,
)
from tests.unit.event_tracer.testing_utils.dummy_state_enum import (
    DummyStateEnum,
)
from tests.unit.event_tracer.testing_utils.patch_context_devproxy import (
    patch_context_device_proxy,
)
from tests.unit.event_tracer.testing_utils.populate_tracer import (
    add_event,
    delayed_add_event,
)


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
        test_event = create_eventdata_mock(
            "test_device", "test_attribute", 123, error=True
        )

        tracer._event_callback(test_event)  # pylint: disable=protected-access

        assert_that(tracer.events).described_as(
            "Event callback should ignore events with errors"
        ).is_empty()

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
    def test_subscribe_event(tracer: TangoEventTracer) -> None:
        """Subscribe to a device and attribute.

        :param tracer: The `TangoEventTracer` instance.
        """
        device_name, attribute_name = "test_device", "test_attribute"

        with patch_context_device_proxy() as mock_proxy:
            tracer.subscribe_event(device_name, attribute_name)

            mock_proxy.assert_called_with(device_name)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                tracer._event_callback,  # pylint: disable=protected-access
            )

    @staticmethod
    def test_subscribe_event_passing_instance(
        tracer: TangoEventTracer,
    ) -> None:
        """Subscribe to a device and attribute passing a device instance.

        :param tracer: The `TangoEventTracer` instance.
        """
        device_name, attribute_name = "test_device", "test_attribute"

        with patch("tango.DeviceProxy", new_callable=DeviceProxyMock):
            device_proxy = tango.DeviceProxy(device_name)
            tracer.subscribe_event(device_proxy, attribute_name)

            device_proxy.subscribe_event.assert_called_with(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                tracer._event_callback,  # pylint: disable=protected-access
            )

    @staticmethod
    def test_subscribe_event_passing_dev_factory(
        tracer: TangoEventTracer,
    ) -> None:
        """Subscribe to a device and attribute passing a device factory.

        :param tracer: The `TangoEventTracer` instance.
        """
        device_name, attribute_name = "test_device", "test_attribute"

        def device_factory(device_name: str) -> tango.DeviceProxy:
            """Create a device proxy.

            :param device_name: The device name.

            :return: A device proxy.
            """
            return tango.DeviceProxy(device_name)

        with patch(
            "tango.DeviceProxy", new_callable=DeviceProxyMock
        ) as mock_proxy:
            tracer.subscribe_event(
                device_name, attribute_name, dev_factory=device_factory
            )

            mock_proxy.assert_called_with(device_name)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                tracer._event_callback,  # pylint: disable=protected-access
            )

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
        )  # Add an event after 5 seconds

        # query_events with a timeout of 10 seconds
        result = tracer.query_events(
            lambda e: e.has_device("device1"), timeout=5
        )

        # Assert that the event is found within the timeout
        assert_that(result).described_as(
            "Expected to find a matching event for 'device1' "
            "within 10 seconds, but none was found."
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

    # ########################################
    # Test cases: typed events
    # (some special events are typed with an Enum)

    @staticmethod
    def test_add_typed_event() -> None:
        """A typed event is correctly created and added to the tracer."""
        tracer = TangoEventTracer({"state": DummyStateEnum})
        test_event = create_eventdata_mock(
            "test_device", "state", DummyStateEnum.STATE_2
        )

        tracer._event_callback(test_event)  # pylint: disable=protected-access

        assert_that(tracer.events).described_as(
            "Event callback should add an event"
        ).is_length(1)
        assert_that(tracer.events[0]).described_as(
            "First event should be a TypedEvent instance"
        ).is_instance_of(ReceivedEvent)
        assert_that(tracer.events[0].attribute_value).described_as(
            "The attribute value should be a DummyStateEnum instance"
        ).is_instance_of(DummyStateEnum)
        assert_that(tracer.events[0].attribute_value).described_as(
            "The attribute value should be DummyStateEnum.STATE2"
        ).is_equal_to(DummyStateEnum.STATE_2)
        assert_that(tracer.events[0].attribute_value_as_str).described_as(
            "The attribute value as string should be 'STATE2'"
        ).is_equal_to("DummyStateEnum.STATE_2")
