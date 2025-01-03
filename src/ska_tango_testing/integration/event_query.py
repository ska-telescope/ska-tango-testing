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
        self._evaluation_start: datetime | None = None
        """The evaluation start time. It is set when the evaluation begins."""

        self._evaluation_end: datetime | None = None
        """The evaluation end time. It is set when the evaluation ends."""

        self._timeout: SupportsFloat = timeout
        """The object that will determine the timeout of the query.

        It is not simply a float because it can also be something that
        casts to a float. This is useful when you want to have a dynamic
        timeout shared between multiple queries.
        """

        self._initial_timeout_value: float | None = None
        """The initial timeout set when the evaluation begins.

        It is automatically set to the value of the timeout attribute
        at the time of the evaluation start.
        """

        self._timeout_signal = Event()
        """A signal to notify the timeout expiration."""
        self._lock = Lock()
        """A lock to protect the query state."""

    # ---------------------------------------------------------------------
    # Status properties
    
    def status(self) -> EventQueryStatus:
        """Get the status of the query.

        The query can be in one of the following states:

        - NOT_STARTED: the query is created but not evaluated yet.
        - IN_PROGRESS: the query is being evaluated.
        - SUCCEEDED: the query evaluation terminated and succeeded.
        - FAILED: the query evaluation terminated and failed.

        :return: The status of the query.
        """
        with self._lock:
            return self._status()

    def is_completed(self) -> bool:
        """Check if the query is completed.

        :return: True if the query is completed, False otherwise.
        """
        with self._lock:
            return self._is_completed()
        
    def remaining_timeout(self) -> float:
        """Get the remaining timeout in seconds.

        :return: The remaining timeout in seconds.
        """
        with self._lock:
            return self._remaining_timeout()
        
    def evaluation_duration(self) -> float | None:
        """Get the duration of the query evaluation in seconds.

        :return: The duration of the query evaluation in seconds.
        """
        with self._lock:
            return self._evaluation_duration()
        
    # ---------------------------------------------------------------------
    # Evaluation methods (DO NOT CALL DIRECTLY)


    def evaluate(self) -> None:
        """Start the evaluation of the query (DO NOT CALL DIRECTLY).

        This method is used by the tracer to put the query in evaluation
        mode so it can receive events and evaluate them. It should not
        be called directly by the user. This method is blocking and
        will return only when the query evaluation completes or the
        timeout expires.

        :raises ValueError: If the evaluation is already started.
        """
        # Begin the evaluation (set the start time)
        with self._lock:
            if self._evaluation_start:
                raise ValueError(
                    "Evaluation already started. A query can "
                    "only be evaluated once."
                )
            self._evaluation_start = datetime.now()
            self._initial_timeout_value = float(self._timeout)

        # TODO: here I may do the storage subscription, it would be
        # appropriate to keep it controlled I guess.

        # If a timeout is set, start a timer and wait for it to expire
        # or for the query to be completed (succeeded or failed)
        # If the timeout is 0.0, the query will not wait for nothing and
        # will return immediately
        if self._initial_timeout_value > 0.0:
            self._timeout_signal.clear()
            self._timeout_signal.wait(self._initial_timeout_value)

        # End the evaluation (set the end time)
        with self._lock:
            self._evaluation_end = datetime.now()

    def on_events_change(self, events: List[ReceivedEvent]) -> None:
        """Handle events change and evaluate them against the query criteria.

        (DO NOT CALL DIRECTLY)

        This method is the callback that is called when new events are
        received by the events manager. It evaluates again all the events
        and stops the evaluation if the criteria are met.

        :param events: The updated list of events (with both
            new and old events).
        """
        with self._lock:
            # If the query is already completed, do not evaluate
            if self._is_completed():
                return

            # Evaluate the events and stop if the criteria are met
            self._evaluate_events(events)

            # If the query should stop, set the timeout signal
            if self._is_stop_criteria_met():
                self._timeout_signal.set()

    def succeeded(self) -> bool:
        """Check if the query succeeded.

        :return: True if the query succeeded, False otherwise.
        """
        with self._lock:
            return self._succeeded()

    # ---------------------------------------------------------------------
    # Protected thread-unlocked methods
    #
    # The following methods are by themselves thread-unsafe,
    # but they are protected by the locks in the public methods

    def _status(self) -> EventQueryStatus:
        """Get the status of the query (thread-unsafe).

        :return: The status of the query.
        """
        if self._evaluation_start is None:
            return EventQueryStatus.NOT_STARTED
        if self._evaluation_end is None:
            return EventQueryStatus.IN_PROGRESS

        if self._succeeded():
            return EventQueryStatus.SUCCEEDED
        return EventQueryStatus.FAILED
    
    def _is_completed(self) -> bool:
        """Check if the query evaluation is completed (thread-unsafe).

        :return: True if the query evaluation is completed, False otherwise.
        """
        return self._status() in (
            EventQueryStatus.SUCCEEDED,
            EventQueryStatus.FAILED,
        )

    def _is_stop_criteria_met(self) -> bool:
        """Check if the evaluation should stop now (thread-unsafe).

        The stop criteria is the criteria that determines if the query
        should stop evaluating events. By default, the query stops if
        it succeeded, but you can override this method to add more
        criteria (e.g., an early stop condition).

        NOTE: this is NOT a method to check if the query completed or
        succeeded, but if it should stop right now (and then so be marked
        as completed).

        :return: True if the query should stop, False otherwise.
        """
        return self._succeeded()

    def _evaluation_duration(self) -> float | None:
        """Get the duration of the query evaluation in seconds (thread-unsafe).

        :return: The duration of the query evaluation in seconds.
        """
        if self._evaluation_start is None:
            return 0.0
        if self._evaluation_end is None:
            return (datetime.now() - self._evaluation_start).total_seconds()
        return (self._evaluation_end - self._evaluation_start).total_seconds()

    def _remaining_timeout(self) -> float:
        """Get the remaining timeout in seconds (thread-unsafe).

        :return: The remaining timeout in seconds.
        """
        if self._initial_timeout_value is None:
            return float(self._timeout)

        duration = self._evaluation_duration()

        # duration cannot be None because evaluation
        # start time is not None when initial timeout is set
        assert duration is not None

        return max(0.0, self._initial_timeout_value - duration)

    # ---------------------------------------------------------------------
    # Subclasses must implement the following methods

    @abstractmethod
    def _succeeded(self) -> bool:
        """Check if the query succeeded.

        NOTE: this method should be implemented in subclasses. By default,
        if is protected by the a lock, so whatever data structure
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
