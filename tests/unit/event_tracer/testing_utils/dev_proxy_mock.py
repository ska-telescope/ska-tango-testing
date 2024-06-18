"""A mock class for a Tango device proxy."""

from typing import Any
from unittest.mock import MagicMock

import tango


class DeviceProxyMock(MagicMock):
    """A mock class for a Tango device proxy.

    This class extends MagicMock to make an
    ``isinstance(instance, tango.DeviceProxy)`` check return True.
    """

    def __instancecheck__(self, instance: Any) -> bool:
        """Check if an instance is a Tango device proxy.

        :param instance: The instance to check.

        :returns: True if the has basic Tango device proxy features.
        """
        # check if this instance has dev_name() and subscribe_event() methods
        return all(
            hasattr(instance, method)
            for method in ["dev_name", "subscribe_event"]
        )


def create_dev_proxy_mock(dev_name: str) -> DeviceProxyMock:
    """Create a mock Tango device proxy.

    :param dev_name: The device name.

    :return: A mock Tango device proxy.
    """
    mock_dev_proxy = DeviceProxyMock(spec=tango.DeviceProxy)
    mock_dev_proxy.dev_name.return_value = dev_name

    return mock_dev_proxy
