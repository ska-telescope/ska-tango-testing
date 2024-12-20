"""Thread-safe storage for Tango events."""

import threading
from typing import Callable

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

    def get_matching(
        self, predicate: Callable[[ReceivedEvent], bool]
    ) -> list[ReceivedEvent]:
        """Get all events that match the given predicate.

        :param predicate: Function that takes an event and returns
            True if it matches your desired criteria.

            NOTE: The predicate may recursively reference the current
            list of events, and also call this method.

            E.g., return all the events only if the total number of events
            is greater than 10, otherwise return an empty list.

            .. code-block:: python

                storage.get_matching(lambda _: len(storage.events) > 10)

        :return: list of matching events
        """
        current_events = self.events
        return [event for event in current_events if predicate(event)]

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
