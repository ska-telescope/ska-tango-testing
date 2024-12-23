"""Thread-safe storage for Tango events."""

import threading

from .event import ReceivedEvent


class EventsStorage:
    """Thread-safe storage for Tango events.

    This class provides thread-safe storage and retrieval of ReceivedEvents.
    It handles the concurrent access to events from different threads through
    a lock mechanism.
    """

    def __init__(self) -> None:
        """Initialize the events storage."""
        self._events: list[ReceivedEvent] = []
        self._lock = threading.Lock()

    def store(self, event: ReceivedEvent) -> list[ReceivedEvent]:
        """Store a new event in a thread-safe way.

        :param event: The event to store.
        :return: A copy of the current events list
        """
        with self._lock:
            self._events.append(event)
            return self._events.copy()

    def clear_events(self) -> None:
        """Clear all stored events."""
        with self._lock:
            self._events.clear()

    @property
    def events(self) -> list[ReceivedEvent]:
        """Get a copy of all stored events.

        :return: A copy of the current events list
        """
        with self._lock:
            return self._events.copy()
