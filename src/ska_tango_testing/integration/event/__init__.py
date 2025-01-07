"""Event-mechanism on the basis of the tracer and the logger.

The basis of the TangoEventTracer and the related logging mechanism
are the capturing, the storing and the reacting to Tango events. In practice,
the tracer and the logging core mechanism are both based on the following
classes and concepts:

- :py:class:`~ska_tango_testing.integration.event.ReceivedEvent` is the base
  class to represent a received event from a Tango device.
- A ReceivedEvent, usually is generated through a subscription to a Tango
  device and attribute; the subscription is managed by a
  :py:class:`~ska_tango_testing.integration.event.TangoSubscriber`.
- Particular kinds of events can be represented by ReceivedEvent subclasses,
  such as :py:class:`~ska_tango_testing.integration.event.TypedEvent`, which
  represents an event where the attribute value is supposed to be read as an
  ``Enum`` value.
- (for the tracer) The events are stored in a
  :py:class:`~ska_tango_testing.integration.event.EventStorage`, which can
  thread-safely store events and notify observers of changes.

"""

from .base import ReceivedEvent
from .storage import EventStorage, EventStorageObserver
from .subscriber import TangoSubscriber
from .typed import EventEnumMapper, TypedEvent

__all__ = [
    "ReceivedEvent",
    "EventEnumMapper",
    "TypedEvent",
    "EventStorage",
    "EventStorageObserver",
    "TangoSubscriber",
]
