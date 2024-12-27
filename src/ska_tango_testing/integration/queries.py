"""Implementation of specific event queries."""

from typing import Callable, List, SupportsFloat

from .event import ReceivedEvent
from .event_query import EventQuery


class NEventsMatchQuery(EventQuery):
    """Query that looks for N events that match a given predicate.

    This query will succeed when there are received N events that match
    a certain predicate (without duplicates). The query will evaluate
    the predicate for each event and store the matching events (avoiding
    duplicates) and will succeed when the number of matching events is
    equal or greater than the target number of events.
    """

    def __init__(
        self,
        predicate: Callable[[ReceivedEvent], bool],
        target_n_events: int = 1,
        timeout: SupportsFloat = 0.0,
    ) -> None:
        """Initialize the query with the predicate and target number of events.

        :param predicate: A function that takes an event as input and returns
            True if the event matches the desired criteria.
        :param target_n_events: The target number of events to match.
            Defaults to 1.
        :param timeout: The timeout for the query in seconds. Defaults to 0.
        """
        super().__init__(timeout)
        self.predicate = predicate
        self.target_n_events = target_n_events
        self.matching_events: List[ReceivedEvent] = []

    def _succeeded(self) -> bool:
        """Check if the query succeeded.

        :return: True if the query succeeded, False otherwise.
        """
        return len(self.matching_events) >= self.target_n_events

    def _evaluate_events(self, events: List[ReceivedEvent]) -> None:
        """Evaluate the query based on the current events.

        :param events: The updated list of events.
        """
        for event in events:
            if self.predicate(event) and event not in self.matching_events:
                self.matching_events.append(event)
