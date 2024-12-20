"""Unit tests for :py:class:`TangoSubscriber`.

This set of tests covers the basic functionality of the
:py:class:`TangoSubscriber` class, focusing on thread safety
and correct event handling.
"""

from unittest.mock import MagicMock

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.subscription_manager import TangoSubscriber
from tests.unit.event_tracer.testing_utils.patch_context_devproxy import (
    patch_context_device_proxy,
)

from .testing_utils import create_eventdata_mock


@pytest.mark.integration_tracer
class TestTangoSubscriber:
    """Unit tests for the TangoSubscriber class."""

    @staticmethod
    def test_subscribe_event_adds_subscription() -> None:
        """Test that subscribing to an event adds a subscription."""
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

    @staticmethod
    def test_unsubscribe_all_removes_all_subscriptions() -> None:
        """Test that unsubscribing from all removes all subscriptions."""
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

    @staticmethod
    def test_callback_is_called_with_received_event() -> None:
        """Test that the callback is called with a ReceivedEvent."""
        subscriber = TangoSubscriber()
        callback = MagicMock()
        event_data = create_eventdata_mock("test/device/1", "test_attr", 42)

        # pylint: disable=protected-access
        subscriber._call_callback(event_data, callback)

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
