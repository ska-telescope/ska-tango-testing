"""Module for creating dummy ReceivedEvent` objects for testing purposes."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

from ska_tango_testing.integration.event import ReceivedEvent


def create_dummy_event(
    device_name: str,
    attribute_name: str,
    attribute_value: Any,
    seconds_ago: float = 0,
) -> MagicMock:
    """Create a dummy :py:class:`ReceivedEvent` with the specified params.

    :param device_name: The device name.
    :param attribute_name: The attribute name.
    :param attribute_value: The attribute value.
    :param seconds_ago: The time in seconds since the event was received.

    :return: A dummy :py:class:`ReceivedEvent`.
    """
    event = MagicMock(spec=ReceivedEvent)
    event.device_name = device_name
    event.attribute_name = attribute_name
    event.attribute_value = attribute_value
    event.reception_time = datetime.now() - timedelta(seconds=seconds_ago)
    event.has_device = (
        lambda target_device_name: event.device_name == target_device_name
    )
    event.has_attribute = (
        lambda target_attribute_name: event.attribute_name
        == target_attribute_name
    )
    return event
