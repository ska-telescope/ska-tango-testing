"""Unit tests for :py:class:`TangoSubscriber`.

This set of tests covers the basic functionality of the
:py:class:`TangoSubscriber` class, focusing on thread safety
and correct event handling.
"""

from unittest.mock import MagicMock, patch

import pytest
import tango
from assertpy import assert_that

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.subscriber import TangoSubscriber
from ska_tango_testing.integration.typed_event import TypedEvent
from tests.unit.event_tracer.testing_utils.patch_context_devproxy import (
    patch_context_device_proxy,
)

from .testing_utils import DeviceProxyMock, create_eventdata_mock
from .testing_utils.dummy_state_enum import DummyStateEnum


@pytest.mark.integration_tracer
class TestTangoSubscriber:
    """Unit tests for the TangoSubscriber class."""

    # ------------------------------------------------------------------------
    # Subscription management testing

    @staticmethod
    def test_subscribe_event_adds_subscription_and_subscribes() -> None:
        """Subscription adds a subscription and subscribes to the event."""
        with patch_context_device_proxy() as mock_proxy:
            mock_proxy.return_value.subscribe_event.return_value = 1234
            subscriber = TangoSubscriber()
            callback = MagicMock()

            subscriber.subscribe_event("test/device/1", "test_attr", callback)

        # pylint: disable=protected-access
        assert_that(subscriber._subscription_ids).described_as(
            "Subscription should be added"
        ).is_not_empty()
        assert_that(
            # pylint: disable=protected-access
            subscriber._subscription_ids[mock_proxy.return_value]
        ).described_as("Subscription ID should be stored").contains(1234)
        assert_that(
            mock_proxy.return_value.subscribe_event.call_args_list
        ).described_as("subscribe_event should be called").is_length(1)
        assert_that(
            mock_proxy.return_value.subscribe_event.call_args_list[0][0][0]
        ).described_as(
            "subscribe_event should be called with the correct attribute name"
        ).is_equal_to(
            "test_attr"
        )

    @staticmethod
    def test_subscribe_event_passing_instance() -> None:
        """Subscription works also passing a device instance."""
        device_name, attribute_name = "test_device", "test_attr"
        with patch("tango.DeviceProxy", new_callable=DeviceProxyMock):
            device_proxy = tango.DeviceProxy(device_name)
            subscriber = TangoSubscriber()
            callback = MagicMock()

            subscriber.subscribe_event(device_proxy, attribute_name, callback)

        assert_that(device_proxy.subscribe_event.call_args_list).described_as(
            "subscribe_event should be called"
        ).is_length(1)
        assert_that(
            device_proxy.subscribe_event.call_args_list[0][0][0]
        ).described_as(
            "subscribe_event should be called with the correct attribute name"
        ).is_equal_to(
            attribute_name
        )

    @staticmethod
    def test_unsubscribe_all_removes_all_subscriptions() -> None:
        """Unsubscribe method removes all subscriptions."""
        with patch_context_device_proxy() as mock_proxy:
            mock_proxy.return_value.subscribe_event.return_value = 1234
            subscriber = TangoSubscriber()
            subscriber.subscribe_event(
                "test/device/1", "test_attr", MagicMock()
            )

            subscriber.unsubscribe_all()

        # pylint: disable=protected-access
        assert_that(subscriber._subscription_ids).described_as(
            "All subscriptions should be removed"
        ).is_empty()
        assert_that(
            mock_proxy.return_value.unsubscribe_event.call_args_list
        ).described_as("unsubscribe_event should be called").is_length(1)
        assert_that(
            mock_proxy.return_value.unsubscribe_event.call_args_list[0][0][0]
        ).described_as(
            "unsubscribe_event should be called with "
            "the correct subscription ID"
        ).is_equal_to(
            1234
        )

    # ------------------------------------------------------------------------
    # Callback and events generation testing

    @staticmethod
    def test_callback_is_called_with_received_event() -> None:
        """Passed callback function is called with ReceivedEvent instance."""
        subscriber = TangoSubscriber()
        callback = MagicMock()
        event_data = create_eventdata_mock("test/device/1", "test_attr", 42)

        # pylint: disable=protected-access
        subscriber._on_receive_tango_event(event_data, callback)

        assert_that(callback.call_args_list).described_as(
            "Callback should be called once"
        ).is_length(1)

        received_event = callback.call_args_list[0][0][0]
        assert_that(received_event).described_as(
            "Callback should be called with a ReceivedEvent"
        ).is_instance_of(ReceivedEvent)
        assert_that(received_event.device_name).described_as(
            "ReceivedEvent should have correct device name"
        ).is_equal_to("test/device/1")
        assert_that(received_event.attribute_name).described_as(
            "ReceivedEvent should have correct attribute name"
        ).is_equal_to("test_attr")
        assert_that(received_event.attribute_value).described_as(
            "ReceivedEvent should have correct value"
        ).is_equal_to(42)

    @staticmethod
    def test_callback_receives_typed_event_if_mapping_contains_attr() -> None:
        """Callback is called with a typed event when attribute is mapped."""
        subscriber = TangoSubscriber({"test_attr": DummyStateEnum})
        callback = MagicMock()
        event_data = create_eventdata_mock(
            "test/device/1", "test_attr", DummyStateEnum.STATE_2
        )

        # pylint: disable=protected-access
        subscriber._on_receive_tango_event(event_data, callback)

        assert_that(callback.call_args_list).described_as(
            "Callback should be called once"
        ).is_length(1)

        received_event = callback.call_args_list[0][0][0]
        assert_that(received_event).described_as(
            "Callback should be called with a ReceivedEvent"
        ).is_instance_of(TypedEvent)
        assert_that(received_event.device_name).described_as(
            "ReceivedEvent should have correct device name"
        ).is_equal_to("test/device/1")
        assert_that(received_event.attribute_name).described_as(
            "ReceivedEvent should have correct attribute name"
        ).is_equal_to("test_attr")
        assert_that(received_event.attribute_value).described_as(
            "ReceivedEvent should have correct value"
        ).is_equal_to(DummyStateEnum.STATE_2)
