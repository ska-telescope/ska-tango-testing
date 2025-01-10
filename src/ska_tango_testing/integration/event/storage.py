"""Thread-safe storage for Tango events."""

import threading
from typing import Protocol

from .base import ReceivedEvent


# pylint: disable=too-few-public-methods
class EventStorageObserver(Protocol):
    """Observer interface for EventStorage changes.

    This class is a protocol that must be implemented by classes that
    want to observe changes in the
    :py:class:`~ska_tango_testing.integration.event.storage.EventStorage`
    class. See the class documentation for more information.
    """

    def on_events_change(self, events: list[ReceivedEvent]) -> None:
        """Handle events list change.

        :param events: Current list of events
        """


class EventStorage:
    """Thread-safe storage for Tango events.

    This class provides a thread-safe storage for
    :py:class:`~ska_tango_testing.integration.event.base.ReceivedEvent`
    instances. An instance of this class can be used to store the events
    that are received from multiple Tango devices concurrently.

    This class also offers a subscription mechanism to notify observers
    of changes in the stored events. An observer must implement the
    :py:class:`~ska_tango_testing.integration.event.storage.EventStorageObserver`
    interface. The observer will be notified of changes in the events list
    1) the first time it subscribes, and 2) every time a new event is stored.
    Every notification will include a full copy of the current events list
    (maybe in future we will also pass the new event separately).

    Both the storing and the notification mechanisms are thread-safe.

    The subscription mechanism is inspired by the
    `Observer Design Pattern <https://refactoring.guru/design-patterns/observer>`_.
    """  # pylint: disable=line-too-long # noqa: E501

    def __init__(self) -> None:
        """Initialise the events storage."""
        self._events: list[ReceivedEvent] = []
        self._lock = threading.Lock()
        self._observers: list[EventStorageObserver] = []

    def subscribe(self, observer: EventStorageObserver) -> None:
        """Add an observer to be notified of events changes.

        :param observer: The observer to add
        """
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)
        observer.on_events_change(self.events)

    def unsubscribe(self, observer: EventStorageObserver) -> None:
        """Remove an observer.

        :param observer: The observer to remove
        """
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def _notify_all(self) -> None:
        """Notify all observers of the current events."""
        events_copy = self.events
        for observer in self._observers:
            observer.on_events_change(events_copy)

    def store(self, event: ReceivedEvent) -> list[ReceivedEvent]:
        """Store a new event and notify observers.

        :param event: The event to store
        :return: A copy of the current events list
        """
        with self._lock:
            self._events.append(event)
            events_copy = self._events.copy()

        self._notify_all()
        return events_copy

    def clear_events(self) -> None:
        """Clear all stored events."""
        with self._lock:
            self._events.clear()

        self._notify_all()

    @property
    def events(self) -> list[ReceivedEvent]:
        """Get a copy of all stored events.

        :return: A copy of the current events list
        """
        with self._lock:
            return self._events.copy()
