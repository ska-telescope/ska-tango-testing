"""This module provides support for tango testing contexts."""

from __future__ import annotations

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
        self._context: Optional[
            ThreadedTestTangoContextManager._TangoContext
        ] = None
        self._mocks: Dict[str, tango.DeviceProxy] = {}

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

    def add_mock_device(
        self,
        device_name: str,
        device_mock: tango.DeviceProxy,
    ) -> None:
        """
        Register a mock at a given device name.

        Registering this mock means that when an attempts is made to
        create a `tango.DeviceProxy` to that device name, this mock is
        returned instead.

        :param device_name: name of the device for which the mock is to
            be registered.
        :param device_mock: the mock to be registered at this name.
        """
        self._mocks[device_name] = device_mock

    class _TangoContext:
        def __init__(
            self,
            device_info: List[Dict[str, Any]],
            mocks: Dict[str, tango.DeviceProxy],
        ) -> None:
            self._context = tango.test_context.MultiDeviceTestContext(
                device_info,
                process=False,
                daemon=True,
            )
            self._mocks = mocks

        def __enter__(self) -> TangoContextProtocol:
            DeviceProxy.factory = self._proxy_factory
            self._context.__enter__()
            return self

        def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exception: Optional[BaseException],
            trace: Optional[TracebackType],
        ) -> bool:
            # pylint: disable-next=assignment-from-no-return
            return self._context.__exit__(exc_type, exception, trace)

        def _proxy_factory(
            self, name: str, *args: Any, **kwargs: Any
        ) -> tango.DeviceProxy:
            if name in self._mocks:
                return self._mocks[name]
            return tango.DeviceProxy(
                self._context.get_device_access(name), *args, **kwargs
            )

        def get_device(self, device_name: str) -> tango.DeviceProxy:
            """
            Return a proxy to a Tango device.

            This implementation first checks if a mock has been
            registered, and if so it returns the registered mock.
            Otherwise it attempts to create a proxy to the device
            specified.

            :param device_name: name of the device

            :return: a proxy to the device
            """
            return self._proxy_factory(device_name)

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
        self._context = self._TangoContext(device_info, self._mocks)
        return self._context.__enter__()

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
