"""Tools to create mock data for testing event tracer and logger."""

from typing import Any
from unittest.mock import MagicMock

import tango

from .dev_proxy_mock import create_dev_proxy_mock


def create_eventdata_mock(
    dev_name: str, attribute: str, value: Any, error: bool = False
) -> MagicMock:
    """Create a mock Tango event data object.

    :param dev_name: The device name.
    :param attribute: The attribute name.
    :param value: The current value.
    :param error: Whether the event is an error event, default is False.

    :return: A mock Tango event data object.
    """
    # Create a mock device
    mock_device = create_dev_proxy_mock(dev_name)

    # Create a mock attribute value
    mock_attr_value = MagicMock()
    mock_attr_value.value = value
    mock_attr_value.name = attribute

    # Create a mock event
    mock_event = MagicMock(spec=tango.EventData)
    mock_event.device = mock_device
    mock_event.attr_name = (
        f"tango://127.0.0.1:8080/{dev_name}/{attribute}#dbase=no"
    )
    mock_event.attr_value = mock_attr_value
    mock_event.err = error

    return mock_event
