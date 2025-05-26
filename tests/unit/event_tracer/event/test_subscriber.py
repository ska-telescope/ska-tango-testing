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
from ska_tango_testing.integration.event.subscriber import TangoSubscriber
from ska_tango_testing.integration.event.typed import TypedEvent

from ..testing_utils import DeviceProxyMock, create_eventdata_mock
from ..testing_utils.dev_proxy_mock import create_dev_proxy_mock
from ..testing_utils.dummy_state_enum import DummyStateEnum
from ..testing_utils.patch_context_devproxy import patch_context_device_proxy


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
        ).described_as("Subscription ID should be stored").contains(
            "test_attr"
        )
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

    # ------------------------------------------------------------------------
    # Double subscription testing

    @staticmethod
    def test_double_subscriptions_are_not_repeated() -> None:
        """Double subscriptions are not repeated."""
        with patch_context_device_proxy() as mock_proxy:
            mock_proxy.return_value.subscribe_event.return_value = 1234
            mock_proxy.dev_name.return_value = "test/device/1"
            subscriber = TangoSubscriber()
            callback = MagicMock()

            subscriber.subscribe_event("test/device/1", "test_attr", callback)
            subscriber.subscribe_event("test/device/1", "test_attr", callback)

        assert_that(
            mock_proxy.return_value.subscribe_event.call_args_list
        ).described_as("subscribe_event should be called only once").is_length(
            1
        )

    @staticmethod
    def test_double_subscriptions_check_is_case_insensitive() -> None:
        """Double subscriptions are case insensitive."""
        with patch_context_device_proxy() as mock_proxy:
            mock_proxy.return_value.subscribe_event.return_value = 1234
            mock_proxy.dev_name.return_value = "test/device/1"
            subscriber = TangoSubscriber()
            callback = MagicMock()

            subscriber.subscribe_event("test/device/1", "test_attr", callback)
            subscriber.subscribe_event("TEST/DEVICE/1", "TEST_ATTR", callback)

        assert_that(
            mock_proxy.return_value.subscribe_event.call_args_list
        ).described_as("subscribe_event should be called only once").is_length(
            1
        )

    @staticmethod
    def test_double_subscr_with_device_proxy_are_not_repeated() -> None:
        """Subscriptions with proxies to the same device are not repeated."""
        subscriber = TangoSubscriber()
        # create two device proxies to the same device
        # (-> the subscription should be the same)
        device_proxy_a = create_dev_proxy_mock("test/device/1")
        device_proxy_b = create_dev_proxy_mock("test/device/1")
        subscribe_event = MagicMock(side_effect=[1234, 1234])
        device_proxy_a.subscribe_event = subscribe_event
        device_proxy_b.subscribe_event = subscribe_event
        callback = MagicMock()

        # subscribe to the same attribute with two different proxies
        subscriber.subscribe_event(device_proxy_a, "test_attr", callback)
        subscriber.subscribe_event(device_proxy_b, "test_attr", callback)

        assert_that(subscribe_event.call_args_list).described_as(
            "subscribe_event should be called only once"
        ).is_length(1)

    @staticmethod
    def test_double_subscr_with_name_and_device_are_not_repeated() -> None:
        """Subscriptions with name and device proxy are not repeated."""
        with patch_context_device_proxy() as mock_proxy:
            subscribe_event = MagicMock(side_effect=[1234, 1234])
            mock_proxy.return_value.subscribe_event = subscribe_event
            mock_proxy.return_value.dev_name.return_value = "test/device/1"
            device_proxy = create_dev_proxy_mock("test/device/1")
            device_proxy.subscribe_event = subscribe_event
            subscriber = TangoSubscriber()
            callback = MagicMock()

            # subscribe to the same attribute with a name and a proxy
            subscriber.subscribe_event("test/device/1", "test_attr", callback)
            subscriber.subscribe_event(device_proxy, "test_attr", callback)

        assert_that(subscribe_event.call_args_list).described_as(
            "subscribe_event should be called only once"
        ).is_length(1)

    @staticmethod
    def test_subscriptions_are_possible_from_different_attributes() -> None:
        """Double subscriptions are possible from different attributes."""
        with patch_context_device_proxy() as mock_proxy:
            mock_proxy.return_value.subscribe_event.return_value = 1234
            subscriber = TangoSubscriber()
            callback = MagicMock()

            subscriber.subscribe_event("test/device/1", "test_attr1", callback)
            subscriber.subscribe_event("test/device/1", "test_attr1", callback)
            subscriber.subscribe_event("test/device/1", "test_attr2", callback)
            subscriber.subscribe_event("test/device/1", "test_attr2", callback)

        assert_that(
            mock_proxy.return_value.subscribe_event.call_args_list
        ).described_as("subscribe_event should be called twice").is_length(2)
