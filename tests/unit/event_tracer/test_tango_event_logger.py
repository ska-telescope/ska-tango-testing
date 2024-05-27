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

from ska_tango_testing.integration.logger import (
    DEFAULT_LOG_ALL_EVENTS,
    DEFAULT_LOG_MESSAGE_BUILDER,
    TangoEventLogger,
)
from tests.unit.event_tracer.testing_utils import create_mock_eventdata

LOGGING_PATH = "ska_tango_testing.integration.logger.logging"


@pytest.mark.Tracer
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
        mock_event = create_mock_eventdata("test/device/1", "attribute1", 123)

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
        mock_event = create_mock_eventdata("test/device/1", "attribute1", 123)

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
        mock_event = create_mock_eventdata("test/device/1", "attribute1", 123)

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
        mock_event = create_mock_eventdata(
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

        with patch("tango.DeviceProxy") as mock_proxy:
            logger.log_events_from_device(device_name, attribute_name)

            mock_proxy.assert_called_with(device_name)
            mock_proxy.return_value.subscribe_event.assert_called_with(
                attribute_name, tango.EventType.CHANGE_EVENT, ANY
            )
