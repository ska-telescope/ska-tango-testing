"""Thread-safe storage for Tango events."""

import threading
from typing import Protocol

from .event import ReceivedEvent


# pylint: disable=too-few-public-methods
class EventStorageObserver(Protocol):
    """Observer interface for EventStorage changes."""

    def on_events_change(self, events: list[ReceivedEvent]) -> None:
        """Handle events list change.

        :param events: Current list of events
        """


class EventStorage:
    """Thread-safe storage for Tango events.

    This class provides thread-safe storage and retrieval of ReceivedEvents.
    It handles the concurrent access to events from different threads through
    a lock mechanism.
    """

    def __init__(self) -> None:
        """Initialize the events storage."""
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
