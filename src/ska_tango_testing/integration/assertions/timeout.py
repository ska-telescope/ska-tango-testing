"""Timeout for chained assertions in the integration tests.

This module provides utilities to set a timeout for multiple chained
assertions. The timeout is shared between all the chained assertions,
so that the total time to wait for all the events to occur is the same.

This module exposes:

- a function :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
  which is an assertpy extension that permits setting a timeout for the next
  chain of assertions.
- a class :py:class:`~ska_tango_testing.integration.assertions.ChainedAssertionsTimeout`
  to implement a timeout that can be shared between multiple chained
  assertions, essentially providing updated timeout values that decrease
  over time. (It is used internally)
- a function :py:func:`~ska_tango_testing.integration.assertions.get_context_timeout`
  that retrieves the timeout value from the given assertpy context.
  (It is used internally)

"""  # pylint: disable=line-too-long # noqa: E501

from datetime import datetime
from threading import Lock
from typing import Any, SupportsFloat

# ------------------------------------------------------------------
# Class to represent a shared timeout for chained assertions


class ChainedAssertionsTimeout(SupportsFloat):
    """A utility for using the same timeout for multiple chained assertions.

    (It is used internally)

    This class is used to set a timeout once and share it between multiple
    chained assertions. It permits you to:

    - Initialise the timeout once, with a specified value in seconds.
    - Start the timeout
    - In various moments, get an updated timeout value that is the remaining
      time from the initial timeout.

    By default, the initialisation is done when
    :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
    is called. The updated timeout should then be used in the next chained
    assertions. When you print an error message, you can also access the
    original timeout value.

    Usage example:

    if this is the assertion code you want to achieve (where the three events
    must occur within the same ``10`` seconds timeout):

    .. code-block:: python

        assert_that(event_tracer).within_timeout(10).has_change_event_occurred(
            ...
        ).has_change_event_occurred(
            ...
        ).has_change_event_occurred(
            ...
        )

    You can use the ``ChainedAssertionsTimeout`` inside the
    ``has_change_event_occurred`` method like this:

    .. code-block:: python

        def has_change_event_occurred(self, ...):
            # ... some code ...
            timeout = self.timeout.get_remaining_timeout()
            query = tracer.query_events(..., timeout=timeout)
            # ... some code ...

            # if I need to access the original timeout value
            # (e.g., for composing an error message)
            error_message = (
                "Expected a change event to occur within"
                f" {self.timeout.initial_timeout} seconds"
            )

    **Some further notes**:

    - For the evaluation to begin, you have to call the :py:meth:`start`
      method, which is automatically called in the
      :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
      assertion. The method can be called many times, but it will only
      set the start time once.
    - You can directly pass a timeout object both to the
      :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
      assertion and to the query objects and methods. A casting to a float
      will automatically return the remaining timeout value. Sharing the same
      timeout object between multiple blocks of assertions is also possible
      and will lead to the same timeout value for all the blocks. E.g.,

    .. code-block:: python

        timeout = ChainedAssertionsTimeout(10)

        # this asserton block automatically starts the timeout
        assert_that(tracer).within_timeout(timeout).has_change_event_occurred(
            ...
        )

        # this assertion block will access a decreased timeout value
        assert_that(tracer).within_timeout(timeout).has_change_event_occurred(
            ...
        )

    - The object is protected by an internal lock for ensuring
      eventual parallel access to the timeout object. This is probably
      strictly necessary (since those kinds of parallel accesses are edge
      cases), but we still do it for safety.
    """

    def __init__(self, timeout: float) -> None:
        """Initialise a new timeout for chained assertions.

        :param timeout: The initial timeout value in seconds. If the timeout
            is < 0 or infinite, it will be set to 0.
        """
        super().__init__()
        self._lock = Lock()
        self._initial_timeout = (
            max(0.0, timeout) if timeout != float("inf") else 0.0
        )
        self._start_time: datetime | None = None

    @staticmethod
    def get_timeout_object(
        timeout: SupportsFloat,
    ) -> "ChainedAssertionsTimeout":
        """Get a timeout object from a timeout value.

        This method is a factory method that creates a new timeout object
        from a timeout value. If the timeout value is already a timeout object,
        it will return the same object.

        :param timeout: The timeout value in seconds, or a timeout object.
        :return: A timeout object.
        """
        if isinstance(timeout, ChainedAssertionsTimeout):
            return timeout
        return ChainedAssertionsTimeout(float(timeout))

    # ------------------------------------------------------------------
    # Public API (thread-safe, it calls the lock)

    @property
    def initial_timeout(self) -> float | int:
        """Get the initial timeout value in seconds.

        :return: The initial timeout value in seconds.
        """
        with self._lock:
            return self._initial_timeout

    @property
    def start_time(self) -> datetime | None:
        """Get the start time of the timeout.

        :return: The start time of the timeout.
        """
        with self._lock:
            return self._start_time

    def is_started(self) -> bool:
        """Check if the timeout has been started.

        :return: ``True`` if the timeout has been started, ``False`` otherwise.
        """
        with self._lock:
            return self._is_started()

    def start(self) -> None:
        """Start the timeout.

        This method sets the start time of the timeout to the current time.
        It can be called multiple times, but it will only set the start time
        once.
        """
        with self._lock:
            self._start()

    def get_remaining_timeout(self) -> float:
        """Get the remaining timeout value, since the initialization time.

        :return: The remaining timeout value in seconds. It is at least ``0``
            and at most the initial timeout value. It will decrease over time.
        """
        with self._lock:
            return self._get_remaining_timeout()

    def __float__(self) -> float:
        """Get the remaining timeout value when casting to float.

        # NOTE: For retro-compatibility, we want this object to be possible to
        # cast to a number. This is why before 0.7.2, the timeout in assertions
        # used as float number directly. We want to keep this behavior for
        # retro-compatibility reasons.

        :return: The remaining timeout value in seconds.
        """
        return self.get_remaining_timeout()

    # ------------------------------------------------------------------
    # Implementations (they assume the lock is called by the public API)

    def _is_started(self) -> bool:
        """Check if the timeout has been started.

        :return: ``True`` if the timeout has been started, ``False`` otherwise.
        """
        return self._start_time is not None

    def _start(self) -> None:
        """Start the timeout."""
        if self._start_time is None:
            self._start_time = datetime.now()

    def _get_remaining_timeout(self) -> float:
        """Get the remaining timeout (in seconds) since the start time.

        :return: The remaining timeout value in seconds. It is at least ``0``
            and at most the initial timeout value. It will decrease over time.
            If the timeout has not been started yet, it will return the initial
            timeout value.
        """
        if not self._is_started():
            return float(self._initial_timeout)

        assert self._start_time is not None
        return max(
            0.0,
            float(self._initial_timeout)
            - (datetime.now() - self._start_time).total_seconds(),
        )


# ------------------------------------------------------------------
# Assertpy extension to set a timeout for chained assertions


def within_timeout(assertpy_context: Any, timeout: SupportsFloat) -> Any:
    """Add a timeout for the next chain of tracer assertions.

    :py:class:`~ska_tango_testing.integration.TangoEventTracer`
    allows querying events within a timeout. In other words, you can
    make assertions about events that will occur in the future within
    a certain time frame and "await" for them (if they didn't occur yet).
    This method when called inside an assertion context permits
    you to set a timeout for the next chain of assertions.

    **IMPORTANT NOTE**: The timeout, like one may intuitively expect, is
    shared between all the chained assertions. This means that if you set
    a timeout of 10 seconds and you have 3 chained assertions, the total
    time to wait for all the events to occur is 10 seconds, not 30 seconds.
    Concretely, each assertion will consume some time from the timeout, until
    it reaches zero.

    Usage example:

    .. code-block:: python

        # (given a subscribed tracer)

        # non-blocking long operation that triggers an event at the end
        sut.long_operation_that_triggers_an_event()

        # Check that the operation is done within 30 seconds
        assert_that(tracer).within_timeout(30).has_change_event_occurred(
            attribute_name="operation_state",
            attribute_value="DONE",
        )

    Alternatively, when you want to verify a set of events occurring
    within a certain shared timeout:

    .. code-block:: python

        # Check that the 3 events occur within 30 seconds
        assert_that(tracer).within_timeout(30).has_change_event_occurred(
            attribute_name="operation_state",
            attribute_value="INITIAL_STATE",
        ).has_change_event_occurred(
            attribute_name="operation_state",
            attribute_value="PROCESSING",
        ).has_change_event_occurred(
            attribute_name="operation_state",
            attribute_value="DONE",
        )

        # IMPORTANT NOTE: this will NOT verify that the events occur in the
        # given order, just that they occur within the same timeout!

    **NOTE**: this assertion always passes, its only purpose is to
    set the timeout for the following assertions.

    **NOTE**: Using a (small) timeout is a good practice even in not so long
    operations, because it makes the test more robust and less prone to
    flakiness and false positives.

    :param assertpy_context: The `assertpy` context object
        (It is passed automatically)
    :param timeout: The time in seconds to wait for the event to occur, or
        a timeout object that supports float operations. NOTE: you can
        pass a
        :py:class:`~ska_tango_testing.integration.assertions.ChainedAssertionsTimeout`
        object to share the same timeout between multiple blocks of assertions.

    :return: The decorated assertion context, with a
        :py:class:`~ska_tango_testing.integration.assertions.ChainedAssertionsTimeout`
        instance stored in the ``event_timeout`` attribute.
    """  # pylint: disable=line-too-long # noqa: E501
    # create a new timeout object (or re-use the existing one)
    timeout = ChainedAssertionsTimeout.get_timeout_object(timeout)

    # ensure the timeout is started
    timeout.start()

    # store the timeout in the assertpy context
    assertpy_context.event_timeout = timeout
    return assertpy_context


def get_context_timeout(assertpy_context: Any) -> SupportsFloat:
    """Get the timeout value from the given assertpy context.

    (It is used internally)

    This function retrieves the timeout value from the given assertpy context.
    It is used internally in the assertions to get the timeout value to use
    in the next chained assertions. To set the timeout, you should use the
    :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
    assertion.

    (It is used internally)

    :param assertpy_context: The `assertpy` context object

    :return: An object that supports float operations, representing the
        timeout value in seconds for this context.
    """
    return getattr(assertpy_context, "event_timeout", 0.0)
