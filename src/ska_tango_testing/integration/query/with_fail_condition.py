"""Implementation of specific event queries."""

from typing import Callable

from ..event import ReceivedEvent
from .base import EventQuery


class QueryWithFailCondition(EventQuery):
    """A query that wraps another query and stops early if a condition is met.

    This query wraps another query and stops the evaluation early if a given
    stop condition is met. The stop condition is a function that takes an event
    as input and returns True if the query should stop evaluating events.
    Each new event is evaluated by the stop condition before being passed to
    the wrapped query. A few notes:

    - this query will succeed if the wrapped query succeeds (and the stop
      condition is not met);
    - the stop condition is evaluated before the wrapped query, so the wrapped
      query will not be evaluated if the stop condition is met;
    - this query timeout is exactly the one of the wrapped query.

    Here follows an example of how to use this query:

    .. code-block:: python

        # define a wrapped query
        wrapped_query = NStateChangesQuery(
            device_name="sys/tg_test/1",
            attribute_name="attr1",
            custom_matcher=lambda event: event.attribute_value >= 42,
            target_n_events=3,
            timeout=10, # this timeout will be used
        )

        # define a stop condition that detects error events from any device
        def stop_condition(event: ReceivedEvent) -> bool:
            return (
                event.has_attribute("longRunningCommandResult") and
                "error code 3: exception" in str(event.attribute_value)
            )

        # wrap the query with the stop condition
        query = QueryWithFailCondition(wrapped_query, stop_condition)

        # evaluate the query
        tracer.evaluate_query(query)

        if query.succeeded():
            # access the matching events
            first_matching_event = wrapped_query.matching_events[0]
        elif query.failed_event is not None:
            # query failed early because of the stop condition
            # ...
        else:
            # query failed for another reason (e.g., timeout)
            # ...

        # description will combine the wrapped query description with
        # the stop condition description and the eventual detected
        # early stop event
        logging.info(query.describe())

    The general idea of this kind of query comes from the
    `Decorator Design Pattern <https://refactoring.guru/design-patterns/decorator>`_,
    because this query is a subclass that wraps a generic query to
    add a new behavior (the early stop condition).

    **IMPORTANT NOTE**: at the moment, the internal fail event variable is not
    protected from external modifications with a lock, so if
    an user modifies the value while the query is being evaluated,
    there may be unexpected results. But this is not likely to happen
    if the client is using the query as intended.

    """  # pylint: disable=line-too-long # noqa: E501

    def __init__(
        self,
        wrapped_query: EventQuery,
        stop_condition: Callable[[ReceivedEvent], bool],
    ) -> None:
        """Initialize the query with the wrapped query and stop condition.

        :param wrapped_query: The query to wrap.
        :param stop_condition: A function that takes an event
            as input and returns True if the stop condition is met.
        """
        # pylint: disable=protected-access
        super().__init__(wrapped_query._timeout)
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
