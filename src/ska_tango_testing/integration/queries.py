"""Implementation of specific event queries."""

from typing import Any, Callable, List, SupportsFloat

import tango

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
        predicate: Callable[[ReceivedEvent, List[ReceivedEvent]], bool],
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

    def _evaluate_events(self, events: List[ReceivedEvent]) -> None:
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


class NStateChangesQuery(NEventsMatchQuery):
    """Query that looks for N state change events.

    This query will succeed when there are received N state change events
    using the provided criteria. The supported criteria are the following:

    - the device name
    - the attribute name
    - the current value
    - the previous value
    - a custom matcher function

    All the criteria are optional and can be combined to define the state
    change events you are looking for. The query will evaluate the criteria
    for each event and store the matching events (avoiding duplicates) and
    will succeed when the number of matching events is equal or greater than
    the target number of events.

    NOTE: passing ``None`` to any of the criteria will match any value for
    that criterion.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        device_name: str | tango.DeviceProxy | None = None,
        attribute_name: str | None = None,
        attribute_value: Any | None = None,
        previous_value: Any | None = None,
        custom_matcher: Callable[[ReceivedEvent], bool] | None = None,
        target_n_events: int = 1,
        timeout: SupportsFloat = 0.0,
    ) -> None:
        """Initialize the query with the state change parameters.

        :param device_name: The name of the device to match.
            Optional, by default it will match any device.
        :param attribute_name: The name of the attribute to match.
            Optional, by default it will match any attribute.
        :param attribute_value: The current value of the attribute.
            Optional, by default it will match any current value.
        :param previous_value: The previous value of the attribute.
            Optional, by default it will match any previous value.
        :param custom_matcher: A custom matcher function to apply to events
            to define further rules. Optional, by default no further rules
            are applied.
        :param target_n_events: The target number of events to match.
            Defaults to 1.
        :param timeout: The timeout for the query in seconds. Defaults to 0.

        NOTE: passing ``None`` to any of the criteria will match any value for
        that criterion.
        """
        super().__init__(self._predicate, target_n_events, timeout)
        self.device_name = device_name
        self.attribute_name = attribute_name
        self.attribute_value = attribute_value
        self.previous_value = previous_value
        self.custom_matcher = custom_matcher

    def _predicate(
        self, event: ReceivedEvent, events: List[ReceivedEvent]
    ) -> bool:
        """Check if the event matches the state change criteria.

        :param event: The event to check.
        :param events: The list of all events.
        :return: True if the event matches the state change criteria,
            False otherwise.
        """
        return (
            # if given, check if the device name matches
            (self.device_name is None or event.has_device(self.device_name))
            # if given, check if the attribute name matches
            and (
                self.attribute_name is None
                or event.has_attribute(self.attribute_name)
            )
            # if given, check if the attribute value matches
            and (
                self.attribute_value is None
                or event.attribute_value == self.attribute_value
            )
            # if given, check if the previous value matches
            and (
                self.previous_value is None
                or self._event_has_previous_value(event, events)
            )
            # if given, apply the custom matcher
            and (self.custom_matcher is None or self.custom_matcher(event))
        )

    def _event_has_previous_value(
        self, event: ReceivedEvent, events: List[ReceivedEvent]
    ) -> bool:
        """Check if the event has the expected previous value.

        :param event: The event to check.
        :param events: The list of all events.
        :return: True if the event has the expected previous value,
            False otherwise.
        """
        # Find the previous event from the same device and attribute (if any)
        previous_event = None
        for evt in events:
            if (
                # the event is from the same device and attribute
                evt.has_device(event.device_name)
                and evt.has_attribute(event.attribute_name)
                # the is previous to the target event
                and evt.reception_time < event.reception_time
                # no previous event was found or the current one
                # is more recent than the previous one
                and (
                    previous_event is None
                    or evt.reception_time > previous_event.reception_time
                )
            ):
                previous_event = evt

        # If no previous event was found, return False (there is no event
        # before the target one, so none with the expected previous value)
        if previous_event is None:
            return False

        # If the previous event was found, check if previous value matches
        return previous_event.attribute_value == self.previous_value

    def _describe_criteria(self) -> str:
        """Describe the criteria of the query.

        :return: A string describing the criteria of the query.
        """
        desc = super()._describe_criteria()
        desc += "\nState change criteria: "

        criteria: list[str] = []
        if self.device_name is not None:
            criteria.append(f"device_name='{self._describe_device_name()}'")
        if self.attribute_name is not None:
            criteria.append(f"attribute_name={self.attribute_name}")
        if self.attribute_value is not None:
            criteria.append(f"attribute_value={self.attribute_value}")
        if self.previous_value is not None:
            criteria.append(f"previous_value={self.previous_value}")
        if self.custom_matcher is not None:
            criteria.append("a custom matcher function is set")

        if criteria:
            desc += ", ".join(criteria)
        else:
            desc += "no criteria set"

        return desc

    def _describe_device_name(self) -> str:
        """Describe the device name criterion.

        Use this method to get the device name criterion as a string.
        Use it only if the device name is set.

        :return: A string describing the device name criterion.
        :raises ValueError: If there is no device name criterion set.
        """
        if isinstance(self.device_name, str):
            return self.device_name
        if isinstance(self.device_name, tango.DeviceProxy):
            return self.device_name.dev_name()

        raise ValueError("There is no device name criterion set")
