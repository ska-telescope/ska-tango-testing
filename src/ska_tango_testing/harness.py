"""This module provides a test harness factory for testing Tango devices."""
from __future__ import annotations

import logging
from contextlib import ExitStack
from types import TracebackType
from typing import Any, ContextManager, cast

from tango import DeviceProxy
from tango.server import Device

from .context import (
    TangoContextProtocol,
    ThreadedTestTangoContextManager,
    TrueTangoContextManager,
)

logger = logging.getLogger("ska_tango_testing.harness")


class TangoTestHarnessContext:
    """Representation of a test harness context."""

    def __init__(
        self: TangoTestHarnessContext,
        tango_context: TangoContextProtocol,
        contexts: dict[str, Any],
    ) -> None:
        """
        Initialise a new instance.

        :param tango_context: the Tango context for this test harness.
        :param contexts: other contexts for this test harness.
        """
        self._tango_context = tango_context
        self._contexts = contexts

    def get_device(
        self: TangoTestHarnessContext,
        device_name: str,
    ) -> DeviceProxy:
        """
        Return a proxy to a Tango device running in this test harness context.

        :param device_name: name of the Tango device.

        :return: a proxy to the Tango device.
        """
        return self._tango_context.get_device(device_name)

    def get_context(
        self: TangoTestHarnessContext,
        context_name: str,
    ) -> Any:
        """
        Return a sub-context of this test harness.

        For example, if this test harness contains a context manager
        that launches a simulator as a TCP server, and returns the
        address of that server, then this method can be used to recover
        that address.

        :param context_name:
            name under which the context manager was added.

        :return: the context hook for the named context.
        """
        return self._contexts[context_name]


class TangoTestHarness:
    """A test harness for Tango devices."""

    def __init__(self: TangoTestHarness) -> None:
        """Initialise a new instance."""
        self._devices: dict[
            str, tuple[type[Device] | str, dict[str, Any]]
        ] = {}
        self._mocks: dict[str, DeviceProxy] = {}
        self._context_managers: dict[str, ContextManager[Any]] = {}
        self._tango_context_manager: ContextManager[
            TangoContextProtocol
        ] | None = None

        self._exit_stack = ExitStack()

    def add_device(
        self: TangoTestHarness,
        device_name: str,
        device_class: type[Device] | str,
        **properties: Any,
    ) -> None:
        """
        Add a Tango device to this test harness.

        :param device_name: name of the device to be added
        :param device_class: the class of the device to be added. This
            can be the class itself, or its name.
        :param properties: a dictionary of device properties
        """
        logger.debug(f"Adding device {device_name} to test harness.")
        self._devices[device_name] = (device_class, properties)

    def add_mock_device(
        self: TangoTestHarness,
        device_name: str,
        device_mock: DeviceProxy,
    ) -> None:
        """
        Register a mock at a given Tango device name.

        Registering this mock means that when an attempts is made to
        create a `tango.DeviceProxy` to that device name, this mock is
        returned instead.

        :param device_name: name of the device for which the mock is to
            be registered.
        :param device_mock: the mock to be registered at this name.
        """
        logger.debug(f"Adding mock device {device_name} to test harness.")
        self._mocks[device_name] = device_mock

    def add_context_manager(
        self: TangoTestHarness,
        context_name: str,
        context_manager: ContextManager[Any],
    ) -> None:
        """
        Add a context manager to this test harness.

        When we enter the context of this test harness, we enter the
        contexts of any context managers registered with this method.

        For example,
        suppose we want to test our ``FooDevice`` Tango device,
        but first we need to stand up a HTTP server interface
        to a ``FooSimulator``,
        so that the ``FooDevice`` has something to monitor and control.
        To achieve this, we create a context manager
        that provides a context in which
        the required ``FooSimulator`` HTTP server is running;
        and we register that context manager with this test harness.
        When we enter this harness, we also enter the simulator context,
        which means the HTTP server gets launched.

        :param context_name: name of the context.
            We can use this to recover the context once entered.
        :param context_manager: the context manager to launch.
        """
        logger.debug(f"Adding context manager {context_name} to test harness.")
        self._context_managers[context_name] = context_manager

    def __enter__(self: TangoTestHarness) -> TangoTestHarnessContext:
        """
        Enter the context.

        :return: the entered context.
        """
        logger.debug("Entering test harness context...")
        self._exit_stack.__enter__()

        contexts = {
            context_name: self._exit_stack.enter_context(context_manager)
            for context_name, context_manager in self._context_managers.items()
        }

        if not self._devices and not self._mocks:
            logger.info(
                "Test harness has no devices to deploy, "
                "so will not deploy a Tango test context. "
            )
            self._tango_context_manager = TrueTangoContextManager()
        else:
            logger.info(
                "Test harness is deploying a Tango test context.\n"
                f"* Devices: {', '.join(self._devices)}\n"
                f"* Mocks: {', '.join(self._mocks)}"
            )
            self._tango_context_manager = ThreadedTestTangoContextManager()
            for device_name, (
                device_class,
                properties,
            ) in self._devices.items():
                resolved_properties = {
                    name: (value(contexts) if callable(value) else value)
                    for name, value in properties.items()
                }
                logger.debug(
                    f"Resolved properties for device {device_name}: "
                    f"{repr(resolved_properties)}."
                )
                self._tango_context_manager.add_device(
                    device_name, device_class, **resolved_properties
                )
            for device_name, device_mock in self._mocks.items():
                self._tango_context_manager.add_mock_device(
                    device_name, device_mock
                )

        tango_context = self._exit_stack.enter_context(
            cast(
                ContextManager[TangoContextProtocol],
                self._tango_context_manager,
            )
        )
        return TangoTestHarnessContext(tango_context, contexts)

    def __exit__(
        self: TangoTestHarness,
        exc_type: type[BaseException] | None,
        exception: BaseException | None,
        trace: TracebackType | None,
    ) -> bool | None:
        """
        Exit the context.

        :param exc_type: the type of exception thrown in the with block,
            if any.
        :param exception: the exception thrown in the with block, if
            any.
        :param trace: the exception traceback, if any,

        :return: whether the exception (if any) has been fully handled
            by this method and should be swallowed i.e. not re-raised
        """
        logger.debug("Exiting test harness context...")
        return self._exit_stack.__exit__(exc_type, exception, trace)
