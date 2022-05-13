"""This module contains tests of the :py:class:`MockCallable` class."""
from typing import Callable

import pytest

from ska_tango_testing.callable import MockCallable


def test_assert_next_call_when_called(
    mock_callable: MockCallable, schedule_call: Callable
) -> None:
    """
    Test that we can `assert_next_call` when the mock callable has been called.

    :param mock_callable: the mock callable under test
    :param schedule_call: a callable used to schedule a call.
    """
    args = ["arg1", "arg2"]
    kwargs = {"kwarg1": "kwarg1", "kwarg2": "kwarg2"}

    schedule_call(0.5, mock_callable, *args, **kwargs)
    mock_callable.assert_call(*args, **kwargs)


def test_assert_next_call_when_not_called(
    mock_callable: MockCallable, schedule_call: Callable
) -> None:
    """
    Test that assert_next_call fails when the mock callable is called too late.

    :param mock_callable: the mock callable under test
    :param schedule_call: a callable used to schedule a call.
    """
    args = ["arg1", "arg2"]
    kwargs = {"kwarg1": "kwarg1", "kwarg2": "kwarg2"}

    schedule_call(1.5, mock_callable, *args, **kwargs)

    with pytest.raises(AssertionError, match="Callable has not been called."):
        mock_callable.assert_call(*args, **kwargs)


def test_assert_not_called_when_called(
    mock_callable: MockCallable, schedule_call: Callable
) -> None:
    """
    Test that assert_not_called fails when the mock callable is called.

    :param mock_callable: the mock callable under test
    :param schedule_call: a callable used to schedule a call.
    """
    args = ["arg1", "arg2"]
    kwargs = {"kwarg1": "kwarg1", "kwarg2": "kwarg2"}

    schedule_call(0.5, mock_callable, *args, **kwargs)

    with pytest.raises(
        AssertionError,
        match="Callable has been called",
    ):
        mock_callable.assert_not_called()


def test_assert_not_called_when_not_called(
    mock_callable: MockCallable, schedule_call: Callable
) -> None:
    """
    Test that assert_not_called succeeds when the callable is called too late.

    :param mock_callable: the mock callable under test
    :param schedule_call: a callable used to schedule a call.
    """
    args = ["arg1", "arg2"]
    kwargs = {"kwarg1": "kwarg1", "kwarg2": "kwarg2"}

    schedule_call(1.5, mock_callable, *args, **kwargs)
    mock_callable.assert_not_called()


# def test_initialisation_configuration() -> None:
#     """
#     Test that `__init__` configuration data configures the callable.

#     Here we only test that the callable returns the configured return
#     value when called.
#     """
#     callable = MockCallable(timeout=1.0, return_value="return_value")

#     assert callable("arg", kwarg="kwarg") == "return_value"
#     callable.assert_next_call("arg", kwarg="kwarg")


# def test_configure_mock(callable: MockCallable) -> None:
#     """
#     Test that `configure_mock` configuration data configures the callable.

#     Here we only test that the callable returns a configured return
#     value when called.

#     :param callable: the callable under test
#     """
#     callable.configure_mock(return_value="return_value")

#     assert callable("arg", kwarg="kwarg") == "return_value"
#     callable.assert_next_call("arg", kwarg="kwarg")


# def test_mock_configuration_exception() -> None:
#     """Test that configuration of exceptions is also correct."""
#     callable = MockCallable(
#         timeout=1.0, side_effect=ValueError("side effect exception")
#     )

#     with pytest.raises(ValueError, match="side effect exception"):
#         callable("arg", kwarg="kwarg")
#     callable.assert_next_call("arg", kwarg="kwarg")


# def test_transform() -> None:
#     """Test that transform functionality works correctly."""

#     def _swap_args_and_kwargs(
#         args: List[Any], kwargs: Dict[str, Any]
#     ) -> Tuple[List[Any], Dict[str, Any]]:
#         new_args = [
#             kwargs["input_first_kwarg"], kwargs["input_second_kwarg"]
#         ]
#         new_kwargs = {
#             "output_first_kwarg": args[0],
#             "output_second_kwarg": args[1],
#         }
#         return (new_args, new_kwargs)

#     callable = MockCallable(transform=_swap_args_and_kwargs)
#     callable(
#         "input_first_arg",
#         "input_second_arg",
#         input_first_kwarg="output_first_arg",
#         input_second_kwarg="output_second_arg",
#     )
#     callable.assert_next_call(
#         "output_first_arg",
#         "output_second_arg",
#         output_first_kwarg="input_first_arg",
#         output_second_kwarg="input_second_arg",
#     )
