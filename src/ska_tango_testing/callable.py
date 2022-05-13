"""This module provides a mock callable class."""
from __future__ import annotations

import queue
import unittest.mock
from typing import Any, Dict, NamedTuple, Optional, Tuple

from .consumer import ConsumerAsserter, MockConsumerGroup


class MockCallableGroup:
    """This class implements a group of callables."""

    class _CallableInfo(NamedTuple):
        name: str
        args: Tuple
        kwargs: Dict[str, Any]

    def __init__(
        self: MockCallableGroup,
        *callables: str,
        timeout: Optional[float] = 1.0,
    ) -> None:
        """
        Initialise a new instance.

        :param timeout: number of seconds to wait for the callable to be
            called, or None to wait forever. The default is 1.0 seconds.
        :param callables: names of callables in this group.
        """
        self._queue: queue.SimpleQueue[
            MockCallableGroup._CallableInfo
        ] = queue.SimpleQueue()

        characterizers = {category: None for category in callables}

        self._mock_consumer_group = MockConsumerGroup(
            lambda timeout: self._queue.get(timeout=timeout),
            lambda callable_info: callable_info.name,
            timeout,
            **characterizers,
        )

        self._callables = {
            name: self._Callable(
                self._queue, name, self._mock_consumer_group[name]
            )
            for name in callables
        }

    def __getitem__(
        self: MockCallableGroup,
        callable_name: str,
    ) -> MockCallableGroup._Callable:
        """
        Return a standalone callable for the specified callable_name.

        This can be passed to the caller to be actually called, and it
        can also be used to assert calls.

        :param callable_name: name of the callable sought.

        :return: a standalone mock callable
        """
        return self._callables[callable_name]

    def assert_call(
        self: MockCallableGroup,
        callable_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Assert that the specified callable has been called as specified.

        :param callable_name: name of the callable that we are asserting
            to have been called
        :param args: positional arguments asserted to be in the call
        :param kwargs: keyword arguments. An optional "lookahead"
            keyword argument may be used to specify the number of calls
            to examing in search of a matching call. The default is 1,
            which means we are asserting on the *next* call, All other
            keyword arguments are part of the asserted call.

        :raises AssertionError: if the asserted call has not occurred
            within the timeout period
        """
        lookahead = kwargs.pop("lookahead", 1)
        try:
            self._mock_consumer_group.assert_item(
                (callable_name, args, kwargs), lookahead=lookahead
            )
        except AssertionError as assertion_error:
            raise AssertionError(
                f"Callable has not been called with args {args}, kwargs "
                f"{kwargs}."
            ) from assertion_error

    def assert_not_called(self: MockCallableGroup) -> None:
        """
        Assert that no callable in this group has been called.

        :raises AssertionError: if one of the callables in this group
            has been called.
        """
        try:
            self._mock_consumer_group.assert_no_item()
        except AssertionError as assertion_error:
            raise AssertionError(
                "Callable has been called."
            ) from assertion_error

    class _Callable:
        """A view on a single callable."""

        def __init__(
            self: MockCallableGroup._Callable,
            call_queue: queue.SimpleQueue,
            name: str,
            consumer_view: ConsumerAsserter,
        ) -> None:
            """
            Initialise a new instance.

            :param call_queue: the queue in which calls are places
            :param name: the name of this callable
            :param consumer_view: the underlying view on the consumer
            """
            self._call_queue = call_queue
            self._name = name
            self._consumer_view = consumer_view
            self._mock_configuration: Dict[str, Any] = {}

        def configure_mock(self, **configuration: Any) -> None:
            """
            Configure the underlying mock.

            :param configuration: keyword arguments to be passed to the
                underlying mock.
            """
            self._mock_configuration = configuration

        def __call__(
            self: MockCallableGroup._Callable, *args: Any, **kwargs: Any
        ) -> Any:
            """
            Register a call on this callable.

            :param args: positional arguments in the call
            :param kwargs: keyword arguments in the call

            :return: whatever this callable is configured to return
            """
            self._call_queue.put(
                MockCallableGroup._CallableInfo(self._name, args, kwargs)
            )

            mock = unittest.mock.Mock(self._mock_configuration)
            return mock(*args, **kwargs)

        def assert_call(
            self: MockCallableGroup._Callable,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            """
            Assert that this callable has been called as specified.

            :param args: positional arguments asserted to be in the call
            :param kwargs: keyword arguments. An optional "lookahead"
                keyword argument may be used to specify the number of
                calls to examine in search of a matching call. The
                default is 1, which means we are asserting on the *next*
                call, All other keyword arguments are part of the
                asserted call.

            :raises AssertionError: if the asserted call has not
                occurred within the timeout period
            """
            lookahead = kwargs.pop("lookahead", 1)
            try:
                self._consumer_view.assert_item(
                    (self._name, args, kwargs), lookahead=lookahead
                )
            except AssertionError as assertion_error:
                raise AssertionError(
                    f"Callable has not been called with args {args}, kwargs "
                    f"{kwargs}."
                ) from assertion_error

        def assert_not_called(self: MockCallableGroup._Callable) -> None:
            """
            Assert that this callable has not been called.

            :raises AssertionError: if this callable has been called.
            """
            try:
                self._consumer_view.assert_no_item()
            except AssertionError as assertion_error:
                raise AssertionError(
                    "Callable has been called."
                ) from assertion_error


class MockCallable:
    """A class for a single mock callable."""

    def __init__(self: MockCallable, timeout: Optional[float] = 1.0) -> None:
        """
        Initialise a new instance.

        :param timeout: how long to wait for the call, in seconds, or
            None to wait forever. The default is 1 second.
        """
        name = "__mock_callable"
        self._view = MockCallableGroup(name, timeout=timeout)[name]

    def configure_mock(self: MockCallable, **configuration: Any) -> None:
        """
        Configure the underlying mock.

        :param configuration: keyword arguments to be passed to the
            underlying mock.
        """
        self._view.configure_mock(**configuration)

    def assert_call(
        self: MockCallable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Assert that this callable has been called as specified.

        :param args: positional arguments asserted to be in the call
        :param kwargs: keyword arguments. An optional "lookahead"
            keyword argument may be used to specify the number of calls
            to examing in search of a matching call. The default is 1,
            which means we are asserting on the *next* call, All other
            keyword arguments are part of the asserted call.

        :raises AssertionError: if the asserted call has not
            occurred within the timeout period
        """
        try:
            self._view.assert_call(*args, **kwargs)
        except AssertionError:
            raise

    def assert_not_called(self: MockCallable) -> None:
        """
        Assert that this callable has not been called.

        :raises AssertionError: if this callable has been called.
        """
        try:
            self._view.assert_not_called()
        except AssertionError:
            raise

    def __call__(self: MockCallable, *args: Any, **kwargs: Any) -> Any:
        """
        Register a call on this callable.

        :param args: positional arguments in the call
        :param kwargs: keyword arguments in the call

        :return: whatever this callable is configured to return
        """
        return self._view(*args, **kwargs)
