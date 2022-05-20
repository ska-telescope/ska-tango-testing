"""This module contains tests of the mock callback module."""
from typing import Callable

import pytest

from ska_tango_testing import MockTangoEventCallbackGroup


def test_assert_not_called_when_not_called(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that `assert_not_called` succeeds when the event arrives too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(1.2, callback_group["status"], "status", "QUEUED")
    callback_group.assert_not_called()


def test_assert_not_called_when_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that `assert_not_called` fails when an event arrives in time.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["status"], "status", "QUEUED")

    with pytest.raises(
        AssertionError,
        match="Callable has been called.",
    ):
        callback_group.assert_not_called()


def test_assert_call_when_no_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that `assert_against_call` fails when the item is produced too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(1.2, callback_group["status"], "status", "QUEUED")

    with pytest.raises(
        AssertionError,
        match="Callable has not been called",
    ):
        callback_group.assert_against_call("status", attribute_value="QUEUED")


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
def test_assert_against_call_when_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
    position: int,
    lookahead: int,
) -> None:
    """
    Test `assert_against_call` when the callback has been called.

    Specifically, we make a sequence of calls, then we select a call
    that we have made, and we assert that the call has been made.
    Whether we expect that assertion to pass or fail depends on whether
    it falls within the lookahead that we are using.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    :param position: (one-based) position in the queue at which the item
        will appear
    :param lookahead: lookahead setting for the assertion.
    """
    schedule_event(0.2, callback_group["progress"], "progress", 1)
    schedule_event(0.3, callback_group["progress"], "progress", 2)
    schedule_event(0.4, callback_group["progress"], "progress", 3)

    if lookahead >= position:
        callback_group.assert_against_call(
            "progress", attribute_value=position, lookahead=lookahead
        )
    else:
        with pytest.raises(
            AssertionError,
            match="Callable has not been called with",
        ):
            callback_group.assert_against_call(
                "progress", attribute_value=position, lookahead=lookahead
            )


def test_assert_no_call_when_no_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that assert_not_called succeeds when the item is produced too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(1.2, callback_group["status"], "status", "QUEUED")
    callback_group["status"].assert_not_called()


def test_assert_no_call_when_different_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that assert_not_called succeeds when the item is produced too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["progress"], "progress", 50)
    callback_group["status"].assert_not_called()


def test_assert_no_call_when_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that assert_not_called succeeds when the item is produced too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["status"], "status", "IN_PROGRESS")

    with pytest.raises(AssertionError, match="Callable has been called"):
        callback_group["status"].assert_not_called()


def test_assert_against_call_when_no_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that `assert_against_call` fails when the item is produced too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["status"], "status", "IN_PROGRESS")
    schedule_event(1.5, callback_group["progress"], "progress", 50)

    with pytest.raises(
        AssertionError,
        match="Callable has not been called",
    ):
        callback_group["progress"].assert_against_call(attribute_value=50)


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
def test_assert_specific_call_when_events(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
    position: int,
    lookahead: int,
) -> None:
    """
    Test `assert_against_call` when a matching item arrives.

    Specifically, we drop items onto the queue in sequence, then we
    select an item that we have dropped onto the queue, and we assert
    that it is available. Whether we expect that assertion to pass or
    fail depends on whether it falls within the lookahead that we are
    using.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    :param position: (one-based) position in the queue at which the item
        will appear
    :param lookahead: lookahead setting for the assertion.
    """
    schedule_event(0.1, callback_group["status"], "status", "IN_PROGRESS")
    schedule_event(0.2, callback_group["progress"], "progress", 1)
    schedule_event(0.4, callback_group["progress"], "progress", 2)
    schedule_event(0.6, callback_group["progress"], "progress", 3)
    schedule_event(0.8, callback_group["progress"], "progress", 4)

    if lookahead >= position:
        callback_group["progress"].assert_against_call(
            attribute_value=position, lookahead=lookahead
        )
    else:
        with pytest.raises(
            AssertionError,
            match="Callable has not been called with",
        ):
            callback_group["progress"].assert_against_call(
                attribute_value=position, lookahead=lookahead
            )


def test_assert_against_call_consumes_events(
    callback_group: MockTangoEventCallbackGroup, schedule_event: Callable
) -> None:
    """
    Test that assertions on a callback call consume the call on the group.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["status"], "status", "IN_PROGRESS")

    schedule_event(0.4, callback_group["a"], "a", 1)
    schedule_event(0.5, callback_group["a"], "a", 2)
    schedule_event(0.8, callback_group["a"], "a", 3)

    schedule_event(0.5, callback_group["b"], "b", 4)
    schedule_event(0.5, callback_group["b"], "b", 5)
    schedule_event(0.5, callback_group["b"], "b", 6)

    schedule_event(1.0, callback_group["status"], "status", "COMPLETED")

    callback_group.assert_against_call("status", attribute_value="IN_PROGRESS")

    callback_group["a"].assert_against_call(attribute_value=1)
    callback_group["a"].assert_against_call(attribute_value=2)
    callback_group["a"].assert_against_call(attribute_value=3)
    callback_group["a"].assert_not_called()

    callback_group["b"].assert_against_call(attribute_value=4, lookahead=3)
    callback_group["b"].assert_against_call(attribute_value=5, lookahead=2)
    callback_group["b"].assert_against_call(attribute_value=6)
    callback_group["b"].assert_not_called()

    callback_group.assert_against_call("status", attribute_value="COMPLETED")
    callback_group["status"].assert_not_called()

    callback_group.assert_not_called()
