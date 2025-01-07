"""Query that looks for N events that match a given predicate."""

from typing import Callable, SupportsFloat

from ..event import ReceivedEvent
from .base import EventQuery


class NEventsMatchQuery(EventQuery):
    """Query that looks for N events that match a given predicate.

    This query will succeed when there are received N events that match
    a certain predicate (without duplicates). The query will evaluate
    the predicate for each event and store the matching events (avoiding
    duplicates) and will succeed when the number of matching events is
    equal or greater than the target number of events.

    Here the follows an example of how to use this query:

    .. code-block:: python

        def predicate(event: ReceivedEvent, all_events: list[ReceivedEvent]) -> bool:
            return (
                event.has_device("sys/tg_test/1") and
                event.has_attribute("attr1") and
                event.attribute_value >= 42
            )

        # query for 3 events that match from a certain device and attribute
        # with a value greater or equal to 42
        query = NEventsMatchQuery(predicate, target_n_events=3, timeout=10)

        # evaluate the query
        tracer.evaluate_query(query)

        # access the matching events
        if query.succeeded():
            first_matching_event = query.matching_events[0]

        # description will include some information about the criteria
        # (e.g., the target number of events) and the results
        # (e.g., the number of matching events)
        logging.info(query.describe())

    """  # pylint: disable=line-too-long # noqa: E501

    def __init__(
        self,
        predicate: Callable[[ReceivedEvent, list[ReceivedEvent]], bool],
        target_n_events: int = 1,
        timeout: SupportsFloat = 0.0,
    ) -> None:
        """Initialize the query with the predicate and target number of events.

        :param predicate: A function that takes an event
            and the list of all events as input and returns True
            if the event matches the desired criteria. the predicate
            can evaluate just the event in isolation or also the
            event in the context of the other events. The list of events
            is supposed to be ordered by the time they were received.
        :param target_n_events: The target number of events to match.
            Defaults to 1.
        :param timeout: The timeout for the query in seconds. Defaults to 0.
        """
        super().__init__(timeout)
        self.predicate = predicate
        self.target_n_events = target_n_events
        self.matching_events: list[ReceivedEvent] = []

    def _succeeded(self) -> bool:
        """Check if the query succeeded.

        :return: True if the query succeeded, False otherwise.
        """
        return len(self.matching_events) >= self.target_n_events

    def _evaluate_events(self, events: list[ReceivedEvent]) -> None:
        """Evaluate the query based on the current events.

        :param events: The updated list of events.
        """
        for event in events:
            if (
                self.predicate(event, events)
                and event not in self.matching_events
            ):
                self.matching_events.append(event)

    def _describe_criteria(self) -> str:
        """Describe the criteria of the query.

        :return: A string describing the criteria of the query.
        """
        return (
            f"Looking for {self.target_n_events} events"
            "matching a given predicate."
        )

    def _describe_results(self) -> str:
        """Describe the results of the query.

        :return: A string describing the results of the query.
        """
        desc = (
            f"Observed {len(self.matching_events)} events "
            "matching a given predicate. "
        )
        if self.matching_events:
            desc += "\n" + self._events_to_str()
        return desc

    def _events_to_str(self) -> str:
        """Convert the matching events to a string.

        :return: A string representation of the matching events.
        """
        return "\n".join(map(str, self.matching_events))
