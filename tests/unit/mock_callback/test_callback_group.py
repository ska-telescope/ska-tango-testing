"""This module contains tests of the `MockCallback` class."""
from typing import Callable

from ska_tango_testing.mock_callback import MockCallbackGroup


def test_assert_next_call(
    callback_group: MockCallbackGroup, schedule_call: Callable
) -> None:
    """
    Test that we can assert_next_call over multiple callbacks.

    :param callback_group: the callback group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(0.2, callback_group["a"], 1, one=1)
    schedule_call(0.4, callback_group["b"], 2, two=2)
    schedule_call(0.6, callback_group["b"], 3, three=3)
    schedule_call(0.8, callback_group["a"], 4, four=4)

    callback_group.assert_next_call("a", 1, one=1)
    callback_group.assert_next_call("b", 2, two=2)
    callback_group.assert_next_call("b", 3, three=3)
    callback_group.assert_next_call("a", 4, four=4)

    callback_group.assert_not_called()


def test_assert_call_consumption(
    callback_group: MockCallbackGroup, schedule_call: Callable
) -> None:
    """
    Test that assertions on a callback call consume the call on the group.

    :param callback_group: the callback group under test
    :param schedule_call: a callable used to schedule a callback call.
    """
    schedule_call(0.1, callback_group["a"], 1, one=1)
    schedule_call(0.3, callback_group["b"], 2, two=2)
    schedule_call(0.5, callback_group["b"], 3, three=3)
    schedule_call(0.7, callback_group["a"], 4, four=4)
    schedule_call(0.9, callback_group["a"], 5, five=5)

    callback_group["a"].assert_next_call(1, one=1)
    callback_group["b"].assert_next_call(2, two=2)
    callback_group.assert_next_call("b", 3, three=3)
    callback_group.assert_next_call("a", 4, four=4)
    callback_group["b"].assert_not_called()
    callback_group["a"].assert_next_call(5, five=5)
    callback_group.assert_not_called()
