"""This module contains tests of the mock callback module."""
from typing import Callable

import numpy
import pytest
import tango

from ska_tango_testing.mock.placeholders import Anything, OneOf
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup


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
    Test that `assert_change_event` fails when the item is produced too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(1.2, callback_group["status"], "status", "QUEUED")

    with pytest.raises(
        AssertionError,
        match="Callable has not been called",
    ):
        callback_group.assert_change_event("status", "QUEUED")


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
def test_assert_change_event_when_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
    position: int,
    lookahead: int,
) -> None:
    """
    Test `assert_change_event` when the callback has been called.

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
        details = callback_group.assert_change_event(
            "progress", position, lookahead=lookahead
        )
        # Let's not bother checking the call_args: it just contains the mock
        # that we used as a fake tango change event.
        assert details["call_kwargs"] == {}
        assert details["attribute_name"] == "progress"
        assert details["attribute_value"] == position
        assert details["attribute_quality"] == tango.AttrQuality.ATTR_VALID
    else:
        with pytest.raises(
            AssertionError,
            match="Callable has not been called with",
        ):
            callback_group.assert_change_event(
                "progress", position, lookahead=lookahead
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


def test_assert_change_event_when_no_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that `assert_change_event` fails when the item is produced too late.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["status"], "status", "IN_PROGRESS")
    schedule_event(1.5, callback_group["progress"], "progress", 50)

    with pytest.raises(
        AssertionError,
        match="Callable has not been called",
    ):
        callback_group["progress"].assert_change_event(50)


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
def test_assert_specific_call_when_events(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
    position: int,
    lookahead: int,
) -> None:
    """
    Test `assert_change_event` when a matching item arrives.

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
        details = callback_group["progress"].assert_change_event(
            position, lookahead=lookahead
        )
        # Let's not bother checking the call_args: it just contains the mock
        # that we used as a fake tango change event.
        assert details["call_kwargs"] == {}
        assert details["attribute_name"] == "progress"
        assert details["attribute_value"] == position
        assert details["attribute_quality"] == tango.AttrQuality.ATTR_VALID

    else:
        with pytest.raises(
            AssertionError,
            match="Callable has not been called with",
        ):
            callback_group["progress"].assert_change_event(
                position, lookahead=lookahead
            )


def test_assert_change_event_consumes_events(
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

    callback_group.assert_change_event("status", "IN_PROGRESS")

    callback_group["a"].assert_change_event(1)
    callback_group["a"].assert_change_event(2)
    callback_group["a"].assert_change_event(3)
    callback_group["a"].assert_not_called()

    callback_group["b"].assert_change_event(4, lookahead=3)
    callback_group["b"].assert_change_event(5, lookahead=2)
    callback_group["b"].assert_change_event(6)
    callback_group["b"].assert_not_called()

    callback_group.assert_change_event("status", "COMPLETED")
    callback_group["status"].assert_not_called()

    callback_group.assert_not_called()


def test_assert_any_change_event_when_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that `assert_change_event` passes when asserted with `Anything`.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["status"], "status", "IN_PROGRESS")
    callback_group["status"].assert_change_event(Anything)


def test_assert_oneof_change_event_when_event(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test that `assert_change_event` passes when a `OneOf` option matches.

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["status"], "status", "IN_PROGRESS")
    callback_group["status"].assert_change_event(
        OneOf("IN_PROGRESS", "COMPLETED")
    )


def test_assert_change_event_with_matching_numpy_array(
    callback_group: MockTangoEventCallbackGroup,
    schedule_event: Callable,
) -> None:
    """
    Test handling of events with numpy arrays.

    Tango events for spectrum and image attributes will be numpy arrays,
    but numpy prevent equality checking between numpy arrays. Therefore
    ska-tango-testing coerces numpy arrays to (nested) lists.

    Here we test that an assertion with a list successfully passes when
    the received event contains a matching subarray/

    :param callback_group: the Tango event callback group under test.
    :param schedule_event: a callable used to schedule a callback call.
    """
    schedule_event(0.2, callback_group["a"], "a", numpy.array([1.0, 2.0]))
    schedule_event(0.2, callback_group["b"], "b", numpy.array([3.0, 4.0]))

    # Test successful match
    callback_group["a"].assert_change_event(
        [pytest.approx(1.0), pytest.approx(2.0)],
    )

    # Test unsuccessful match
    with pytest.raises(
        AssertionError,
        match="Callable has not been called with",
    ):
        callback_group["b"].assert_change_event(
            [pytest.approx(1.0), pytest.approx(1.0)],
        )
