"""Query that looks for N state change events."""

from typing import Any, Callable, SupportsFloat

import tango

from ..event import ReceivedEvent
from .n_events_match import NEventsMatchQuery


class NStateChangesQuery(NEventsMatchQuery):
    """Query that looks for N state change events.

    This query extend
    :py:class:`~ska_tango_testing.integration.query.NEventsMatchQuery` to
    will succeed when there are received N state change events
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

    Here the follows an example of how to use this query:

    .. code-block:: python

        # query to detect a state change from OFF to ON
        query = NStateChangesQuery(
            device_name=device, # device name or device proxy, it's the same
            attribute_name="state",
            attribute_value=tango.DevState.ON,
            previous_value=tango.DevState.OFF,
            timeout=10,
        )

        # evaluate the query
        tracer.evaluate_query(query)

        # access the matching events
        if query.succeeded():
            first_matching_event = query.matching_events[0]

        # another more elaborate query that replicates the NEventsMatchQuery
        # example but with state change criteria
        query2 = NStateChangesQuery(
            device_name="sys/tg_test/1",
            attribute_name="attr1",
            custom_matcher=lambda event: event.attribute_value >= 42,
            target_n_events=3,
            timeout=10,
        )

        # ...

    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        device_name: "str | tango.DeviceProxy | None" = None,
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
        self, event: ReceivedEvent, events: list[ReceivedEvent]
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
        self, event: ReceivedEvent, events: list[ReceivedEvent]
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
