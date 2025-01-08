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
