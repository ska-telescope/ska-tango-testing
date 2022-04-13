"""This module provides a mock callback class."""
from __future__ import annotations

import queue
from typing import Any, Callable, Optional
from unittest.mock import Mock

from .callback_queue_protocol import MockCallbackQueueProtocol


class MockCallback:
    """This class implements a mock callback."""

    def __init__(
        self: MockCallback,
        transform: Optional[Callable] = None,
        callback_queue: Optional[MockCallbackQueueProtocol] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new callback.

        :param transform: An optional transform function to apply to the
            call arguments.
        :param callback_queue: optionally specify the underlying queue
            that this callback should use. If omitted, a
            `queue.SimpleQueue` is created.
        :param kwargs: additional keyword arguments. If "timeout" kwarg
            is provided, this specifies the maximum time to wait, in
            seconds, for a call to occur. If provided as `timeout=None`,
            the callback will wait forever. It omitted, the default is
            1.0 seconds.

            All other kwargs are passed to the underlying
            :py:class:`Mock` objects that are used by this class. Hence
            you can configure this callback in the same way that you
            would consider a `Mock`.
        """
        self._transform = transform
        self._timeout = kwargs.pop("timeout", 1.0)
        self._configure_kwargs = kwargs

        self._queue: MockCallbackQueueProtocol
        if callback_queue is None:
            self._queue = queue.SimpleQueue()  # type: ignore[assignment]
        else:
            self._queue = callback_queue

    @property
    def timeout(self: MockCallback) -> Optional[float]:
        """
        Return the timeout for this callback.

        :return: the timeout for this callback.
        """
        return self._timeout

    def configure_mock(self: MockCallback, **kwargs: Any) -> None:
        """
        Configure the underlying mocks used by this MockCallback.

        :param kwargs: keyword arguments, passed straight to the
            underlying `Mock` objects that are used and returned by this
            class.
        """
        self._configure_kwargs = kwargs

    def __call__(self: MockCallback, *args: Any, **kwargs: Any) -> Any:
        """
        Handle a callback call.

        :param args: positional arguments to the call.
        :param kwargs: keyword arguments to the call.

        :return: whatever this mock callback has been configured to
            return.
        """
        called_mock = Mock(**self._configure_kwargs)
        if self._transform is not None:
            (args, kwargs) = self._transform(args, kwargs)
        try:
            return called_mock(*args, **kwargs)
        finally:
            self._queue.put(called_mock)

    def assert_not_called(
        self: MockCallback, **kwargs: Optional[float]
    ) -> None:
        """
        Assert that the callback is not called withint the timeout period.

        This is a slow method because it has to wait the full timeout
        period in order to determine that the call has not arrived. An
        optional timeout parameter is provided for situations where you
        are happy for the assertion to pass after a shorter wait time.

        :param kwargs: additional keyword arguments. The only supported
            argument is "timeout", which, if provided, sets the timeout,
            in seconds. If None, the callback will never timeout. If not
            provided, the default is the class setting.
        """
        try:
            called_mock = self._queue.get(
                timeout=kwargs.get("timeout", self._timeout)
            )
        except queue.Empty:
            return

        # We already know this will fail and raise an AssertionError.
        called_mock.assert_not_called()

    def assert_next_call(
        self: MockCallback, *args: Any, **kwargs: Any
    ) -> None:
        """
        Assert the arguments of the next call to this mock callback.

        If the call has not been made, this method will wait up to the
        specified timeout for a call to arrive.

        :param args: positional arguments that the call is asserted to
            have
        :param kwargs: keyword arguments that the call is asserted to
            have

        :raises AssertionError: if the callback has not been called.
        """
        try:
            called_mock = self._queue.get(timeout=self._timeout)
        except queue.Empty:
            raise AssertionError(  # pylint: disable=raise-missing-from
                "MockCallback has not been called."
            )
        called_mock.assert_called_once_with(*args, **kwargs)
