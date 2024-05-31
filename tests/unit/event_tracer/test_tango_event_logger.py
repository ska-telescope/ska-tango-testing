"""Basic unit tests for :py:class:`TangoEventLogger`.

This set of tests covers the basic individual methods of the
:py:class:`TangoEventLogger` class. The tests are designed to trigger
each single method in isolation and check that it behaves as expected.

Those tests are not exhaustive, because they do not cover the actual
capability of subscribing to events from a Tango device and capturing
those events correctly. For that, see `test_logger_subscribe_event.py`.
"""

from unittest.mock import ANY, MagicMock, patch

import pytest
import tango
from assertpy import assert_that  # type: ignore

from ska_tango_testing.integration import log_events
from ska_tango_testing.integration.logger import (
    DEFAULT_LOG_ALL_EVENTS,
    DEFAULT_LOG_MESSAGE_BUILDER,
    TangoEventLogger,
)
from tests.unit.event_tracer.testing_utils import create_eventdata_mock
from tests.unit.event_tracer.testing_utils.dev_proxy_mock import (
    DeviceProxyMock,
)

LOGGING_PATH = "ska_tango_testing.integration.logger.logging"


class TestTangoEventLogger:
    """Basic unit tests for the :py:class:`TangoEventLogger`."""

    @pytest.fixture
    @staticmethod
    def logger() -> TangoEventLogger:
        """Return the :py:class:`TangoEventLogger` instance to test.

        :return: The :py:class:`TangoEventLogger`
        """
        return TangoEventLogger()

    @staticmethod
    @patch(LOGGING_PATH)
    def test_log_event_writes_the_right_message_on_logging_info(
        mock_logging: MagicMock,
        logger: TangoEventLogger,
    ) -> None:
        """log_event writes a message to the logger when called.

        :param mock_logging: The mock logging module.
        :param logger: The TangoEventLogger instance.
        """
        mock_event = create_eventdata_mock("test/device/1", "attribute1", 123)

        logger._log_event(  # pylint: disable=protected-access
            event_data=mock_event,
            filtering_rule=DEFAULT_LOG_ALL_EVENTS,
            message_builder=DEFAULT_LOG_MESSAGE_BUILDER,
        )

        # Assert that content of the last message
        # printed includes device name, attribute name and current value
        assert_that(mock_logging.info.call_args[0][0]).described_as(
            "The log_event method should write"
            " the right message to the logger."
        ).contains("test/device/1")
        assert_that(mock_logging.info.call_args[0][0]).described_as(
            "The log_event method should write"
            " the right message to the logger."
        ).contains("attribute1")
        assert_that(mock_logging.info.call_args[0][0]).described_as(
            "The log_event method should write"
            " the right message to the logger."
        ).contains(str(123))

    @staticmethod
    @patch(LOGGING_PATH)
    def test_log_event_does_not_write_message_when_filtering_rule_returns_false(  # pylint: disable=line-too-long # noqa: E501
        mock_logging: MagicMock,
        logger: TangoEventLogger,
    ) -> None:
        """log_event does not write a message when the filtering fail.

        :param mock_logging: The mock logging module.
        :param logger: The TangoEventLogger instance.
        """
        mock_event = create_eventdata_mock("test/device/1", "attribute1", 123)

        logger._log_event(  # pylint: disable=protected-access
            event_data=mock_event,
            filtering_rule=lambda e: False,
            message_builder=DEFAULT_LOG_MESSAGE_BUILDER,
        )

        # Assert that the logging method was not called
        assert_that(mock_logging.info.call_count).described_as(
            "The log_event method should not write a message to the logger."
        ).is_zero()

    @staticmethod
    @patch(LOGGING_PATH)
    def test_log_event_writes_custom_message_when_required(
        mock_logging: MagicMock,
        logger: TangoEventLogger,
    ) -> None:
        """log_event writes a custom message when required.

        :param mock_logging: The mock logging module.
        :param logger: The TangoEventLogger instance.
        """
        mock_event = create_eventdata_mock("test/device/1", "attribute1", 123)

        logger._log_event(  # pylint: disable=protected-access
            event_data=mock_event,
            filtering_rule=DEFAULT_LOG_ALL_EVENTS,
            message_builder=lambda e: "Custom message",
        )

        # Assert that the logging method was called with the expected message
        assert_that(mock_logging.info.call_args[0][0]).described_as(
            "The log_event method should write"
            " the custom message to the logger."
        ).is_equal_to("Custom message")

    @staticmethod
    @patch(LOGGING_PATH)
    def test_log_event_when_event_contains_error_writes_error_message(
        mock_logging: MagicMock,
        logger: TangoEventLogger,
    ) -> None:
        """log_event writes an error message when the event contains an error.

        :param mock_logging: The mock logging module.
        :param logger: The TangoEventLogger instance.
        """
        mock_event = create_eventdata_mock(
            "test/device/1",
            "attribute1",
            123,
            error=True,
        )

        logger._log_event(  # pylint: disable=protected-access
            event_data=mock_event,
            filtering_rule=DEFAULT_LOG_ALL_EVENTS,
            message_builder=DEFAULT_LOG_MESSAGE_BUILDER,
        )

        # Assert that content of the last message
        # printed includes device name, attribute name and current value
        assert_that(mock_logging.error.call_args[0][0]).described_as(
            "The log_event method should write"
            " the right message to the logger."
        ).contains("test/device/1")
        assert_that(mock_logging.error.call_args[0][0]).described_as(
            "The log_event method should write"
            " the right message to the logger."
        ).contains("attribute1")
        assert_that(mock_logging.error.call_args[0][0]).described_as(
            "The log_event method should write"
            " the right message to the logger."
        ).contains(str(123))

    @staticmethod
    def test_logger_subscribe_event(logger: TangoEventLogger) -> None:
        """The logger subscribes to a device without exceptions.

        :param logger: The TangoEventLogger instance.
        """
        device_name = "test_device"
        attribute_name = "test_attribute"

        with patch(
            "tango.DeviceProxy", new_callable=DeviceProxyMock
        ) as mock_proxy:
            logger.log_events_from_device(device_name, attribute_name)

            mock_proxy.assert_called_with(device_name)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name, tango.EventType.CHANGE_EVENT, ANY
            )

    # ########################################
    # Quick log utility function shortcut

    @staticmethod
    def test_log_utility_function_subscribe_event() -> None:
        """The quick logger utiliy subscribes to device without exceptions."""
        device_name = "test_device"
        attribute_name = "test_attribute"

        with patch(
            "tango.DeviceProxy", new_callable=DeviceProxyMock
        ) as mock_proxy:
            logger = log_events({device_name: [attribute_name]})

            mock_proxy.assert_called_with(device_name)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name, tango.EventType.CHANGE_EVENT, ANY
            )

            assert_that(logger).is_instance_of(TangoEventLogger)

    @staticmethod
    def test_log_utility_subscribe_multiple_attributes() -> None:
        """The quick logger utility subscribes to multiple attributes."""
        device_name_1 = "test_device_1"
        attribute_name_1 = "test_attribute_1"
        attribute_name_2 = "test_attribute_2"

        with patch(
            "tango.DeviceProxy", new_callable=DeviceProxyMock
        ) as mock_proxy:
            log_events(
                {
                    device_name_1: [attribute_name_1, attribute_name_2],
                }
            )

            mock_proxy.assert_called_with(device_name_1)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name_2, tango.EventType.CHANGE_EVENT, ANY
            )

    @staticmethod
    def test_log_utility_subscribe_multiple_devices() -> None:
        """The quick logger utility subscribes to multiple devices."""
        device_name_1 = "test_device_1"
        device_name_2 = "test_device_2"
        attribute_name_1 = "test_attribute_1"
        attribute_name_2 = "test_attribute_2"

        with patch(
            "tango.DeviceProxy", new_callable=DeviceProxyMock
        ) as mock_proxy:
            log_events(
                {
                    device_name_1: [attribute_name_1],
                    device_name_2: [attribute_name_2],
                }
            )
            mock_proxy.assert_called_with(device_name_2)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name_2, tango.EventType.CHANGE_EVENT, ANY
            )

    @staticmethod
    def test_log_utility_subscribe_passing_devproxy() -> None:
        """The quick logger utility subscribes using a device proxy."""
        device_name_1 = "test_device_1"
        attribute_name_1 = "test_attribute_1"

        with patch("tango.DeviceProxy", new_callable=DeviceProxyMock):

            device_1 = tango.DeviceProxy(device_name_1)

            log_events(
                {
                    device_1: [attribute_name_1],
                }
            )

            device_1.subscribe_event.assert_called_once()

            # get args of last call on the first device
            args, _ = device_1.subscribe_event.call_args
            assert_that(args[0]).is_equal_to(attribute_name_1)
            assert_that(args[1]).is_equal_to(tango.EventType.CHANGE_EVENT)
