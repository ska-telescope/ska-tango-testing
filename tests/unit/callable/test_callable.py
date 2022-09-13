"""This module contains tests of the :py:class:`MockCallable` class."""
from typing import Callable

import pytest

from ska_tango_testing.mock import MockCallable


def test_assert_call_when_called(
    mock_callable: MockCallable, schedule_call: Callable
) -> None:
    """
    Test that we can `assert_call` when the mock callable has been called.

    :param mock_callable: the mock callable under test
    :param schedule_call: a callable used to schedule a call.
    """
    args = ("arg1", "arg2")
    kwargs = {"kwarg1": "kwarg1", "kwarg2": "kwarg2"}

    schedule_call(0.5, mock_callable, *args, **kwargs)
    call_details = mock_callable.assert_call(*args, **kwargs)
    assert call_details == {
        "call_args": args,
        "call_kwargs": kwargs,
        "arg0": args[0],
        "arg1": args[1],
        "kwarg1": "kwarg1",
        "kwarg2": "kwarg2",
    }


def test_assert_call_when_not_called(
    mock_callable: MockCallable, schedule_call: Callable
) -> None:
    """
    Test that assert_call fails when the mock callable is called too late.

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


def test_assert_against_call(
    mock_callable: MockCallable, schedule_call: Callable
) -> None:
    """
    Test that assertions on a callback call consume the call on the group.

    :param mock_callable: the mock callable under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(
        0.2,
        mock_callable,
        "first_arg",
        "second_arg",
        first_kwarg=1,
        second_kwarg=2,
        third_kwarg=3,
    )

    mock_callable.assert_against_call(arg1="second_arg", second_kwarg=2)


def test_configure_mock(mock_callable: MockCallable) -> None:
    """
    Test that `configure_mock` configuration data configures the callable.

    Here we only test that the callable returns a configured return
    value when called.

    :param mock_callable: the mock callable under test
    """
    mock_callable.configure_mock(return_value="return_value")

    assert mock_callable("arg", kwarg="kwarg") == "return_value"
    mock_callable.assert_call("arg", kwarg="kwarg")


def test_mock_configuration_exception() -> None:
    """Test that configuration of exceptions is also correct."""
    mock_callable = MockCallable(timeout=1.0)
    mock_callable.configure_mock(
        side_effect=ValueError("side effect exception")
    )

    with pytest.raises(ValueError, match="side effect exception"):
        mock_callable("arg", kwarg="kwarg")
    mock_callable.assert_call("arg", kwarg="kwarg")
