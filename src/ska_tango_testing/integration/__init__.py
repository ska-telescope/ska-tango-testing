"""A set of utility tools for integration testing of SKA Tango devices.

This module provides a set of utility tools for integration testing
of SKA Tango devices. In particular, it provides tools to subscribe to
events, query them (within a timeout), log them in real-time, and build
complex queries and assertions to verify the behaviour of a complex
set of devices.

The three main classes provided by this module are:

- A class :py:class:`TangoEventTracer` that can be used to subscribe to
    events from a Tango device and then query them for making assertions.
- A class :py:class:`TangoEventLogger` that can be used to subscribe to
    events from a Tango device and then live log them for debugging purposes.
- A class :py:class:`ReceivedEvent` that wraps
    :py:class:`tango.EventData` and represents an event received by the
    :py:class:`TangoEventTracer` or the :py:class:`TangoEventLogger`.
    It is useful to access quickly the event data and to build predicates
    for the queries.

Other than those three main classes, this module provides a set of predicates
(:py:mod:`ska_tango_testing.integration.tango_event_tracer_predicates`)
that can be used to filter events when calling the
:py:meth:`TangoEventTracer.query_events` method (e.g.,
"select all events from device X with attribute Y that have a certain value
and a certain previous value"), but also some high-level custom
`assertpy` assertions to make it easier to write tests
using :py:class:`TangoEventTracer`
(:py:mod:`ska_tango_testing.integration.tango_event_tracer_predicates`).

If you are an end-user of this module, you will probably use the tracer
toghether with the custom assertions. See
:py:mod:`ska_tango_testing.integration.tango_event_tracer_predicates`
for more details and usage examples.
"""

from .received_event import ReceivedEvent
from .tango_event_logger import (
    DEFAULT_LOG_ALL_EVENTS,
    DEFAULT_LOG_MESSAGE_BUILDER,
    TangoEventLogger,
)
from .tango_event_tracer import TangoEventTracer

__all__ = [
    "TangoEventTracer",
    "TangoEventLogger",
    "ReceivedEvent",
    "DEFAULT_LOG_ALL_EVENTS",
    "DEFAULT_LOG_MESSAGE_BUILDER",
]
