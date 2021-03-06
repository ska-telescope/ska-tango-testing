"""This module contains tests of the mock callback module."""
from typing import Callable

import pytest

from ska_tango_testing.mock import MockCallableGroup


def test_assert_no_call_when_no_call(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(1.2, callable_group["a"], "foo", bah="bah")
    callable_group.assert_not_called()


def test_assert_no_call_when_called(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
) -> None:
    """
    Test that `assert_no_item` fails when an item is produced in time.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(0.2, callable_group["a"], "foo", bah="bah")

    with pytest.raises(
        AssertionError,
        match="Callable has been called.",
    ):
        callable_group.assert_not_called()


def test_assert_call_when_no_call(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
) -> None:
    """
    Test that `assert_call` fails when the item is produced too late.

    :param callable_group: the callback group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(1.2, callable_group["a"], "foo", bah="bah")

    with pytest.raises(
        AssertionError,
        match="Callable has not been called",
    ):
        callable_group.assert_call("a", "foo", bah="bah")


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
def test_assert_call_when_called(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
    position: int,
    lookahead: int,
) -> None:
    """
    Test `assert_call` when the callback has been called.

    Specifically, we make a sequence of calls, then we select a call
    that we have made, and we assert that the call has been made.
    Whether we expect that assertion to pass or fail depends on whether
    it falls within the lookahead that we are using.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    :param position: (one-based) position in the queue at which the item
        will appear
    :param lookahead: lookahead setting for the assertion.
    """
    schedule_call(0.2, callable_group["a"], 1)
    schedule_call(0.3, callable_group["a"], 2)
    schedule_call(0.4, callable_group["a"], 3)

    if lookahead >= position:
        call_details = callable_group.assert_call(
            "a", position, lookahead=lookahead
        )
        assert call_details == {
            "category": "a",
            "call_args": (position,),
            "call_kwargs": {},
        }
    else:
        with pytest.raises(
            AssertionError,
            match="Callable has not been called with",
        ):
            callable_group.assert_call("a", position, lookahead=lookahead)


def test_assert_callback_not_called_when_not_called(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(1.2, callable_group["a"], "foo", bah="bah")
    callable_group["a"].assert_not_called()


def test_assert_callback_not_called_when_different_callback_called(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(0.2, callable_group["a"], "foo", bah="bah")
    callable_group["b"].assert_not_called()


def test_assert_callback_not_called_when_callback_called(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(0.2, callable_group["a"], "foo", bah="bah")

    with pytest.raises(AssertionError, match="Callable has been called"):
        callable_group["a"].assert_not_called()


def test_assert_callback_called_when_no_call(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
) -> None:
    """
    Test that `assert_item` fails when the item is produced too late.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(0.2, callable_group["a"], 1)
    schedule_call(1.5, callable_group["b"], 2)

    with pytest.raises(
        AssertionError,
        match="Callable has not been called",
    ):
        callable_group["b"].assert_call(2)


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
def test_assert_specific_item_when_items_are_available(
    callable_group: MockCallableGroup,
    schedule_call: Callable,
    position: int,
    lookahead: int,
) -> None:
    """
    Test `assert_item` when an equal item arrives.

    Specifically, we drop items onto the queue in sequence, then we
    select an item that we have dropped onto the queue, and we assert
    that it is available. Whether we expect that assertion to pass or
    fail depends on whether it falls within the lookahead that we are
    using.

    :param callable_group: the callable group under test
    :param schedule_call: a callable used to schedule a callback call.
    :param position: (one-based) position in the queue at which the item
        will appear
    :param lookahead: lookahead setting for the assertion.
    """
    schedule_call(0.1, callable_group["a"], 0)
    schedule_call(0.2, callable_group["b"], 1)
    schedule_call(0.4, callable_group["b"], 2)
    schedule_call(0.6, callable_group["b"], 3)
    schedule_call(0.8, callable_group["b"], 4)

    if lookahead >= position:
        call_details = callable_group["b"].assert_call(
            position, lookahead=lookahead
        )
        assert call_details == {
            "category": "b",
            "call_args": (position,),
            "call_kwargs": {},
        }

    else:
        with pytest.raises(
            AssertionError,
            match="Callable has not been called with",
        ):
            callable_group["b"].assert_call(position, lookahead=lookahead)


def test_assert_call_consumes_calls(
    callable_group: MockCallableGroup, schedule_call: Callable
) -> None:
    """
    Test that assertions on a callback call consume the call on the group.

    :param callable_group: the callback group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(0.2, callable_group["a"], "started")

    schedule_call(0.4, callable_group["b"], 1, one=1)
    schedule_call(0.5, callable_group["b"], 2, two=2)
    schedule_call(0.8, callable_group["b"], 3, three=3)

    schedule_call(0.5, callable_group["c"], 4)
    schedule_call(0.5, callable_group["c"], 5)
    schedule_call(0.5, callable_group["c"], 6)

    schedule_call(1.0, callable_group["a"], "finished")

    callable_group.assert_call("a", "started")

    callable_group["b"].assert_call(1, one=1)
    callable_group["b"].assert_call(2, two=2)
    callable_group["b"].assert_call(3, three=3)
    callable_group["b"].assert_not_called()

    callable_group["c"].assert_call(4, lookahead=3)
    callable_group["c"].assert_call(5, lookahead=2)
    callable_group["c"].assert_call(6)
    callable_group["c"].assert_not_called()

    callable_group.assert_call("a", "finished")
    callable_group["a"].assert_not_called()

    callable_group.assert_not_called()
