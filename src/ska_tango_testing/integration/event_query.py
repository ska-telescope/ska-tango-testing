"""Abstract class for querying events with a timeout mechanism."""


from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from threading import Event, Lock
from typing import List, SupportsFloat

from .event import ReceivedEvent


class EventQueryStatus(Enum):
    """Enumeration for the status of an events query."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EventQuery(ABC):
    """Abstract class for querying events with a timeout mechanism.

    An events query is a mechanism to query a set of events within a timeout.
    A query has the following characteristics:

    - it has a lifecycle:
        - it is created
        - it is evaluated, (with the ``evaluate`` method, called once
            by the events manager)
        - while ongoing, the query receive events and wait or to reach
            the success criteria defined in the ``succeeded`` method
            or for a timeout to expire
        - when the query is completed, the status is updated and the
            evaluation end time is set

    The lifecycle is accessible through the ``status`` method.

    - it is an abstract class, so it cannot be instantiated directly
        and you have to subclass it and implement two key methods:
    - ``_succeeded`` defines the success criteria of your query, write
        here some logic to check if your query is satisfied (return True
        if it is, False otherwise). Consider that by default a timeout
        will be awaited if the query is not completed yet.
    - ``_evaluate_events`` is a callback method you can implement to
        analyze new events and update some kind of your internal state.
        The same internal state can be used in the ``_succeeded`` method.
        The method is activated once when the query evaluation begins
        and every time new events are received. Consider that every time
        this method is called all the received events are passed to it
        (not only the new ones). Consider also that both this method and
        the ``_succeeded`` method are protected by a lock, so you can
        safely access your internal state.

    To evaluate a query, technically you:

    - subscribe the query to an
        :py:class:`ska_tango_testing.integration.events_storage.EventStorage`;
    - call the ``evaluate`` method of the query, which will block you until
        the query is completed or the timeout expires.

    From an user perspective, to evaluate the query you can simply pass it
    to a :py:class:`ska_tango_testing.integration.tracer.TangoEventTracer`
    instance.
    """

    def __init__(self, timeout: SupportsFloat = 0.0) -> None:
        """Initialize the events query.

        :param timeout: The timeout for the query in seconds.
        """
        self.evaluation_start: datetime | None = None
        self.evaluation_end: datetime | None = None
        self.timeout: SupportsFloat = timeout
        self._timeout_signal = Event()

        self._evaluation_time_lock = Lock()
        self._evaluation_events_lock = Lock()

    def describe(self) -> str:
        """Describe the query for logging purposes.

        The description includes:

        - The query class name
        - The query status
        - The query timeout
        - The query evaluation start time, the duration and end time
          (if available)
        - Additional information provided by the subclass.

        Extend this method in subclasses to provide additional information
        such as query criteria, expected results, and actual results. Be
        exhaustive in the description to facilitate debugging. Design a
        one-line description.

        :return: A string description of the query.
        """
        description = (
            f"Query class: {self.__class__.__name__}, "
            f"Status: {self.status().value}, "
            f"Timeout: {self.timeout} s, "
        )

        duration = None

        with self._evaluation_time_lock:
            if self.evaluation_start is not None:
                description += f"Start time: {self.evaluation_start}, "
                duration = datetime.now() - self.evaluation_start

            if self.evaluation_end is not None:
                assert self.evaluation_start is not None
                description += f"End time: {self.evaluation_end}, "
                duration = self.evaluation_end - self.evaluation_start

        if duration is not None:
            description += f"Duration: {duration}, "

        return description

    def status(self) -> EventQueryStatus:
        """Get the status of the query.

        :return: The status of the query.
        """
        with self._evaluation_time_lock:
            if self.evaluation_start is None:
                return EventQueryStatus.NOT_STARTED
            if self.evaluation_end is None:
                return EventQueryStatus.IN_PROGRESS

        if self.succeeded():
            return EventQueryStatus.SUCCEEDED
        return EventQueryStatus.FAILED

    def is_completed(self) -> bool:
        """Check if the query is completed.

        :return: True if the query is completed, False otherwise.
        """
        return self.status() in (
            EventQueryStatus.SUCCEEDED,
            EventQueryStatus.FAILED,
        )

    def evaluate(self) -> None:
        """Start the evaluation of the query.

        This method is called by the events manager to start the evaluation
        of the query. It blocks until the query is completed or the timeout
        expires.

        :raises ValueError: If the evaluation is already started.
        """
        # Begin the evaluation (set the start time)
        with self._evaluation_time_lock:
            if self.evaluation_start:
                raise ValueError(
                    "Evaluation already started. A query can "
                    "only be evaluated once."
                )
            self.evaluation_start = datetime.now()

        # If a timeout is set, start a timer and wait for it to expire
        # or for the query to be completed (succeeded or failed)
        timeout = float(self.timeout)
        if timeout > 0.0:
            self._timeout_signal.clear()
            self._timeout_signal.wait(timeout)

        # End the evaluation (set the end time)
        with self._evaluation_time_lock:
            self.evaluation_end = datetime.now()

    def on_events_change(self, events: List[ReceivedEvent]) -> None:
        """Handle events change.

        :param events: The updated list of events.
        """
        # no more evaluation if the query is completed
        if self.is_completed():
            return

        # Evaluate the events and stop if the criteria are met
        # (protected by the events lock)
        stop = False
        with self._evaluation_events_lock:
            self._evaluate_events(events)
            stop = self._is_stop_criteria_met()

        # If the query should stop, set the timeout signal
        # (the end time will be set by the evaluate method)
        if stop:
            self._timeout_signal.set()

    def _is_stop_criteria_met(self) -> bool:
        """Check if the stop criteria are met.

        This method is called by the events manager to check if the
        query should stop evaluating events.

        :return: True if the query should stop, False otherwise.
        """
        return self._succeeded()

    def succeeded(self) -> bool:
        """Check if the query succeeded.

        :return: True if the query succeeded, False otherwise.
        """
        with self._evaluation_events_lock:
            return self._succeeded()

    @abstractmethod
    def _succeeded(self) -> bool:
        """Check if the query succeeded.

        NOTE: this method should be implemented in subclasses. By default,
        if is protected by the events lock, so whatever data structure
        you use to store events, you can safely access it.

        :return: True if the query succeeded, False otherwise.
        """

    @abstractmethod
    def _evaluate_events(self, events: List[ReceivedEvent]) -> None:
        """Evaluate the query based on the current events.

        This method is called automatically by the events manager
        whenever the list of events changes.

        :param events: The updated list of events.
        """
