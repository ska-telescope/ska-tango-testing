"""Timeout for chained assertions in the integration tests.

This module provides a utilities to set a timeout for multiple chained
assertions. The timeout is shared between all the chained assertions,
so that the total time to wait for all the events to occur is the same.

This module exposes:

- a function :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
  which is an assertpy extension that permits to set a timeout for the next
  chain of assertions.
- a class :py:class:`~ska_tango_testing.integration.assertions.ChainedAssertionsTimeout`
  to implement a timeout that can be shared between multiple chained
  assertions, that essentially after it's initialised, it provides
  updated timeout values that decrease over time. (It is used internally)
- a function :py:func:`~ska_tango_testing.integration.assertions.get_context_timeout`
  that from the given assertpy context, retrieves the timeout value.
  (It is used internally)

"""  # pylint: disable=line-too-long # noqa: E501

from datetime import datetime
from typing import Any, SupportsFloat

# ------------------------------------------------------------------
# Class to represent a shared timeout for chained assertions


class ChainedAssertionsTimeout(SupportsFloat):
    """A utility for using the same timeout for multiple chained assertions.

    (It is used internally)

    This class is used to set a timeout once and share it between multiple
    chained assertions. It permits you:

    - Init the timeout once, with a specified value in seconds.
    - In various moments, get an updated timeout value that is the remaining
      time from the initial timeout.

    By default, the init is done when
    :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
    is called. The updated timeout should then be used in the next chained
    assertions. When you print an error message, you can also access the
    original timeout value.

    Usage example:

    if this is the assertion code you want to achieve (where the tree events
    must occur in the same ``10`` seconds timeout):

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
    """

    def __init__(self, timeout: float) -> None:
        """Initialize a new timeout for chained assertions.

        :param timeout: The initial timeout value in seconds.
        """
        super().__init__()
        self._initial_timeout = timeout
        self._start_time = datetime.now()

    @property
    def initial_timeout(self) -> float | int:
        """Get the initial timeout value in seconds.

        :return: The initial timeout value in seconds.
        """
        return self._initial_timeout

    @property
    def start_time(self) -> datetime:
        """Get the start time of the timeout.

        :return: The start time of the timeout.
        """
        return self._start_time

    def get_remaining_timeout(self) -> float:
        """Get the remaining timeout value, since the initialization time.

        :return: The remaining timeout value in seconds. It is at least ``0``
            and at most the initial timeout value. It will decrease over time.
        """
        return max(
            0.0,
            self.initial_timeout
            - (datetime.now() - self.start_time).total_seconds(),
        )

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
# Assertpy extension to set a timeout for chained assertions


def within_timeout(assertpy_context: Any, timeout: int | float) -> Any:
    """Add a timeout for the next chain of tracer assertions.

    :py:class:`~ska_tango_testing.integration.TangoEventTracer`
    allows to query events within a timeout. In other words, you can
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

    Alteratively, when you want to verify a set of events occurring
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
    :param timeout: The time in seconds to wait for the event to occur.

    :return: The decorated assertion context, with a
        :py:class:`~ska_tango_testing.integration.assertions.ChainedAssertionsTimeout`
        instance stored in the ``event_timeout`` attribute.
    """  # pylint: disable=line-too-long # noqa: E501
    assertpy_context.event_timeout = ChainedAssertionsTimeout(timeout)
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
