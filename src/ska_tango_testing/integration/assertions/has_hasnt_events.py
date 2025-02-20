"""Custom assertions for event-based testing with `assertpy`.

This module provides custom assertions for `assertpy` to be used with
:py:class:`~ska_tango_testing.integration.TangoEventTracer` instances.

Specifically, two assertions are exposed:

- :py:func:`~ska_tango_testing.integration.assertions.has_change_event_occurred`,
  to verify that N or more events matching a given predicate occur
  within a specified timeout.
- :py:func:`~ska_tango_testing.integration.assertions.hasnt_change_event_occurred`,
  to verify that no more than N-1 events matching a given predicate occur
  within a specified timeout.

These assertions access a timeout previously set with the
:py:func:`~ska_tango_testing.integration.assertions.within_timeout` function.

A further utility exposed by this module is the
:py:func:`~ska_tango_testing.integration.assertions.get_context_tracer`
function, which retrieves the `TangoEventTracer` instance from the
`assertpy` context or raises an error if it is not found. It may be
useful for internal purposes.

"""  # pylint: disable=line-too-long # noqa: E501

# pylint: disable=unused-import
from typing import Any, Callable, SupportsFloat

# pylint: disable=unused-import
import tango

from ..event import ReceivedEvent
from ..query import EventQuery, NStateChangesQuery, QueryWithFailCondition
from ..tracer import TangoEventTracer
from .early_stop import get_context_early_stop
from .timeout import ChainedAssertionsTimeout, get_context_timeout

# ------------------------------------------------------------------
# Utility functions


def get_context_tracer(assertpy_context: Any) -> TangoEventTracer:
    """Get the `TangoEventTracer` instance from the `assertpy` context.

    (It is used internally)

    Helper method to get the
    :py:class:`~ska_tango_testing.integration.TangoEventTracer`
    instance from the `assertpy` context which is stored in the 'val'.
    It fails if the instance is not found.

    :param assertpy_context: The `assertpy` context object.

    :return: The `TangoEventTracer` instance.

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the assertion is not called with
        a tracer instance).
    """
    if not hasattr(assertpy_context, "val") or not isinstance(
        assertpy_context.val, TangoEventTracer
    ):
        raise ValueError(
            "The 'TangoEventTracer' instance must be stored in the 'val' "
            "attribute of the assertpy context. Try using the 'assert_that' "
            "method with the 'TangoEventTracer' instance as argument.\n"
            "Example: assert_that(tracer).has_change_event_occurred(...)"
        )
    return assertpy_context.val


def _get_n_events_from_query(query: EventQuery) -> int:
    """Get the number of matching events from the query.

    This method navigates a query structure and extracts - if possible -
    the number of found matching events. This method will raise an error
    if the query (or some other wrapped query) does not have the
    `matching_events` attribute.

    :param query: The query to extract the number of matching events from.
        It can be a simple query or a wrapped query. Somewhere, it must
        have the `matching_events` attribute.
    :return: The number of matching events found in the query.
    :raises ValueError: If the query or some wrapped one
        does not have the `matching_events`
        attribute (i.e., the query structure is not as expected).
    """
    if isinstance(query, QueryWithFailCondition):
        return _get_n_events_from_query(query.wrapped_query)

    if hasattr(query, "matching_events") and isinstance(
        query.matching_events, list
    ):
        return len(query.matching_events)

    raise ValueError(
        "The query structure is not as expected. "
        "It should have the 'matching_events' attribute."
    )


def _early_stop_triggered_failure(query: EventQuery) -> bool:
    """Check if an early stop condition triggered a failure.

    This method navigates a query structure and checks if an early stop
    condition triggered a failure.

    :param query: The query that may or may not have an early stop condition.
    :return: True if an early stop condition triggered a failure. False
        if it didn't or if the query has no early stop condition set.
    """
    # if a query has an early stop condition set, check if it activated
    if isinstance(query, QueryWithFailCondition):
        return query.failed_event is not None

    # the query has no early stop condition set
    return False


def _describe_failure(
    query: EventQuery, tracer: TangoEventTracer, timeout: Any
) -> str:
    """Describe a query failure in detail.

    - describe the failure reason (early stop or conditions not met,
      with and without timeout)
    - list the events captured by the tracer
    - provide the query details

    :param query: The query that failed.
    :param tracer: The tracer instance that captured the events.
    :param timeout: The timeout used for the query.

    :return: A detailed message describing the failure.
    """
    msg = ""
    if _early_stop_triggered_failure(query):
        msg += (
            "FAILURE REASON: An early stop condition was triggered "
            "and so the query failed "
        )
        if isinstance(timeout, ChainedAssertionsTimeout):
            msg += f" {query.remaining_timeout()} seconds before the timeout"
        msg += ".\n\n"
    else:
        msg += "FAILURE REASON: The query condition was not met"
        if isinstance(timeout, ChainedAssertionsTimeout):
            msg += f" within the {timeout.initial_timeout} seconds timeout"
        msg += ".\n\n"

    events_list = "\n".join([str(event) for event in tracer.events])
    msg += f"Events captured by TANGO_TRACER:\n{events_list}"

    msg += "\n\nTANGO_TRACER Query details:\n"
    msg += query.describe()

    return msg


# ------------------------------------------------------------------
# Custom assertions


def has_change_event_occurred(
    assertpy_context: Any,
    device_name: "str | tango.DeviceProxy | None" = None,
    attribute_name: "str | None" = None,
    attribute_value: "Any | None" = None,
    previous_value: "Any | None" = None,
    custom_matcher: "Callable[[ReceivedEvent], bool] | None" = None,
    min_n_events: int = 1,
) -> Any:
    """Verify that an event matching a given predicate occurs.

    Custom `assertpy` assertion to verify that a certain event occurs,
    eventually within a specified timeout. When it fails,
    it provides a detailed error message with the events captured by the
    tracer, the passed parameters and some timing information.

    If you wish, you can also specify a minimum number of events
    that must match the predicate (through the ``min_n_events`` parameter),
    to verify that **at least** a certain number of events occurred [within the
    timeout]. By default, it checks that  **at least one event** matches the
    predicate.

    To describe the event to match, you can pass the following parameters
    (all optional):

    - the name of the device you are interested in
    - the name of the attribute you are interested in
    - the current value of the attribute (the value that the attribute
      has when the event is captured)
    - the previous value of the attribute (the value that the attribute
      had before the event is captured - pretty useful to catch state
      transitions from a value to another)
    - an arbitrary predicate over the event (to deal with tricky cases where
      a simple value comparison is not enough or is not possible)

    Usage example:

    .. code-block:: python

        # (given a subscribed tracer)

        # Check that an attr change from "old_value" to "new_value"
        assert_that(tracer).has_change_event_occurred(
            device_name="devname",
            attribute_name="attrname",
            attribute_value="new_value",
            previous_value="old_value",
        )

        # Just check that there is an event with the value "new_value"
        # (from any device and with any previous value)
        assert_that(tracer).has_change_event_occurred(
            attribute_name="attrname",
            attribute_value="new_value",
        )

        # Add an arbitrary condition
        assert_that(tracer).has_change_event_occurred(
            attribute_name="other_attrname",
            custom_matcher=lambda e: e.attribute_value > 5,
        )

        # Perform the same check, but look for AT LEAST 3 matching events.
        assert_that(tracer).has_change_event_occurred(
            attribute_name="attrname",
            attribute_value="new_value",
            min_n_events=3,
        )

    :param assertpy_context: The `assertpy` context object
        (It is passed automatically)
    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.
    :param previous_value: The previous value to match. If not provided,
        it will match any previous value.
    :param custom_matcher: An arbitrary predicate over the event. It is
        essentially a function or a lambda that takes an event and returns
        ``True`` if it satisfies your condition. NOTE: it is put in ``and``
        with the other specified parameters.
    :param min_n_events: The minimum number of events to match for the
        assertion to pass; verifies that at least n events have occurred.
        If not provided, it defaults to 1. If used without a timeout, the
        assertion will only check events received up to the time of calling.
        If specified, it must be a positive integer >= 1.

    :return: The `assertpy` context object.

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the method is called outside
        an ``assert_that(tracer)`` context).
    """  # noqa: DAR402
    # pylint: disable=too-many-arguments

    # check assertpy_context has a tracer object
    tracer = get_context_tracer(assertpy_context)

    # get the remaining timeout if it exists
    timeout: SupportsFloat = get_context_timeout(assertpy_context)

    # Create a query
    query: EventQuery = NStateChangesQuery(
        device_name=device_name,
        attribute_name=attribute_name,
        attribute_value=attribute_value,
        previous_value=previous_value,
        custom_matcher=custom_matcher,
        target_n_events=min_n_events,
        timeout=timeout,
    )

    # if given, wrap the query with the early stop condition
    early_stop_predicate = get_context_early_stop(assertpy_context)
    if early_stop_predicate is not None:
        query = QueryWithFailCondition(
            wrapped_query=query, stop_condition=early_stop_predicate
        )

    tracer.evaluate_query(query)

    # if not enough events are found, raise an error
    if not query.succeeded():
        msg = (
            f"Expected to find {min_n_events} event(s) "
            + "matching the predicate"
        )
        if isinstance(timeout, ChainedAssertionsTimeout):
            msg += f" within {timeout.initial_timeout} seconds"
        else:
            msg += " in already existing events"
        msg += f", but only {_get_n_events_from_query(query)} found.\n"

        msg += _describe_failure(query, tracer, timeout)

        return assertpy_context.error(msg)

    return assertpy_context


def hasnt_change_event_occurred(
    assertpy_context: Any,
    device_name: "str | tango.DeviceProxy | None" = None,
    attribute_name: "str | None" = None,
    attribute_value: "Any | None" = None,
    previous_value: "Any | None" = None,
    custom_matcher: "Callable[[ReceivedEvent], bool] | None" = None,
    max_n_events: int = 1,
) -> Any:  # pylint: disable=duplicate-code
    """Verify that an event matching a given predicate does not occur.

    It is the opposite of :py:func:`has_change_event_occurred`. It verifies
    that no event(s) matching the given conditions occurs, eventually within a
    specified timeout. When it fails, it provides a detailed
    error message with the events captured by the tracer,
    the passed parameters and some timing information.

    If you wish, you can also specify a maximum number of events
    that must match the predicate (through the ``max_n_events`` parameter),
    to verify that **no more than** a certain number of events occurred
    [within the timeout]. By default, it checks that
    **no more than one event** matches the predicate.

    The parameters are the same as :py:func:`has_change_event_occurred`.

    Usage example:

    .. code-block:: python

        # (given a subscribed tracer)

        # Check that none of the captured events has the value "ERROR"
        assert_that(tracer).hasnt_change_event_occurred(
            attribute_value="ERROR",
        )


    :param assertpy_context: The assertpy context object
        (It is passed automatically)
    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.
    :param previous_value: The previous value to match. If not provided,
        it will match any previous value.
    :param custom_matcher: An arbitrary predicate over the event. It is
        essentially a function or a lambda that takes an event and returns
        ``True`` if it satisfies your condition. NOTE: it is put in ``and``
        with the other specified parameters.
    :param max_n_events: The maximum number of events to match before the
        assertion fails; verifies that no more than n-1 events have occurred.
        If not provided, it defaults to 1. If used without a timeout, the
        assertion will only check events received up to the time of calling.
        If specified, it must be a positive integer >= 1.

    :return: The assertpy context object.

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the method is called outside
        an ``assert_that(tracer)`` context).
    """  # noqa: DAR402
    # pylint: disable=too-many-arguments

    # check assertpy_context has a tracer object
    tracer = get_context_tracer(assertpy_context)

    # get the remaining timeout if it exists
    timeout: SupportsFloat = get_context_timeout(assertpy_context)

    # Create and evaluate the query
    query: EventQuery = NStateChangesQuery(
        device_name=device_name,
        attribute_name=attribute_name,
        attribute_value=attribute_value,
        previous_value=previous_value,
        custom_matcher=custom_matcher,
        target_n_events=max_n_events,
        timeout=timeout,
    )

    # if given, wrap the query with the early stop condition
    early_stop_predicate = get_context_early_stop(assertpy_context)
    if early_stop_predicate is not None:
        query = QueryWithFailCondition(
            wrapped_query=query, stop_condition=early_stop_predicate
        )

    tracer.evaluate_query(query)

    # TODO: better messaging in case of early stop

    # if enough events are found (or an early stop is triggered),
    # raise an error
    if query.succeeded() or _early_stop_triggered_failure(query):
        msg = (
            f"Expected to NOT find {max_n_events} event(s) "
            + "matching the predicate"
        )
        if isinstance(timeout, ChainedAssertionsTimeout):
            msg += f" within {timeout.initial_timeout} seconds"
        else:
            msg += " in already existing events"
        msg += f", but {_get_n_events_from_query(query)} were found."

        msg += _describe_failure(query, tracer, timeout)

        msg += (
            "NOTE: the query looks for N={max_n_events} events, "
            "but in this case you were expecting less!"
        )

        assertpy_context.error(msg)

    return assertpy_context
