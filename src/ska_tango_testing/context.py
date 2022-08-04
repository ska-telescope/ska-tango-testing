"""This module provides support for tango testing contexts."""

from types import TracebackType
from typing import Any, Dict, List, Optional, Type, Union

import tango
import tango.server
import tango.test_context
from typing_extensions import Literal, Protocol


# TODO: Remove _DeviceProxyFactory and DeviceProxy once pytango issue
# https://gitlab.com/tango-controls/pytango/-/issues/459 has been fixed.
class _DeviceProxyFactory:  # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        self.factory = tango.DeviceProxy

    def __call__(
        self, device_name: str, *args: Any, **kwargs: Any
    ) -> tango.DeviceProxy:
        return self.factory(device_name, *args, **kwargs)


DeviceProxy = _DeviceProxyFactory()
"""
A drop-in replacement for :py:class:`tango.DeviceProxy`.

There is a known bug in :py:class:`tango.test_context.MultiDeviceTestContext`
for which the workaround is a patch to :py:class:`tango.DeviceProxy`.
This drop-in replacement makes it possible for
:py:class:`~ska_tango_testing.context.ThreadedTestTangoContextManager`
to apply this patch. Until the bug is fixed, all production code that
will be tested in that context must use this class instead of
:py:class:`tango.DeviceProxy`.

(For more information, see
https://gitlab.com/tango-controls/pytango/-/issues/459.)
"""


# pylint: disable-next=too-few-public-methods
class TangoContextProtocol(Protocol):
    """Protocol for a tango context."""

    def get_device(self, device_name: str) -> tango.DeviceProxy:
        """
        Return a proxy to a specified device.

        :param device_name: name of the device

        :return: a proxy to the device
        """  # noqa: DAR202


class TrueTangoContextManager:
    """
    A Tango context in which the device has already been deployed.

    For example, Tango has been deployed into a k8s cluster, and now we
    want to run tests against it.
    """

    def __enter__(self) -> TangoContextProtocol:
        """
        Enter the context.

        :return: the context
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        trace: Optional[TracebackType],
    ) -> Literal[False]:
        """
        Exit the context.

        :param exc_type: the type of exception thrown in the with block
        :param exception: the exception thrown in the with block
        :param trace: a traceback

        :returns: whether the exception (if any) has been fully handled
            by this method and should be swallowed i.e. not re-raised
        """
        return False

    # pylint: disable-next=no-self-use
    def get_device(self, device_name: str) -> tango.DeviceProxy:
        """
        Return a proxy to a specified device.

        :param device_name: name of the device

        :return: a proxy to the device
        """
        return tango.DeviceProxy(device_name)


class ThreadedTestTangoContextManager:
    """A lightweight context for testing Tango devices."""

    def __init__(self) -> None:
        """Initialise a new instance."""
        self._device_info_by_class: Dict[
            Union[str, Type[tango.server.Device]], List[Dict[str, Any]]
        ] = {}
        self._context = None

    def add_device(
        self,
        device_name: str,
        device_class: Union[str, Type[tango.server.Device]],
        **properties: Any,
    ) -> None:
        """
        Add a device to the context managed by this manager.

        :param device_name: name of the device to be added
        :param device_class: the class of the device to be added. This
            can be the class itself, or its name.
        :param properties: a dictionary of device properties
        """
        self._device_info_by_class.setdefault(device_class, [])
        self._device_info_by_class[device_class].append(
            {"name": device_name, "properties": properties}
        )

    def __enter__(self) -> TangoContextProtocol:
        """
        Enter the context.

        The context is a :py:class:`tango.test_context.MultiDeviceTestContext`,
        which has a known bug that forces us to patch `tango.DeviceProxy`.

        :return: a proxy to the device under test.
        """
        device_info = [
            {"class": class_name, "devices": devices}
            for class_name, devices in self._device_info_by_class.items()
        ]

        self._context = tango.test_context.MultiDeviceTestContext(
            device_info,
            process=False,
            daemon=True,
        )
        assert self._context is not None  # for the type checker

        DeviceProxy.factory = lambda name, *args, **kwargs: tango.DeviceProxy(
            self._context.get_device_access(name), *args, **kwargs
        )

        self._context.__enter__()
        return self._context

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        trace: Optional[TracebackType],
    ) -> bool:
        """
        Exit method for "with" context.

        :param exc_type: the type of exception thrown in the with block
        :param exception: the exception thrown in the with block
        :param trace: a traceback

        :returns: whether the exception (if any) has been fully handled
            by this method and should be swallowed i.e. not re-raised
        """
        assert self._context is not None  # for the type checker
        try:
            # pylint: disable-next=assignment-from-no-return
            return self._context.__exit__(exc_type, exception, trace)
        finally:
            self._context = None
