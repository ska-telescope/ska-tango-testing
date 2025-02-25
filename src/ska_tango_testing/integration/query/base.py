"""Abstract class for querying events with a timeout mechanism."""


from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from threading import Event, Lock
from typing import List, SupportsFloat

from ..event import ReceivedEvent
from ..event.storage import EventStorage


class EventQueryStatus(Enum):
    """Enumeration for the status of an events query.

    The status of an events query can be one of the following:

    - NOT_STARTED: the query is created but not evaluated yet.
    - IN_PROGRESS: the query is being evaluated.
    - SUCCEEDED: the query evaluation terminated and succeeded.
    - FAILED: the query evaluation terminated and failed.
    """

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EventQuery(ABC):
    """Abstract class for querying events with a timeout mechanism.

    An events query is a mechanism to query a set of events within a timeout
    and succeed if some criteria are met or fail otherwise.
    A query has the following characteristics.

    - It has a lifecycle (accessible through the ``status`` method and
      represented by
      :py:class:`~ska_tango_testing.integration.query.EventQueryStatus`):

      - it is instantiated and initialised with all the needed parameters
        (such as the timeout)
      - it is evaluated through an event tracer
      - if it has a >0 timeout, it will wait for the timeout to expire
        or for the success criteria to be met; if it has a 0 timeout, it
        will just evaluate the events once and return immediately;
        in both cases, the success criteria are defined by the
        ``succeeded`` method
      - when the query is completed (because the timeout expired or the
        success criteria are met), the evaluation ends and the query
        exposes its success or failed status (through the ``succeeded``
        method) and further information about the evaluation (like
        the duration, the initial and remaining timeout and a description
        of the results and the criteria) through the other methods
        (``evaluation_duration``, ``initial_timeout``, ``remaining_timeout``,
        ``describe``)

    - it is an abstract class, so it cannot be instantiated directly. Instead,
      a subclass has to be created to define which are exactly the success
      criteria and the evaluation logic. The subclass must implement the
      following protected methods:

      - ``_succeeded`` defines the success criteria of your query, write
        here some logic to check if your query is satisfied (return True
        if it is, False otherwise). Consider that by default a timeout
        will be awaited if the query is not completed yet.
      - ``_evaluate_events`` is a callback method you can implement to
        analyse new events and update some kind of your internal state.
        The same internal state can be used in the ``_succeeded`` method.
        The method is activated once when the query evaluation begins
        and every time new events are received. Consider that every time
        this method is called all the received events are passed to it
        (not only the new ones). Consider also that both this method and
        the ``_succeeded`` method are protected by a lock, so you can
        safely access your internal state
      - you may also want to override the ``_is_stop_criteria_met`` method
        to add more criteria to stop the evaluation (e.g., an early stop
        condition)
      - you may also want to override the description private method
        ``_describe_results`` to provide a custom description of the
        query results and the ``_describe_criteria`` method to provide
        a custom description of the query criteria you are using.

    From a user's perspective, to evaluate the query you can simply pass it
    to a :py:class:`ska_tango_testing.integration.tracer.TangoEventTracer`
    instance. Inside it, the query will automatically subscribe to the
    events storage and wait for the evaluation to complete. Example:

    .. code-block:: python

        tracer = TangoEventTracer()
        # (do all your subscriptions here)

        class MyQuery(EventQuery):

            def _evaluate_events(self, events: List[ReceivedEvent]) -> None:
                # (your logic here, that saves some kind of state)

            def _succeeded(self):
                # (your logic here, that checks if the query is satisfied
                # using the state saved in the _evaluate_events method)

            def _describe_results(self):
                # (your logic here, that describes the results of the query)
                # (optional but recommended)

            def _describe_criteria(self):
                # (your logic here, that describes the criteria of the query)
                # (optional but recommended)

        # simple evaluation without timeout (non blocking)
        query = MyQuery()
        tracer.evaluate_query(query)

        # evaluation with timeout (blocking, for at most 10 seconds)
        query_with_timeout = MyQuery(timeout=10.0)
        tracer.evaluate_query(query_with_timeout)

    **A SMALL DESCRIPTION OF THE QUERY EVALUATION MECHANISM**:
    the query is evaluated by connecting it to an
    :py:class:`~ska_tango_testing.integration.event.storage.EventStorage`,
    through a subscription mechanism. The query is then notified when
    new events are received and it can evaluate them. The query is
    also notified once when the evaluation begins. This way, when the
    ``evaluate`` method is called, the query is put in evaluation mode,
    it receives at least once all the events that are in the storage
    and every time a new event is stored it updates its internal state
    and checks if the success criteria are met. The timeout mechanism
    is implemented using a signal that is set when the timeout expires
    or when the success criteria are met (this way a client can be
    blocked until the evaluation completes or the timeout expires).

    Important inspiration for the query mechanism comes from:

    - the `Observer Design Pattern <https://refactoring.guru/design-patterns/observer>`_,
      for the way a query receives events from the storage and updates
      its internal state;
    - the `Template Method Design Pattern <https://refactoring.guru/design-patterns/template-method>`_,
      because it is just a skeleton class that requires subclasses to
      implement a few key steps of the algorithm.

    **IMPORTANT NOTE**: the query is internally thread safe,
    since all the attributes access are protected by a lock.
    As you may notice, the protected
    internal methods are not thread safe by themselves, but the lock
    is always and only acquired in the public methods. If you implement
    your own query:

    - **do not acquire the lock in the protected methods**, because it is
      already acquired in the public methods and that would cause a
      deadlock;
    - **do not call query public methods from the protected template methods**
      (like ``_succeeded`` and ``_evaluate_events``)
      you implement, because they may acquire the lock again and
      cause a deadlock (instead, limit yourself to access the internal
      state and eventually the protected methods, you will already
      have the lock acquired, so don't worry about acquiring it again).

    Essentially, you can not worry about concurrent access
    to your internal state, because it is protected by the lock (at least
    from eventual concurrent internal calls). The only tricky case may be
    if you wish to expose your internal state to the outside world
    and you think that some external client may access it concurrently
    to the evaluation phase. In this case, it's recommended that your
    internal state is protected in the same way as the query internal
    state is protected (with a lock, called just by public methods, that
    acquire the lock and orchestrate other unprotected private methods).
    If you think no client will access your state during the evaluation
    (which is the most common case), you can also not worry about it.

    """  # pylint: disable=line-too-long # noqa: E501

    def __init__(self, timeout: SupportsFloat = 0.0) -> None:
        """Initialise the events query.

        :param timeout: The timeout for the query in seconds. By default,
            the query will not wait for any timeout.

            NOTE: timeouts < 0 and infinite timeouts are automatically
            converted to 0 timeouts (no timeout).
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

    def set_timeout(self, timeout: SupportsFloat) -> None:
        """Change the timeout of the query (only before evaluation).

        Before the evaluation begins, you can change this query's timeout.

        :param timeout: The new timeout for the query in seconds.
        :raises RuntimeError: If the evaluation already started.
        """  # noqa: DAR402
        with self._lock:
            self._set_timeout(timeout)

    def initial_timeout(self) -> float:
        """Get the initial timeout in seconds.

        The initial timeout is the timeout set when the evaluation begins.
        If the evaluation did not start yet, the initial timeout is the
        value that can be read now from the timeout attribute.

        :return: The initial timeout in seconds.
        """
        with self._lock:
            return self._initial_timeout_value or self._get_timeout_value()

    def remaining_timeout(self) -> float:
        """Get the remaining timeout in seconds.

        The remaining timeout is the time left before the timeout expires.
        If the evaluation did not start yet, the remaining timeout is the
        value of the timeout attribute.

        :return: The remaining timeout in seconds.
        """
        with self._lock:
            return self._remaining_timeout()

    def evaluation_duration(self) -> float | None:
        """Get the duration of the query evaluation in seconds.

        The duration is the time elapsed between the evaluation start
        and the evaluation end. If the evaluation has not started yet,
        the duration is None. If the evaluation is in progress, the
        duration is the time elapsed between the evaluation start and
        the current time.

        :return: The duration of the query evaluation in seconds.
        """
        with self._lock:
            return self._evaluation_duration()

    def describe(self) -> str:
        """Describe the query status, criteria and results.

        By default the status is described including the status, the
        start and end time of the evaluation (if available), the timeout
        and the remaining timeout. You can override this method to
        provide a custom description of the query results by overriding
        the ``_describe_results`` method and the query criteria
        by overriding the ``_describe_criteria`` method.

        :return: The description of the query. It is a 6 lines string divided
            in 3 sections: status, criteria and results.
        """
        with self._lock:
            description = "EVENT QUERY STATUS:\n"
            description += self._describe_status()
            description += "\nEVENT QUERY CRITERIA:\n"
            description += self._describe_criteria()
            description += "\nEVENT QUERY RESULTS:\n"
            description += self._describe_results()
            return description

    # ---------------------------------------------------------------------
    # Evaluation methods
    # (DO NOT OVERRIDE THESE METHODS)

    def _set_timeout(self, timeout: SupportsFloat) -> None:
        """Change the timeout of the query (only before evaluation).

        This method is used internally to change the timeout of the query
        before the evaluation begins.

        :param timeout: The new timeout for the query in seconds.
        :raises RuntimeError: If the evaluation already started.
        """
        if self._evaluation_start:
            raise RuntimeError(
                "Cannot change the timeout after the evaluation started."
            )
        self._timeout = timeout

    def evaluate(self, storage: EventStorage) -> None:
        """Start the evaluation of the query (USED BY THE TRACER).

        This method is used by the tracer to put the query in evaluation
        mode so it can receive events and evaluate them.
        This method is blocking and
        will return only when the query evaluation completes or the
        timeout expires.

        NOTE: this method is meant to be called only one time. If you
        try to evaluate again or if you try to evaluate a query that is
        already in an evaluation state, a ValueError will be raised.

        NOTE: this method is meant to be called by the tracer, not by
        the end user. The end user should simply pass the query to the
        tracer and let it handle the evaluation.

        NOTE: this method is not meant to be overridden. If you want to
        implement the evaluation logic, you should implement the
        ``_succeeded`` and ``_evaluate_events`` methods. You can also
        override the ``_is_stop_criteria_met`` method to add more
        criteria to stop the evaluation.

        :param storage: The event storage to use to receive events.
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
            self._initial_timeout_value = self._get_timeout_value()

        # (if multiple processes call evaluate together, only one will
        # go on evaluating, the others will fail the check above)

        # Subscribe the query to the storage to receive events
        storage.subscribe(self)

        # If a timeout is set, start a timer and wait for it to expire
        # or for the query to be completed (succeeded or failed)
        # If the timeout is 0.0, the query will not wait for anything and
        # will return immediately
        if self._initial_timeout_value > 0.0:
            self._timeout_signal.wait(self._initial_timeout_value)

        # Unsubscribe the query from the storage
        storage.unsubscribe(self)

        # End the evaluation (set the end time)
        with self._lock:
            self._evaluation_end = datetime.now()

    def on_events_change(self, events: List[ReceivedEvent]) -> None:
        """Handle events change and evaluate them against the query criteria.

        This method is the callback that is called when new events are
        received by the events manager. It evaluates again all the events
        and stops the evaluation if the criteria are met.

        NOTE: this method is meant to be called by the events manager
        when new events are received. The end user should not call this
        method directly.

        NOTE: this method is not meant to be overridden. If you want to
        implement the evaluation logic, you should implement the
        ``_succeeded`` and ``_evaluate_events`` methods. You can also
        override the ``_is_stop_criteria_met`` method to add more
        criteria to stop the evaluation.

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
    # Subclasses must implement the following methods

    @abstractmethod
    def _succeeded(self) -> bool:
        """Check if the query succeeded.

        NOTE: this method should be implemented in subclasses. By default,
        it is protected by a lock, so whatever data structure
        you use to store events, you can safely access it.

        IMPORTANT: do not call public methods from this method implementation,
        as they may acquire the lock again and cause a deadlock! Also, do not
        acquire the lock again in this method, as it is already acquired.

        :return: True if the query succeeded, False otherwise.
        """

    @abstractmethod
    def _evaluate_events(self, events: List[ReceivedEvent]) -> None:
        """Evaluate the query based on the current events.

        This method is called automatically by the events manager
        whenever the list of events changes.

        IMPORTANT: do not call public methods from this method implementation,
        as they may acquire the lock again and cause a deadlock! Also, do not
        acquire the lock again in this method, as it is already acquired.

        :param events: The updated list of events.
        """

    # pylint: disable=no-self-use
    def _describe_results(self) -> str:
        """Describe the query results.

        By default, this method returns nothing. You can override
        this method to provide a custom description of the query results.
        Consider that ``_describe_status`` is already called before this
        and that it already tells if the query is ongoing or completed
        and if it succeeded or failed.

        :return: The description of the query results.
        """
        return "Results not described."

    # pylint: disable=no-self-use
    def _describe_criteria(self) -> str:
        """Describe the query criteria.

        By default, this method returns nothing. You can override
        this method to provide a custom description of the query criteria.
        Consider that ``_describe_status`` is already called before this
        so things such as the timeout and the remaining timeout are already
        described.

        :return: The description of the query criteria.
        """
        return "Criteria not described."

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

        :return: The duration of the query evaluation in seconds or None
            if the evaluation has not started yet.
        """
        if self._evaluation_start is None:
            return None
        if self._evaluation_end is None:
            return (datetime.now() - self._evaluation_start).total_seconds()
        return (self._evaluation_end - self._evaluation_start).total_seconds()

    def _remaining_timeout(self) -> float:
        """Get the remaining timeout in seconds (thread-unsafe).

        :return: The remaining timeout in seconds.
        """
        if self._initial_timeout_value is None:
            return self._get_timeout_value()

        duration = self._evaluation_duration()

        # duration cannot be None because evaluation
        # start time is not None when initial timeout is set
        assert duration is not None

        return max(0.0, self._initial_timeout_value - duration)

    def _describe_status(self) -> str:
        """Describe the status of the query (thread-unsafe).

        The status is described including the status, the start and end
        time of the evaluation (if available), the timeout and the
        remaining timeout. You can override this method to provide a
        better description of the query status.

        :return: The description of the query status.
        """
        description = ""
        description += f"Status={self._status().value}, "

        if self._evaluation_start:
            description += f"Start time={self._evaluation_start}, "

        if self._evaluation_end:
            description += f"End time={self._evaluation_end}, "

        # approximate the remaining timeout to 3 decimal digits
        if self._initial_timeout_value is not None:
            description += (
                f"Initial timeout={self._initial_timeout_value:.3f}s, "
            )
        else:
            description += (
                f"Initial timeout={self._get_timeout_value():.3f}s, "
            )

        if self._status() != EventQueryStatus.NOT_STARTED:
            description += (
                f"Remaining timeout={self._remaining_timeout():.3f}s, "
            )
            description += (
                f"Evaluation duration={self._evaluation_duration():.3f}s, "
            )

        return description

    def _get_timeout_value(self) -> float:
        """Calculate a >= 0 finite value from the timeout object.

        :return: The initial timeout value in seconds.
        """
        # transform None to 0.0 for retro-compatibility and greater safety
        if self._timeout is None:
            return 0.0
        timeout = max(0.0, float(self._timeout))
        return timeout if timeout != float("inf") else 0.0
