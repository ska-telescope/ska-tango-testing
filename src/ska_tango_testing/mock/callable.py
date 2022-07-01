"""This module provides a mock callable class."""
from __future__ import annotations

import queue
import unittest.mock
from typing import Any, Dict, Optional

from .consumer import CharacterizerType, ConsumerAsserter, MockConsumerGroup


def _characterizer_factory(
    special_characterizer: Optional[CharacterizerType],
) -> CharacterizerType:
    def _characterize_call(characteristics: Dict[str, Any]) -> Dict[str, Any]:
        (_, args, kwargs) = characteristics["item"]
        characteristics["call_args"] = args
        characteristics["call_kwargs"] = kwargs

        del characteristics["item"]

        if special_characterizer is not None:
            characteristics = special_characterizer(characteristics)

        return characteristics

    return _characterize_call


class MockCallableGroup:
    """This class implements a group of callables."""

    def __init__(
        self: MockCallableGroup,
        *callables: str,
        timeout: Optional[float] = 1.0,
        **special_callables: CharacterizerType,
    ) -> None:
        """
        Initialise a new instance.

        :param callables: names of simple callables in this group; that
            is, callables that do not need a special characterizer.
        :param timeout: number of seconds to wait for the callable to be
            called, or None to wait forever. The default is 1.0 seconds.
        :param special_callables: keyword argument for special callables
            that need a special characterizer. Each argument is of the
            form `callable_name=characterizer`.
        """
        self._queue: queue.SimpleQueue[Dict[str, Any]] = queue.SimpleQueue()
        characterizers = {
            category: _characterizer_factory(None) for category in callables
        }
        characterizers.update(
            {
                category: _characterizer_factory(special_callable)
                for category, special_callable in special_callables.items()
            }
        )

        self._mock_consumer_group = MockConsumerGroup(
            lambda timeout: self._queue.get(timeout=timeout),
            lambda payload: payload[0],
            timeout,
            **characterizers,
        )

        self._callables = {
            name: self._Callable(
                self._queue, name, self._mock_consumer_group[name]
            )
            for name in characterizers
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
    ) -> Dict[str, Any]:
        """
        Assert that the specified callable has been called as specified.

        For example, `assert_call("a", "b", c=1, lookahead=2)` will
        assert that one of the next 2 calls to callable "a" will
        have call signature `("b", c=1)`.

        This is syntactic sugar, which simplifies the expression of
        assertions, but also muddles up the arguments to `assert_call`
        with the arguments that we are asserting the call to have. It is
        equivalent to the more principled and flexible, but long-winded:

        .. code-block:: py

            assert_against_call(
                "a",
                call_args=("b",),
                call_kwargs={"c": 1},
                lookahead=2,
            )

        :param callable_name: name of the callable that we are asserting
            to have been called
        :param args: positional arguments asserted to be in the call.
        :param kwargs: If a "lookahead" keyword argument is provided,
            this specifies the number of calls to examine in search of a
            matching call. The default is 1, in which case we are
            asserting against the *next* call.

            All other keyword arguments are keyword arguments
            asserted to be in the call.

        :return: details of the call

        :raises AssertionError: if the asserted call has not occurred
            within the timeout period
        """
        lookahead = kwargs.pop("lookahead", 1)
        try:
            return self.assert_against_call(
                callable_name,
                call_args=args,
                call_kwargs=kwargs,
                lookahead=lookahead,
            )
        except AssertionError:
            raise  # pylint: disable=try-except-raise

    def assert_against_call(
        self: MockCallableGroup,
        callable_name: str,
        lookahead: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Assert that the specified callable has been called as characterised.

        :param callable_name: name of the callable that we are asserting
            to have been called
        :param lookahead:  The number of calls to examine in search of a
            matching call. The default is 1, which means we are
            asserting against the *next* call.
        :param kwargs: the characteristics that we are asserting the
            call to have. All call have `call_args` and `call_kwargs`
            characteristics. For example,

            .. code-block:: py

                assert_against_call(
                    "a",
                    lookahead=2,
                    call_args=("b",),
                    call_kwargs={"c": 1},
                )

            asserts that one of the next two calls to callback "a" will
            have the signature ("b", c=1). If a characterizer was
            provided for the callback in this group's constructor, then
            there may be other characteristics that this method can
            assert against. For example, suppose we expect callable "a"
            to have been called with signature

            .. code-block:: py

                callable_a(name="a", value=2, timestamp=1234567890)

            but the timestamp is unknown. If we don't know the timestamp
            then we can't

            .. code-block:: py

                assert_against_call(
                    "a",
                    lookahead=2,
                    call_args=(,),
                    call_kwargs={
                        "name": "a",
                        "value": 2,
                        "timestamp": 1234567890,
                    },
                )

            Instead we can provide a characterizer that unpacks the
            "name" and "value" arguments for us, and then

            .. code-block:: py

                assert_against_call(
                    "a",
                    lookahead=2,
                    name="a",
                    value=2,
                )

        :return: details of the call

        :raises AssertionError: if the asserted call has not occurred
            within the timeout period
        """
        try:
            return self._mock_consumer_group.assert_item(
                category=callable_name,
                lookahead=lookahead or 1,
                **kwargs,
            )
        except AssertionError as assertion_error:
            raise AssertionError(
                f"Callable has not been called with characteristics "
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
            self._call_queue.put((self._name, args, kwargs))

            mock = unittest.mock.Mock(self._mock_configuration)
            return mock(*args, **kwargs)

        def assert_call(
            self: MockCallableGroup._Callable,
            *args: Any,
            **kwargs: Any,
        ) -> Dict[str, Any]:
            """
            Assert that this callable has been called as specified.

            For example, `assert_call("b", c=1, lookahead=2)` asserts
            that one of the next 2 calls to this callable will have call
            signature `("b", c=1)`.

            This is syntactic sugar, which simplifies the expression of
            assertions, but also muddles up the arguments to
            `assert_call` with the arguments that we are asserting the
            call to have. It is equivalent to the more principled and
            flexible, but long-winded:

            .. code-block:: py

                assert_against_call(
                    call_args=("b",),
                    call_kwargs={"c": 1},
                    lookahead=2,
                )

            :param args: positional arguments asserted to be in the call.
            :param kwargs: If a "lookahead" keyword argument is
                provided, this specifies the number of calls to examine
                in search of a matching call. The default is 1, in which
                case we are asserting against the *next* call.

                All other keyword arguments are keyword arguments
                asserted to be in the call.

            :return: details of the call

            :raises AssertionError: if the asserted call has not occurred
                within the timeout period
            """
            lookahead = kwargs.pop("lookahead", 1)
            try:
                return self.assert_against_call(
                    call_args=args,
                    call_kwargs=kwargs,
                    lookahead=lookahead,
                )
            except AssertionError:
                raise  # pylint: disable=try-except-raise

        def assert_against_call(
            self: MockCallableGroup._Callable,
            lookahead: Optional[int] = None,
            **kwargs: Any,
        ) -> Dict[str, Any]:
            """
            Assert that this callable has been called as characterised.

            :param lookahead:  The number of calls to examine in search
                of a matching call. The default is 1, which means we are
                asserting against the *next* call.
            :param kwargs: the characteristics that we are asserting the
                call to have. All calls have `call_args` and
                `call_kwargs` characteristics. For example,

                .. code-block:: py

                    assert_against_call(
                        lookahead=2,
                        call_args=("b",),
                        call_kwargs={"c": 1},
                    )

                asserts that one of the next two calls to this callback
                will have the signature ("b", c=1). If a characterizer
                was provided for the callback in this group's
                constructor, then there may be other characteristics
                that this method can assert against. For example,
                suppose we expect this callable to have been called with
                signature

                .. code-block:: py

                    this_callable(name="a", value=2, timestamp=1234567890)

                but the timestamp is unknown. If we don't know the
                timestamp then we can't

                .. code-block:: py

                    assert_against_call(
                        lookahead=2,
                        call_args=(,),
                        call_kwargs={
                            "name": "a",
                            "value": 2,
                            "timestamp": 1234567890,
                        },
                    )

                Instead we can provide a characterizer that unpacks the
                "name" and "value" arguments for us, and then

                .. code-block:: py

                    assert_against_call(
                        lookahead=2,
                        name="a",
                        value=2,
                    )

            :return: details of the call

            :raises AssertionError: if the asserted call has not
                occurred within the timeout period
            """
            try:
                return self._consumer_view.assert_item(
                    category=self._name,
                    # args=args,
                    # kwargs=kwargs,
                    lookahead=lookahead or 1,
                    **kwargs,
                )
            except AssertionError as assertion_error:
                raise AssertionError(
                    f"Callable has not been called with characteristics "
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
    ) -> Dict[str, Any]:
        """
        Assert that this callable has been called as specified.

        For example, `assert_call("b", c=1, lookahead=2)` asserts that
        one of the next 2 calls to this callable will have call
        signature `("b", c=1)`.

        This is syntactic sugar, which simplifies the expression of
        assertions, but also muddles up the arguments to `assert_call`
        with the arguments that we are asserting the call to have. It is
        equivalent to the more principled and flexible, but long-winded:

        .. code-block:: py

            assert_against_call(
                call_args=("b",),
                call_kwargs={"c": 1},
                lookahead=2,
            )

        :param args: positional arguments asserted to be in the call.
        :param kwargs: If a "lookahead" keyword argument is provided,
            this specifies the number of calls to examine in search of a
            matching call. The default is 1, in which case we are
            asserting against the *next* call.

            All other keyword arguments are keyword arguments
            asserted to be in the call.

        :return: details of the call

        :raises AssertionError: if the asserted call has not occurred
            within the timeout period
        """
        lookahead = kwargs.pop("lookahead", 1)
        try:
            return self.assert_against_call(
                call_args=args,
                call_kwargs=kwargs,
                lookahead=lookahead,
            )
        except AssertionError:
            raise  # pylint: disable=try-except-raise

    def assert_against_call(
        self: MockCallable,
        lookahead: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Assert that this callable has been called as characterised.

        :param lookahead:  The number of calls to examine in search of a
            matching call. The default is 1, which means we are
            asserting against the *next* call.
        :param kwargs: the characteristics that we are asserting the
            call to have. All calls have `call_args` and `call_kwargs`
            characteristics. For example,

            .. code-block:: py

                assert_against_call(
                    lookahead=2,
                    call_args=("b",),
                    call_kwargs={"c": 1},
                )

            asserts that one of the next two calls to this callback will
            have the signature ("b", c=1). If a characterizer was
            provided for the callback in this group's constructor, then
            there may be other characteristics that this method can
            assert against. For example, suppose we expect this callable
            to have been called with signature

            .. code-block:: py

                this_callable(name="a", value=2, timestamp=1234567890)

            but the timestamp is unknown. If we don't know the timestamp
            then we can't

            .. code-block:: py

                assert_against_call(
                    lookahead=2,
                    call_args=(,),
                    call_kwargs={
                        "name": "a",
                        "value": 2,
                        "timestamp": 1234567890,
                    },
                )

            Instead we can provide a characterizer that unpacks the
            "name" and "value" arguments for us, and then

            .. code-block:: py

                assert_against_call(
                    lookahead=2,
                    name="a",
                    value=2,
                )

        :return: details of the call

        :raises AssertionError: if the asserted call has not occurred
            within the timeout period
        """
        try:
            call_details = self._view.assert_against_call(
                # args=args, kwargs=kwargs,
                lookahead=lookahead or 1,
                **kwargs,
            )
            del call_details["category"]
            return call_details
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
