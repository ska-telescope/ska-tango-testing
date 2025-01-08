# pylint: disable=duplicate-code

"""Custom assertions for event-based testing with `assertpy`.

This module provides custom assertions for `assertpy` to be used with
:py:class:`~ska_tango_testing.integration.TangoEventTracer` instances.

Concretely, there are exposed two assertions:

- :py:func:`~ska_tango_testing.integration.assertions.has_change_event_occurred`,
  to verify that N or more events matching a given predicate occur
  within a specified timeout.
- :py:func:`~ska_tango_testing.integration.assertions.hasnt_change_event_occurred`,
  to verify that no more than N-1 events matching a given predicate occur
  within a specified timeout.

These assertions access a timeout previously set with the
:py:func:`~ska_tango_testing.integration.assertions.within_timeout` function.

"""  # pylint: disable=line-too-long # noqa: E501


from typing import Any, Callable

# pylint: disable=unused-import
import tango

from ..event import ReceivedEvent
from ..query import NStateChangesQuery
from ..tracer import TangoEventTracer
from .timeout import ChainedAssertionsTimeout


def _get_tracer(assertpy_context: Any) -> TangoEventTracer:
    """Get the `TangoEventTracer` instance from the `assertpy` context.

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


def has_change_event_occurred(
    assertpy_context: Any,
    device_name: "str | tango.DeviceProxy | None" = None,
    attribute_name: str | None = None,
    attribute_value: Any | None = None,
    previous_value: Any | None = None,
    custom_matcher: Callable[[ReceivedEvent], bool] | None = None,
    min_n_events: int = 1,
) -> Any:  # pylint: disable=duplicate-code
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
    - an arbitrary predicate over the event (to deal tricky cases where
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
    tracer = _get_tracer(assertpy_context)

    # get the remaining timeout if it exists
    timeout: ChainedAssertionsTimeout | float = getattr(
        assertpy_context, "event_timeout", 0.0
    )

    # Create and evaluate the query with a tracer
    query = NStateChangesQuery(
        device_name=device_name,
        attribute_name=attribute_name,
        attribute_value=attribute_value,
        previous_value=previous_value,
        custom_matcher=custom_matcher,
        target_n_events=min_n_events,
        timeout=timeout,
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
        msg += f", but only {len(query.matching_events)} found.\n\n"

        events_list = "\n".join([str(event) for event in tracer.events])
        msg += f"Events captured by TANGO_TRACER:\n{events_list}"

        msg += "\n\nTANGO_TRACER Query details:\n"
        msg += query.describe()

        return assertpy_context.error(msg)

    return assertpy_context


def hasnt_change_event_occurred(
    assertpy_context: Any,
    device_name: "str | tango.DeviceProxy | None" = None,
    attribute_name: str | None = None,
    attribute_value: Any | None = None,
    previous_value: Any | None = None,
    custom_matcher: Callable[[ReceivedEvent], bool] | None = None,
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
    tracer = _get_tracer(assertpy_context)

    # get the remaining timeout if it exists
    timeout: ChainedAssertionsTimeout | float = getattr(
        assertpy_context, "event_timeout", 0.0
    )

    # Create and evaluate the query
    query = NStateChangesQuery(
        device_name=device_name,
        attribute_name=attribute_name,
        attribute_value=attribute_value,
        previous_value=previous_value,
        custom_matcher=custom_matcher,
        target_n_events=max_n_events,
        timeout=timeout,
    )
    tracer.evaluate_query(query)

    # if enough events are found, raise an error
    if query.succeeded():
        msg = (
            f"Expected to NOT find {max_n_events} event(s) "
            + "matching the predicate"
        )
        if isinstance(timeout, ChainedAssertionsTimeout):
            msg += f" within {timeout.initial_timeout} seconds"
        else:
            msg += " in already existing events"
        msg += f", but {len(query.matching_events)} were found."

        event_list = "\n".join([str(event) for event in tracer.events])
        msg += f"Events captured by TANGO_TRACER:\n{event_list}"

        msg += "\n\nTANGO_TRACER Query details:\n"
        msg += query.describe()

        msg += "NOTE: the query looks for N events, but in this case, "
        msg += "you are expecting to find none."

        assertpy_context.error(msg)

    return assertpy_context
