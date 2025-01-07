"""Implementation of specific event queries."""

from typing import Callable, SupportsFloat

from ..event import ReceivedEvent
from .base import EventQuery


class QueryWithFailCondition(EventQuery):
    """A query that wraps another query and stops early if a condition is met.

    This query wraps another query and stops the evaluation early if a given
    stop condition is met. The stop condition is a function that takes an event
    as input and returns True if the query should stop evaluating events.
    Each new event is evaluated by the stop condition before being passed to
    the wrapped query.

    Subscribe just this query to the event storage to evaluate it, not
    the wrapped query. The timeout of the wrapped query will be ignored.
    """

    def __init__(
        self,
        wrapped_query: EventQuery,
        stop_condition: Callable[[ReceivedEvent], bool],
        timeout: SupportsFloat = 0.0,
    ) -> None:
        """Initialize the query with the wrapped query and stop condition.

        :param wrapped_query: The query to wrap.
        :param stop_condition: A function that takes an event
            as input and returns True if the stop condition is met.
        :param timeout: The timeout for the query in seconds. Defaults to 0.
        """
        super().__init__(timeout)
        self.wrapped_query = wrapped_query
        self.stop_condition = stop_condition
        self.failed_event: ReceivedEvent | None = None

    def _succeeded(self) -> bool:
        """Check if the query succeeded.

        :return: True if the query succeeded, False otherwise.
        """
        return self.wrapped_query.succeeded() and self.failed_event is None

    def _evaluate_events(self, events: list[ReceivedEvent]) -> None:
        """Evaluate the query based on the current events.

        :param events: The updated list of events.
        """
        for event in events:
            if self.stop_condition(event):
                self.failed_event = event
                self._timeout_signal.set()
                return

        self.wrapped_query.on_events_change(events)

    def _is_stop_criteria_met(self) -> bool:
        """Stop the query if it succeeded or if the stop condition is met.

        :return: True if the query succeeded or if the stop condition is met.
        """
        return self._succeeded() or self.failed_event is not None

    def _describe_criteria(self) -> str:
        """Describe the criteria of the query.

        :return: A string describing the criteria of the query.
        """
        # pylint: disable=protected-access
        wrapped_query_criteria = self.wrapped_query._describe_criteria()
        return wrapped_query_criteria + "\nAn early stop condition is set. "

    def _describe_results(self) -> str:
        """Describe the results of the query.

        :return: A string describing the results of the query.
        """
        # pylint: disable=protected-access
        wrapped_query_results = self.wrapped_query._describe_results()

        if self._is_completed() and not self._succeeded():
            wrapped_query_results += "\n" + self._describe_fail_reason()

        return wrapped_query_results

    def _describe_fail_reason(self) -> str:
        """Describe the reason why the query failed.

        This method assumes that the query already failed and so
        that an initial timeout value was set and the duration calculated.

        :return: A string describing the reason why the query failed.
        """
        if self.failed_event is not None:
            return f"Event {str(self.failed_event)} triggered an early stop."

        # timeout and duration must be already calculated if this
        # method is called
        timeout = self._initial_timeout_value
        duration = self._evaluation_duration()
        assert isinstance(timeout, float)
        assert isinstance(duration, float)
        if duration >= timeout:
            return "The query failed because of a timeout."

        return "The query failed for an unknown reason."
