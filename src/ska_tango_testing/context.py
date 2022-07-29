"""This module provides support for tango testing contexts."""
# TODO: So far this module only supports single device contexts.

from types import TracebackType
from typing import Any, Dict, Optional, Type

import tango
import tango.server
from typing_extensions import Literal


class TrueTangoContext:
    """
    A Tango context in which the device has already been deployed.

    For example, Tango has been deployed into a k8s cluster, and now we
    want to run tests against it.
    """

    def __init__(self, fqdn: str) -> None:
        """
        Initialise a new instance.

        :param fqdn: FQDN of the device under test
        """
        self._fqdn = fqdn

    def __enter__(self) -> tango.DeviceProxy:
        """
        Enter the context.

        This is called when the "with" syntax is used.

        :return: a proxy to the device under test
        """
        return tango.DeviceProxy(self._fqdn)

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


class TestTangoContext:
    """A lightweight context for testing Tango devices."""

    def __init__(
        self,
        device_class: Type[tango.server.Device],
        properties: Dict[str, Any],
        process: bool = True,
    ):
        """
        Initialise a new instance.

        :param device_class: class of the device under test
        :param properties: properties of the device under test.
        :param process: whether to run the device in a separate process.
            If False, the device is run in a separate thread.
        """
        self._context = tango.test_context.DeviceTestContext(
            device_class,
            properties=properties,
            process=process,
            daemon=True,
        )

    def __enter__(self) -> tango.DeviceProxy:
        """
        Enter the context.

        :return: a proxy to the device under test.
        """
        self._context.__enter__()
        return self._context.device

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
        return self._context.__exit__(exc_type, exception, trace)
