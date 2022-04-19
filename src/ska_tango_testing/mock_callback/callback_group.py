"""This module provides support for asserting over multiple callbacks."""
from __future__ import annotations

import queue
from typing import Any, Dict, Hashable, Optional
from unittest.mock import Mock

from .callback import MockCallback
from .callback_queue_protocol import MockCallbackQueueProtocol
from .queue_group import QueueGroup


class _QueueView(MockCallbackQueueProtocol):
    def __init__(  # pylint: disable=super-init-not-called
        self: _QueueView,
        queue_group: QueueGroup,
        callback_name: Hashable,
    ) -> None:
        """
        Initialise a new instance.

        :param queue_group: the group to which this callback belongs.
        :param callback_name: the name of this callback within the
            group.
        """
        self._queue_group = queue_group
        self._callback_name = callback_name

    def put(self: _QueueView, called_mock: Mock) -> None:
        self._queue_group.put(self._callback_name, called_mock)

    def get(self: _QueueView, timeout: Optional[float] = None) -> Mock:
        return self._queue_group.get_from(self._callback_name, timeout=timeout)


class MockCallbackGroup:
    """This class implements a group of callbacks."""

    def __init__(self) -> None:
        """Initialise a new instance."""
        self._callbacks: Dict[Hashable, MockCallback] = {}
        self._max_timeout: Optional[float] = 0.0
        self._queue_group = QueueGroup()

    def new_callback(
        self: MockCallbackGroup,
        callback_name: Hashable,
        **kwargs: Any,
    ) -> MockCallback:
        """
        Add a new callback to this group and return it.

        :param callback_name: name of the callback to be added
        :param kwargs: keyword arguments to pass to the `MockCallback`
            initialisation method.

        :return: a callback
        """
        self._callbacks[callback_name] = MockCallback(
            callback_queue=_QueueView(self._queue_group, callback_name),
            **kwargs,
        )

        timeout = self._callbacks[callback_name].timeout  # for mypy
        if self._max_timeout is None or timeout is None:
            self._max_timeout = None
        elif timeout > self._max_timeout:
            self._max_timeout = timeout

        return self._callbacks[callback_name]

    def __getitem__(
        self: MockCallbackGroup, callback_name: Hashable
    ) -> MockCallback:
        """
        Return a callback by name.

        If the callback does not exist, it is created using default
        values. For more flexibility in callback creation, see
        :py:meth:`new_callback`.

        :param callback_name: name of the callback (actually this can be
            anything hashable)

        :return: a callback
        """
        if callback_name not in self._callbacks:
            return self.new_callback(callback_name)
        return self._callbacks[callback_name]

    def assert_next_call(
        self: MockCallbackGroup,
        callback_name: Hashable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Assert the next call on any callback in this group.

        If the call has not been made, this method will wait up to the
        specified timeout for a call to arrive.

        :param callback_name: the name of the callback asserted to be
            the next to be called.
        :param args: positional arguments that the call is asserted to
            have
        :param kwargs: keyword arguments that the call is asserted to
            have

        :raises AssertionError: if the callback has not been called.
        """
        try:
            (next_callback_name, called_mock) = self._queue_group.get(
                timeout=self._callbacks[callback_name].timeout
            )
        except queue.Empty:
            raise AssertionError(  # pylint: disable=raise-missing-from
                "No callback has been called."
            )

        assert next_callback_name == callback_name, (
            f"Next call was to callback '{next_callback_name}', not "
            f"'{callback_name}'."
        )
        try:
            called_mock.assert_called_once_with(*args, **kwargs)
        except AssertionError as assertion_error:
            raise AssertionError(
                f"Callback '{callback_name}' was called next, but arguments "
                "differ."
            ) from assertion_error

    def assert_not_called(
        self: MockCallbackGroup, **kwargs: Optional[float]
    ) -> None:
        """
        Assert that no callback in this group has been called.

        This is a slow method because it has to wait the full timeout
        period in order to determine that a call has not arrived. An
        optional timeout parameter is provided for situations where you
        are happy for the assertion to pass after a shorter wait time.

        :param kwargs: additional keyword arguments. The only supported
            argument is "timeout", which, if provided, specifies the
            timeout in seconds. If set to None, we wait forever. If
            ommited, the default is the class setting.

        :raises AssertionError: if a callback has been called.
        """
        try:
            (callback_name, _) = self._queue_group.get(
                timeout=kwargs.get("timeout", self._max_timeout)
            )
        except queue.Empty:
            return
        raise AssertionError(
            f"MockCallback '{callback_name}' has been called."
        )
