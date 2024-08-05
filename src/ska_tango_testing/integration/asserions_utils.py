"""A set of utility tools for writing custom ``assertpy`` assertions.

The main ones are:

- :py:class:`~ska_tango_testing.integration.assertions_utils.ChainedAssertionsTimeout`,
  which is a utility for using the same timeout for multiple chained
  assertions.
"""  # pylint: disable=line-too-long # noqa: E501


from datetime import datetime


class ChainedAssertionsTimeout:
    """A utility for using the same timeout for multiple chained assertions.

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
            0,
            self.initial_timeout - (datetime.now() - self.start_time).seconds,
        )
