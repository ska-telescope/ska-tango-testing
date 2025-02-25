"""Predicates to filter `TangoEventTracer` events in queries.

**WARNING**: This module is deprecated and will be removed in future.
It is replaced by queries objects, which are able to print by
themselves their details; see
:py:mod:`~ska_tango_testing.integration.query` module.

A collection of predicates to filter
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent`
instances when calling the
:py:meth:`ska_tango_testing.integration.TangoEventTracer.query_events`
method. The main purpose of these predicates is to allow the user to compose
complex queries to filter events based on their attributes but also on their
position in the event sequence.

If you are an end-user of this module, you will probably not need to
write or use these predicates directly. Instead, you will use the custom
`assertpy <https://assertpy.github.io/index.html>`_ assertions (see
:py:mod:`ska_tango_testing.integration.assertions`). If
you wish to write custom predicates we still recommend to check the custom
code for usage examples.

**WARNING**: This module is deprecated and will be removed in future.
It is replaced by queries objects, which are able to print by
themselves their details; see
:py:mod:`~ska_tango_testing.integration.query`.
"""
from typing import Any

import deprecation  # type: ignore
import tango  # pylint: disable=unused-import

from .event import ReceivedEvent
from .tracer import TangoEventTracer

ANY_VALUE = None


@deprecation.deprecated(
    deprecated_in="0.8.0",
    details="This method is deprecated and will likely be removed in future. "
    "It is replaced by queries objects, which are able to print by "
    "themselves their details; see "
    "`ska_tango_testing.integration.query`.",
)
def event_matches_parameters(
    target_event: ReceivedEvent,
    device_name: "str | tango.DeviceProxy | None" = ANY_VALUE,
    attribute_name: str | None = ANY_VALUE,
    attribute_value: Any | None = ANY_VALUE,
) -> bool:
    """Check if an event matches the provided criteria.

    If a criterion is not given (``ANY_VALUE``), the predicate will always
    return True (only the given and not ``None`` criteria will be checked).

    **WARNING**: This method is deprecated and will be removed in future.
    It is replaced by queries objects, which are able to print by
    themselves their details; see
    :py:mod:`~ska_tango_testing.integration.query`.

    :param target_event: The event to check.
    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.

    :return: True if the event matches the provided criteria, False otherwise.
    """
    # if provided, check if device name matches the criteria
    # (else any device name will match)
    if device_name is not ANY_VALUE and not target_event.has_device(
        device_name
    ):
        return False

    # if provided, check if attribute name matches the criteria
    # (else any attribute name will match)
    if attribute_name is not ANY_VALUE and not target_event.has_attribute(
        attribute_name
    ):
        return False

    # if provided, check if attribute value matches the criteria
    # (else any attribute value will match)
    if (
        attribute_value is not ANY_VALUE
        and not target_event.attribute_value == attribute_value
    ):
        return False

    # if you reach this point, all (provided) criteria match
    return True


@deprecation.deprecated(
    deprecated_in="0.8.0",
    details="This method is deprecated and will likely be removed in future. "
    "It is replaced by queries objects, which are able to print by "
    "themselves their details; see "
    "`ska_tango_testing.integration.query`.",
)
def event_has_previous_value(
    target_event: ReceivedEvent, tracer: TangoEventTracer, previous_value: Any
) -> bool:
    """Check if an event has a specific previous value.

    This predicate can be used to match events based on the value they had
    before the current one. It is useful to check if an event was triggered
    by a specific value change. If the event has no previous value, it will
    return False.

    **WARNING**: This method is deprecated and will be removed in future.
    It is replaced by queries objects, which are able to print by
    themselves their details; see
    :py:mod:`~ska_tango_testing.integration.query`.

    :param target_event: The event to check.
    :param tracer: The event tracer containing the events.
    :param previous_value: The value to match.

    :return: True if the event has the provided previous value, False
        if the event has no previous value or if the previous value does
        not match.
    """
    previous_event = None

    # If any, get the previous event for the same device and attribute
    # than the current event

    for evt in tracer.events:
        if (
            # the event is from the same device and attribute
            # and is previous to the target event
            evt.has_device(target_event.device_name)
            and evt.has_attribute(target_event.attribute_name)
            and evt.reception_time < target_event.reception_time
        ):
            if (
                # if no previous event was found or the current one
                # is more recent than the previous one
                previous_event is None
                or evt.reception_time > previous_event.reception_time
            ):
                previous_event = evt

    # If no previous event was found, return False (there is no event
    # before the target one, so none with the expected previous value)
    if previous_event is None:
        return False

    # If the previous event was found, check if previous value matches
    return previous_event.attribute_value == previous_value
