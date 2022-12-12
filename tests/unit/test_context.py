"""This module tests the ska_tango_testing version."""

import unittest
from typing import Optional

import pytest
import tango.server

from ska_tango_testing.context import (
    DeviceProxy,
    ThreadedTestTangoContextManager,
)


class SoloDevice(tango.server.Device):
    """A basic device for use in testing."""

    Value = tango.server.device_property(dtype=int)

    def init_device(self) -> None:
        """Initialise this device."""
        self.get_device_properties()

    @tango.server.attribute(dtype=int)
    def value(self) -> int:
        """
        Return the value of the "value" attribute.

        :return: the value of the "value" attribute.
        """
        return self.Value


class TwinDevice(tango.server.Device):
    """A device that interacts with another, for use in testing."""

    Value = tango.server.device_property(dtype=int)
    Twin = tango.server.device_property(dtype=str)

    def init_device(self) -> None:
        """Initialise this device."""
        self.get_device_properties()
        self._twin_value: Optional[int] = None

    @tango.server.attribute(dtype=int)
    def value(self) -> int:
        """
        Return the value of the "value" attribute.

        :return: the value of the "value" attribute.
        """
        return self.Value

    @tango.server.attribute(dtype=int)
    def twin_value(self) -> int:
        """
        Return the value of the "value" attribute.

        :return: the value of the "value" attribute.
        """
        if self._twin_value is None:
            twin = DeviceProxy(self.Twin)
            # pylint: disable-next=attribute-defined-outside-init
            self._twin_value = twin.value
        assert self._twin_value is not None  # for the type checker
        return self._twin_value


class TestThreadedTestTangoContextManager:
    """Container class for tests of the ThreadedTestTangoContextManager."""

    @pytest.mark.forked  # pylint: disable-next=no-self-use
    def test_context_manager_with_a_single_device(self) -> None:
        """Test a context manager with a single device."""
        context_manager = ThreadedTestTangoContextManager()
        context_manager.add_device("foo/bar/1", SoloDevice, Value=1)

        with context_manager as context:
            device = context.get_device("foo/bar/1")
            assert device.value == 1

    @pytest.mark.forked  # pylint: disable-next=no-self-use
    def test_context_manager_with_multiple_devices(self) -> None:
        """Test a context manager with multiple devices that communicate."""
        context_manager = ThreadedTestTangoContextManager()
        context_manager.add_device(
            "foo/bar/1", TwinDevice, Value=1, Twin="foo/bar/2"
        )
        context_manager.add_device(
            "foo/bar/2", TwinDevice, Value=2, Twin="foo/bar/1"
        )

        with context_manager as context:
            device_1 = context.get_device("foo/bar/1")
            device_2 = context.get_device("foo/bar/2")

            assert device_1.value == 1
            assert device_2.value == 2

            assert device_1.twin_value == 2
            assert device_2.twin_value == 1

    @pytest.mark.forked  # pylint: disable-next=no-self-use
    def test_context_manager_with_device_and_mock(self) -> None:
        """Test a context manager with a device and a mock."""
        context_manager = ThreadedTestTangoContextManager()
        context_manager.add_device(
            "foo/bar/1", TwinDevice, Value=1, Twin="foo/bar/2"
        )

        mock = unittest.mock.Mock()
        mock.value = 2

        context_manager.add_mock_device("foo/bar/2", mock)

        with context_manager as context:
            device_1 = context.get_device("foo/bar/1")
            device_2 = context.get_device("foo/bar/2")

            type(mock).twin_value = unittest.mock.PropertyMock(
                side_effect=lambda: device_1.value
            )

            assert device_1.value == 1
            assert device_2.value == 2

            assert device_1.twin_value == 2
            assert device_2.twin_value == 1
