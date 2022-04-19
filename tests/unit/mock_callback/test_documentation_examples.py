"""
This module contains test code that is used in the user guide documentation.

It is used to verify that the documented examples behave as expected.
"""
import threading
import time
import unittest.mock
from typing import Callable

from ska_tango_testing.mock_callback import MockCallbackGroup


def do_asynchronous_work(
    status_callback: Callable[[str], None],
    letter_callback: Callable[[str], None],
    number_callback: Callable[[int], None],
) -> None:
    """
    Do some asynchronous work, calling various callbacks along the way.

    This function is example "production code" for us to test against.

    :param status_callback: a callback to call when the status changes
    :param letter_callback: a callback to call with letter updates
    :param number_callback: a callback to call with number updates
    """

    def call_letters() -> None:
        for letter in ["a", "b", "c", "d"]:
            time.sleep(0.1)
            letter_callback(letter)

    letter_thread = threading.Thread(target=call_letters)

    def call_numbers() -> None:
        for number in [1, 2, 3, 4]:
            time.sleep(0.1)
            number_callback(number)

    number_thread = threading.Thread(target=call_numbers)

    def run() -> None:
        status_callback("IN_PROGRESS")

        letter_thread.start()
        number_thread.start()

        letter_thread.join()
        number_thread.join()

        status_callback("COMPLETED")

    work_thread = threading.Thread(target=run)
    work_thread.start()


def test_do_asynchronous_work_using_unittest_mock() -> None:
    """
    Test that the ``unittest.mock`` example in the user guide works correctly.

    The example under test is an example of what not to do. So this is
    deliberately a problematic piece of code. But we still need to test
    that it works correctly.
    """
    status_callback = unittest.mock.Mock()
    letters_callback = unittest.mock.Mock()
    numbers_callback = unittest.mock.Mock()

    do_asynchronous_work(
        status_callback,
        letters_callback,
        numbers_callback,
    )

    time.sleep(0.05)

    status_callback.assert_called_once_with("IN_PROGRESS")
    status_callback.reset_mock()

    time.sleep(0.1)
    letters_callback.assert_called_once_with("a")
    letters_callback.reset_mock()
    numbers_callback.assert_called_once_with(1)
    numbers_callback.reset_mock()

    time.sleep(0.1)
    letters_callback.assert_called_once_with("b")
    letters_callback.reset_mock()
    numbers_callback.assert_called_once_with(2)
    numbers_callback.reset_mock()

    time.sleep(0.1)
    letters_callback.assert_called_once_with("c")
    letters_callback.reset_mock()
    numbers_callback.assert_called_once_with(3)
    numbers_callback.reset_mock()

    time.sleep(0.1)
    letters_callback.assert_called_once_with("d")
    numbers_callback.assert_called_once_with(4)

    status_callback.assert_called_once_with("COMPLETED")


def test_do_asynchronous_work_using_mock_callback_group() -> None:
    """Test that the ``callback_group`` example in the user guide works."""
    callback_group = MockCallbackGroup()

    do_asynchronous_work(
        callback_group["status"],
        callback_group["letters"],
        callback_group["numbers"],
    )

    callback_group.assert_next_call("status", "IN_PROGRESS")

    for letter in ["a", "b", "c", "d"]:
        callback_group["letters"].assert_next_call(letter)

    for number in [1, 2, 3, 4]:
        callback_group["numbers"].assert_next_call(number)

    callback_group.assert_next_call("status", "COMPLETED")
