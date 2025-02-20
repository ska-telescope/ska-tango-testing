"""Utilities for queries testing."""

from assertpy import assert_that

from ska_tango_testing.integration.event.base import ReceivedEvent
from ska_tango_testing.integration.query.base import (
    EventQuery,
    EventQueryStatus,
)
from ska_tango_testing.integration.query.n_events_match import (
    NEventsMatchQuery,
)


def assert_query_succeeded(query: EventQuery) -> None:
    """Assert an EventQuery succeeded.

    The following assertions are made:

    - the ``succeeded`` method returns True
    - the ``status`` method returns SUCCEEDED

    :param query: The query to check
    """
    assert_that(query.succeeded()).described_as(
        "Query should succeed when an event matches"
    ).is_true()
    assert_that(query.status()).described_as(
        "Query status should be SUCCEEDED when an event matches"
    ).is_equal_to(EventQueryStatus.SUCCEEDED)


def assert_n_events_are_collected(
    query: NEventsMatchQuery, expected_events: list[ReceivedEvent]
) -> None:
    """Assert that the query collected the expected events.

    The following assertions are made:

    - the ``matching_events`` attribute matches the expected events

    :param query: The query to check
    :param expected_events: The expected matching events
    """
    assert_that(query.matching_events).described_as(
        "Query should collect the expected number of events"
    ).is_length(len(expected_events))
    assert_that(query.matching_events).described_as(
        "Query should collect the expected events"
    ).is_equal_to(expected_events)


def assert_n_events_match_query_succeeded(
    query: NEventsMatchQuery,
    matching_events: list[ReceivedEvent] | None = None,
) -> None:
    """Assert a NEventsMatchQuery succeeded and matched the expected events.

    The following assertions are made:

    - the ``succeeded`` method returns True
    - the ``status`` method returns SUCCEEDED
    - if given, the ``matching_events`` attribute matches has
      the expected number of events and matches the expected events

    :param query: The query to check
    :param matching_events: The expected matching events. If None, the
        matching events are not checked.
    """
    assert_query_succeeded(query)

    if matching_events is None:
        return

    assert_n_events_are_collected(query, matching_events)


# -------------------------------------------------------------
# Failed queries assertions


def assert_query_failed(query: EventQuery) -> None:
    """Assert an EventQuery failed.

    The following assertions are made:

    - the ``succeeded`` method returns False
    - the ``status`` method returns FAILED

    :param query: The query to check
    """
    assert_that(query.succeeded()).described_as(
        "Query should fail when no event matches"
    ).is_false()
    assert_that(query.status()).described_as(
        "Query status should be FAILED when no event matches"
    ).is_equal_to(EventQueryStatus.FAILED)


def assert_n_events_match_query_failed(query: NEventsMatchQuery) -> None:
    """Assert a NEventsMatchQuery failed and did not match any events.

    The following assertions are made:

    - the ``succeeded`` method returns False
    - the ``status`` method returns FAILED
    - the ``matching_events`` attribute is empty

    :param query: The query to check
    """
    assert_query_failed(query)
    assert_that(query.matching_events).described_as(
        "Query should not collect any events"
    ).is_empty()


# -------------------------------------------------------------
# Query timeout and durations assertions


def assert_duration_is_close_to_the_expected_value(
    query: EventQuery, expected_duration: float | None, tolerance: float = 0.1
) -> None:
    """Assert that the query duration is close to the expected value.

    :param query: The query to check
    :param expected_duration: The expected duration
    :param tolerance: The tolerance to use for the duration assertion
    """
    if expected_duration is None:
        assert_that(query.evaluation_duration()).described_as(
            "Query duration is expected to not be available for this query"
        ).is_none()
    else:
        assert_that(query.evaluation_duration()).described_as(
            "Query duration is expected to be very close to the "
            f"value of {expected_duration}"
        ).is_close_to(expected_duration, tolerance)


def assert_initial_timeout_is_the_expected_value(
    query: EventQuery, expected_timeout: float, tolerance: float = 0.1
) -> None:
    """Assert that the query initial timeout is close to the expected value.

    :param query: The query to check
    :param expected_timeout: The expected timeout
    :param tolerance: The tolerance to use for the timeout
    """
    assert_that(query.initial_timeout()).described_as(
        "Query initial timeout is expected to be very close to the "
        f"value of {expected_timeout}"
    ).is_close_to(expected_timeout, tolerance)


def assert_query_remaining_timeout_is_close_to_the_expected_value(
    query: EventQuery,
    initial_timeout: float,
    expected_duration: float | None,
    tolerance: float = 0.1,
) -> None:
    """Assert that the query remaining timeout is close to the expected value.

    :param query: The query to check
    :param initial_timeout: The initial timeout
    :param expected_duration: The expected duration
    :param tolerance: The tolerance to use for the remaining timeout assertion

    """
    expected_duration = expected_duration or 0
    expected_remaining_timeout = initial_timeout - expected_duration
    assert_that(query.remaining_timeout()).described_as(
        "Query remaining timeout should be close to the difference "
        "between the initial timeout and the duration: "
        f"{initial_timeout} - {expected_duration} = "
        f"{expected_remaining_timeout}"
    ).is_close_to(expected_remaining_timeout, tolerance)


def assert_timeout_and_duration_consistency(
    query: EventQuery,
    initial_timeout: float,
    expected_duration: float | None,
    tolerance: float = 0.1,
) -> None:
    """Assert the consistency between the query timeout and duration.

    The following assertions are made:

    - the ``timeout`` attribute matches the expected initial timeout
    - the ``duration`` attribute is close to the expected duration
    - the ``remaining_timeout`` attribute is close to the expected
      remaining timeout calculated from the initial timeout and the
      expected duration

    :param query: The query to check
    :param initial_timeout: The initial timeout
    :param expected_duration: The expected duration
    :param tolerance: The tolerance to use for the duration and remaining
        timeout assertions
    """
    assert_initial_timeout_is_the_expected_value(
        query, initial_timeout, tolerance
    )
    assert_duration_is_close_to_the_expected_value(
        query, expected_duration, tolerance
    )
    assert_query_remaining_timeout_is_close_to_the_expected_value(
        query, initial_timeout, expected_duration, tolerance
    )
