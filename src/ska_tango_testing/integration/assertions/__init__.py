"""Basic custom event-based assertions for `TangoEventTracer`.

This module provides some basic custom
`assertpy <https://assertpy.github.io/index.html>`_ assertions
to be used with :py:class:`~ska_tango_testing.integration.TangoEventTracer`
instances to assert that certain events have occurred or not occurred.

Essentially assertions are query calls to the tracer, within
a timeout, to check if there are events which match an expected more or less
complex predicate, which include:

- specifics about the source of the event (device name and attribute name);
- specifics about the event value (e.g., the event value is 5);
- specifics about the event value change (e.g., the event value changes from
  "old_value" to "new_value");
- specifics about how many events with certain characteristics
  you expect to have occurred;
- further custom matching rules;
- a way to define a timeout and share it between all the successive assertions
  (i.e., verify that multiple conditions are met within the same timeout).

Assertions are designed to be used in a chain (in a classic *assertpy* style),
where each assertion is called after the previous one,
and the timeout is shared between all
them. At the moment, the main assertions you can use are:

- :py:func:`~ska_tango_testing.integration.assertions.has_change_event_occurred`,
  which asserts that one or more events have occurred (within a timeout);
- :py:func:`~ska_tango_testing.integration.assertions.hasnt_change_event_occurred`,
  which is the negation of the previous one and so asserts that no events
  occurs within a timeout;
- :py:func:`~ska_tango_testing.integration.assertions.within_timeout`,
  which is the way you have to set a timeout for the next chain of assertions.

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

If you feel those assertions aren't enough for your test cases, you can
create your own custom assertions. The assertions provided here may serve
as examples. If you are willing to create your own assertions, we
suggest:

- to give a look to all the support function and classes we provide
  in this module (in particular, to
  :py:class:`~ska_tango_testing.integration.assertions.ChainedAssertionsTimeout`,
  :py:func:`~ska_tango_testing.integration.assertions.get_context_timeout` and
  :py:func:`~ska_tango_testing.integration.assertions.get_context_tracer`);
- to inform yourself well about the internal mechanisms of the
  :py:class:`~ska_tango_testing.integration.TangoEventTracer` class (we suggest
  to read the class documentation and the following modules:
  :py:mod:`ska_tango_testing.integration.event` to understand how the tracer
  captures events and :py:mod:`ska_tango_testing.integration.query` to
  understand how those events can be queried and evaluated);
- to read the `assertpy` documentation to understand how to create and export
  custom assertions (https://assertpy.github.io/docs.html).

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
as a way to compare events. it's important to remember that we are dealing with
a distributed system and the reception time may be misleading in some
cases (e.g., the reception time of the event may not be the same as the
time the event was generated by the device).
We noticed that in :py:class:`tango.EventData` there is a timestamp
which tells when the Tango server received the event. Maybe in the future
it would be better to use that instead of the reception time as a way to
compare events (if it comes from a centralized server and not from the
device itself, because it is important to remember that in distributed
systems the devices' clocks may not be perfectly synchronized).
"""  # pylint: disable=line-too-long # noqa: E501

from .has_hasnt_events import (
    get_context_tracer,
    has_change_event_occurred,
    hasnt_change_event_occurred,
)
from .timeout import (
    ChainedAssertionsTimeout,
    get_context_timeout,
    within_timeout,
)
from .early_stop import with_early_stop, get_context_early_stop

__all__ = [
    "has_change_event_occurred",
    "hasnt_change_event_occurred",
    "within_timeout",
    "with_early_stop",
    "ChainedAssertionsTimeout",
    "get_context_timeout",
    "get_context_tracer",
    "get_context_early_stop",
]
