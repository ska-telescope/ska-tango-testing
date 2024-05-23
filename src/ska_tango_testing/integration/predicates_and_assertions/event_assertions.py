"""Basic custom event-based assertions for :py:class:`TangoEventTracer`.

This module provides some example of basic custom :py:mod:`assertpy` assertions
to be used with :py:class:`TangoEventTracer` instances. These assertions can be
used to verify properties about the events captured by the tracer.

Essentially they are query calls to the tracer, within
a timeout, to check if the are events which match an expected more or less
complex predicate.

You can and you are encouraged to take those assertions as a starting point
to create more complex ones, as needed by your test cases. If you want to do
that it is suggested to check :py:mod:`assertpy` documentation to understand
how to create custom assertions (https://assertpy.github.io/docs.html).

Usage example:

.. code-block:: python

    from assertpy import assert_that, add_extension
    from ska_tango_testing.integration.tango_event_tracer import (
        TangoEventTracer
    )
    from ska_tango_testing.integration.\
        predicates_and_assertions.event_assertions import (
        exists_event
    )

    # ...

    def test_event_occurs_within_timeout(sut, tracer: TangoEventTracer):

        tracer.subscribe_event("devname", "attrname")

        # ... do something that triggers the event

        # Check that an attr change event happens within 10 seconds
        assert_that(tracer).has_change_event_occurred(
            device_name="devname",
            attribute_name="attrname",
            attribute_value="new_value",
            previous_value="old_value",
            timeout=10
        )

NOTE: Just an important note. To make assertions about the events order
- i.e., assertion which include a verification with the shape
"event1 happens before event2" (:py:func:`exists_event` with
:py:param:`previous_value` set to a specific value is an example) - we
are currently using the reception time
(:py:attr:`ReceivedEvent.reception_time`)
as a way to compare events. It's important to remind we are dealing with
a distributed system and the reception time may be misleading in some
cases (e.g., the reception time of the event may not be the same as the
time the event was generated by the device).

We noticed that in :py:class:`tango.EventData` there is a timestamp
which tells when the Tango server received the event. Maybe in the future
it would be better to use that instead of the reception time as a way to
compare events (if it comes from a centralized server and not from the
device itself, because it is important to remember that in distributed
systems the devices clocks may not be perfectly synchronized).
"""

from datetime import datetime
from typing import Any, Optional, Union

import tango

from ..tango_event_tracer import TangoEventTracer
from .predicates import ANY, event_has_previous_value, event_matches_parameters

# TODO: It would be nice to type those functions with the right
# assertpy types, but it is not clear how to do that yet.


def _get_tracer(self: Any) -> TangoEventTracer:
    """Get the :py:class:`TangoEventTracer` instance from the assertpy context.

    Helper method to get the :py:class:`TangoEventTracer` instance from the
    assertpy context or raise an error if it is not found.

    :param self: The assertpy context object.

    :return: The :py:class:`TangoEventTracer` instance.

    :raises ValueError: If the :py:class:`TangoEventTracer` instance is not
        found (i.e., the assertion is not called with a tracer instance).
    """
    if not hasattr(self, "val") or not isinstance(self.val, TangoEventTracer):
        raise ValueError(
            "The TangoEventTracer instance must be stored in the 'val' "
            "attribute of the assertpy context. Try using the 'assert_that' "
            "method with the TangoEventTracer instance as argument.\n"
            "Example: assert_that(tracer).has_change_event_occurred(...)"
        )
    return self.val


def _print_passed_event_args(
    device_name: Optional[str] = ANY,
    attribute_name: Optional[str] = ANY,
    attribute_value: Optional[Any] = ANY,
    previous_value: Optional[Any] = ANY,
) -> str:
    """Print the arguments passed to the event query.

    Helper method to print the arguments passed to the event query in a
    human-readable format.

    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.
    :param previous_value: The previous value to match. If not provided,
        it will match any previous value.

    :return: The string representation of the passed arguments.
    """
    res = ""
    if device_name is not ANY:
        res += f"device_name='{device_name}', "
    if attribute_name is not ANY:
        res += f"attribute_name='{attribute_name}', "
    if attribute_value is not ANY:
        res += f"attribute_value={attribute_value}, "
    if previous_value is not ANY:
        res += f"previous_value={previous_value}, "

    return res


def within_timeout(self: Any, timeout: Union[int, float]) -> Any:
    """Add a timeout to an event-based assertion function.

    A timeout is a maximum wait time in seconds for the event to occur
    from the moment the assertion is called. If the event will not occur
    within this time, the assertion will fail. If no timeout is provided,
    the assertion will consieder only already existing events
    (i.e., there will be no waiting)

    :param self: The assertpy context object (It is passed automatically)
    :param timeout: The time in seconds to wait for the event to occur.

    :return: The decorated assertion context.

    :raises ValueError: If the :py:class:`TangoEventTracer` instance is not
        found (i.e., the assertion is not called with a tracer instance).
    """  # noqa: DAR402
    # verify the tracer is stored in the assertpy context or raise an error
    _get_tracer(self)

    # add the timeout to the assertion
    self.event_timeout = timeout

    return self


def has_change_event_occurred(
    self: Any,
    device_name: Optional[str] = ANY,
    attribute_name: Optional[str] = ANY,
    attribute_value: Optional[Any] = ANY,
    previous_value: Optional[Any] = ANY,
) -> Any:
    """Verify that an event matching a given predicate occurs.

    Custom assertpy assertion to verify that an event matching a given
    predicate occurs, eventually within a specified timeout.

    :param self: The assertpy context object (It is passed automatically)
    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.
    :param previous_value: The previous value to match. If not provided,
        it will match any previous value.

    :return: The assertpy context object.

    :raises ValueError: If the :py:class:`TangoEventTracer` instance is not
        found (i.e., the method is called outside an 'assert_that(tracer)'
        context).
    """  # noqa: DAR402
    # check self has a tracer object
    tracer = _get_tracer(self)

    # quick trick: if device_name is a device proxy, get the name
    if isinstance(device_name, tango.DeviceProxy):
        device_name = device_name.dev_name()

    # start time is needed in case of error
    run_query_time = datetime.now()

    # query and check if any event matches the predicate
    result = tracer.query_events(
        lambda e:
        # the event match passed values
        event_matches_parameters(
            target_event=e,
            device_name=device_name,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
        )
        and (
            # if given a previous value, the event must have a previous
            # event and tue previous value must match
            event_has_previous_value(
                target_event=e, tracer=tracer, previous_value=previous_value
            )
            if previous_value is not ANY
            else True
        ),
        # if given use the timeout, else None
        timeout=getattr(self, "event_timeout", None),
    )

    # if no event is found, raise an error
    if len(result) == 0:
        event_list = "\n".join([str(event) for event in tracer.events])
        msg = "Expected to find an event matching the predicate"
        if hasattr(self, "event_timeout"):
            msg += f" within {self.event_timeout} seconds"
        else:
            msg += " in already existing events"
        msg += ", but none was found.\n\n"
        msg += f"Events captured by TANGO_TRACER:\n{event_list}"
        msg += "\n\nTANGO_TRACER Query arguments: "
        msg += _print_passed_event_args(
            device_name, attribute_name, attribute_value, previous_value
        )
        msg += "\nQuery start time: " + str(run_query_time)
        msg += "\nQuery end time: " + str(datetime.now())

        return self.error(msg)

    return self


def not_exists_event(
    self: Any,
    device_name: Optional[str] = ANY,
    attribute_name: Optional[str] = ANY,
    attribute_value: Optional[Any] = ANY,
    previous_value: Optional[Any] = ANY,
) -> Any:
    """Verify that an event matching a given predicate does not occur.

    Custom assertpy assertion to verify that an event matching a given
    predicate does not occur, eventually within a specified timeout.

    :param self: The assertpy context object (It is passed automatically)
    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.
    :param previous_value: The previous value to match. If not provided,
        it will match any previous value.

    :return: The assertpy context object.

    :raises ValueError: If the :py:class:`TangoEventTracer` instance is not
        found (i.e., the method is called outside an 'assert_that(tracer)'
        context).
    """  # noqa: DAR402
    # check self has a tracer object
    tracer = _get_tracer(self)

    # quick trick: if device_name is a device proxy, get the name
    if isinstance(device_name, tango.DeviceProxy):
        device_name = device_name.dev_name()

    # start time is needed in case of error
    run_query_time = datetime.now()

    # query and check if any event matches the predicate
    result = tracer.query_events(
        lambda e:
        # the event match passed values
        event_matches_parameters(
            target_event=e,
            device_name=device_name,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
        )
        and (
            # if given a previous value, the event must have a previous
            # event and tue previous value must match
            event_has_previous_value(
                target_event=e, tracer=tracer, previous_value=previous_value
            )
            if previous_value is not ANY
            else True
        ),
        # if given use the timeout, else None
        timeout=getattr(self, "event_timeout", None),
    )

    # if any event is found, raise an error
    if len(result) > 0:
        event_list = "\n".join([str(event) for event in tracer.events])
        msg = "Expected to not find an event matching the predicate"
        if self.event_timeout is not None:
            msg += f" within {self.event_timeout} seconds"
        else:
            msg += " in already existing events"
        msg += ", but some were found."
        msg += f"Events captured by TANGO_TRACER:\n{event_list}"
        msg += "\n\nTANGO_TRACER Query arguments: "
        msg += _print_passed_event_args(
            device_name, attribute_name, attribute_value, previous_value
        )
        msg += "\nQuery start time: " + str(run_query_time)
        msg += "\nQuery end time: " + str(datetime.now())
        msg += "\n\nEvents that matched the predicate:\n"
        msg += "\n".join([str(event) for event in result])

        self.error(msg)

    return self
