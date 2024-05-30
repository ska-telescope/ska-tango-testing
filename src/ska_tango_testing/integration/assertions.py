"""Basic custom event-based assertions for `TangoEventTracer`.

This module provides some example of basic custom
`assertpy <https://assertpy.github.io/index.html>`_ assertions
to be used with :py:class:`~ska_tango_testing.integration.TangoEventTracer`
instances. These assertions can be
used to verify properties about the events captured by the tracer.

Essentially they are query calls to the tracer, within
a timeout, to check if the are events which match an expected more or less
complex predicate.

Usage example:

.. code-block:: python

    from assertpy import assert_that, add_extension
    from ska_tango_testing.integration import (
        TangoEventTracer
    )
    from ska_tango_testing.integration.assertions (
        has_change_event_occurred,
        within_timeout,
    )

    def test_event_occurs_within_timeout(sut, tracer: TangoEventTracer):

        # subscribe to the events
        tracer.subscribe_event("devname", "attrname")
        tracer.subscribe_event("devname", "attr2")

        # ... do something that triggers the event

        # Check that a generic event has occurred
        assert_that(tracer).has_change_event_occurred(
            device_name="devname",
            attribute_name="attrname",
            attribute_value=5,
        )

        # Check that an attr change from "old_value" to "new_value"
        # has occurred or will occur within 5 seconds in any device.
        # Describe the eventual failure with an evocative message.
        assert_that(tracer).described_as(
            "An event from 'old_value' to 'new_value' for 'attr2' should have"
            " been occurred within 5 seconds in some device."
        ).within_timeout(5).has_change_event_occurred(
            # (if I don't care about the device name, ANY will match)
            attribute_name="attr2",
            attribute_value="new_value",
            previous_value="old_value",
        )

You can and you are encouraged to take those assertions as a starting point
to create more complex ones, as needed by your test cases. If you want to do
that it is suggested to check `assertpy` documentation to understand
how to create custom assertions (https://assertpy.github.io/docs.html).


**NOTE**: Custom assertions of this module are already exported
to the `assertpy` context in :py:mod:`ska_tango_testing.integration`, so
if you are an end-user, if you import the module somewhere in your tests
you already have access to the assertions. Sometimes your IDE may not
recognize the custom assertions, but they are there.

**ANOTHER NOTE**: To make assertions about the events order
- i.e., assertion which include a verification with the shape
"event1 happens before event2", like when you use `previous_value` - we
are currently using the reception time
(:py:attr:`~ska_tango_testing.integration.event.ReceivedEvent.reception_time`)
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
"""  # pylint: disable=line-too-long

from datetime import datetime
from typing import Any, Optional, Union

import tango

from .predicates import ANY, event_has_previous_value, event_matches_parameters
from .tracer import TangoEventTracer

# TODO: It would be nice to type those functions with the right
# assertpy types, but it is not clear how to do that yet.


def _get_tracer(self: Any) -> TangoEventTracer:
    """Get the `TangoEventTracer` instance from the `assertpy` context.

    Helper method to get the
    :py:class:`~ska_tango_testing.integration.TangoEventTracer`
    instance from the `assertpy` context which is stored in the 'val'.
    It fails if the instance is not found.

    :param self: The `assertpy` context object.

    :return: The `TangoEventTracer` instance.

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the assertion is not called with
        a tracer instance).
    """
    if not hasattr(self, "val") or not isinstance(self.val, TangoEventTracer):
        raise ValueError(
            "The 'TangoEventTracer' instance must be stored in the 'val' "
            "attribute of the assertpy context. Try using the 'assert_that' "
            "method with the 'TangoEventTracer' instance as argument.\n"
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

    :py:class:`~ska_tango_testing.integration.TangoEventTracer`
    allows to query events within a timeout. In other words, you can
    make assertions about events that will occur in the future within
    a certain time frame and "await" for them (if they didn't occur yet).
    This method when called inside an assertion context permits
    you to specify that timeout.

    Usage example:

    .. code-block:: python

        # (given a subscribed tracer)

        # non-blocking long operation that triggers an event at the end
        sut.long_operation_that_triggers_an_event()

        # Check that the operation is done within 30 seconds
        assert_that(tracer).within_timeout(30).has_change_event_occurred(
            attribute_name="operation_state",
            attribute_value="DONE",
        )

    **NOTE**: Using a (small) timeout is a good practice even in not so long
    operations, because it makes the test more robust and less prone to
    flakiness and false positives.

    .. code-block:: python

        # (given a subscribed tracer)

        # non-blocking long operation that triggers an event at the end
        sut.quick_operation()

        # Check that the operation is done within 5 seconds
        assert_that(tracer).within_timeout(5).has_change_event_occurred(
            attribute_name="operation_state",
            attribute_value="DONE",
        )

    :param self: The `assertpy` context object (It is passed automatically)
    :param timeout: The time in seconds to wait for the event to occur.

    :return: The decorated assertion context.

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the method is called outside
        an ``assert_that(tracer)`` context).
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

    Custom `assertpy` assertion to verify that an event matching a given
    predicate occurs, eventually within a specified timeout. When it fails,
    it provides a detailed error message with the events captured by the
    tracer, the passed parameters and some timing information.

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

    :param self: The `assertpy` context object (It is passed automatically)
    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.
    :param previous_value: The previous value to match. If not provided,
        it will match any previous value.

    :return: The `assertpy` context object.

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the method is called outside
        an ``assert_that(tracer)`` context).
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


def hasnt_change_event_occurred(
    self: Any,
    device_name: Optional[str] = ANY,
    attribute_name: Optional[str] = ANY,
    attribute_value: Optional[Any] = ANY,
    previous_value: Optional[Any] = ANY,
) -> Any:
    """Verify that an event matching a given predicate does not occur.

    It is the opposite of :py:func:`has_change_event_occurred`. It verifies
    that no event matching the given predicate occurs, eventually within a
    specified timeout. When it fails,
    it provides a detailed error message with the events captured by the
    tracer, the passed parameters and some timing information.

    Usage example:

    .. code-block:: python

        # (given a subscribed tracer)

        # Check that none of the captured events has the value "ERROR"
        assert_that(tracer).hasnt_change_event_occurred(
            attribute_value="ERROR",
        )


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

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the method is called outside
        an ``assert_that(tracer)`` context).
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
        msg = "Expected to NOT find an event matching the predicate"
        if getattr(self, "event_timeout", None) is not None:
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
