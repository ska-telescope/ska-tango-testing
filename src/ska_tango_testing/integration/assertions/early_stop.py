"""Early stop sentinel for assertions.

This module provides a chained assertion that can be used to define a
sentinel for early stopping the evaluation of the chained assertions
if a certain condition is met.

This module exposes:

- a function
  :py:func:`~ska_tango_testing.integration.assertions.with_early_stop`
  which is an assertpy extension that permits setting a sentinel for the
  following chained assertions.
- a function
  :py:func:`~ska_tango_testing.integration.assertions.get_context_early_stop`
  that retrieves the early stop sentinel from the given assertpy context.
  (It is used internally)
"""

from typing import Any, Callable

from ..event import ReceivedEvent

# ------------------------------------------------------------------
# Early stop sentinel for chained assertions


def with_early_stop(
    assertpy_context: Any,
    sentinel_predicate: Callable[[ReceivedEvent], bool] | None = None,
) -> Any:
    """Define a sentinel predicate to stop the chained assertions early.

    This function is an assertpy extension that permits setting a sentinel
    predicate for the following chained
    :py:class:`~ska_tango_testing.integration.TangoEventTracer`
    assertions. The sentinel predicate is essentially a function
    that receives a
    :py:class:`~ska_tango_testing.integration.event.ReceivedEvent` and
    determines if the evaluation of the chained assertions should stop early.
    The function acts as a sort of "sentinel" and evaluates all the
    new (and old) events every time a new event is received by the tracer.
    If the function returns `True` for some event, the evaluation of the
    chained assertions immediately stops and a failure is raised.

    This is particularly useful when a long timeout is set (e.g., because of
    network delays, slow systems, etc.) but occasionally you are able
    to detect an error early and thus save a lot of time by avoiding
    a useless long wait. If you use the early stop sentinel without
    a timeout, it will still evaluate all the events once
    and fail if the sentinel predicate is met, even if your assertion
    would not have failed (in other words, the early stop criteria always
    have priority).

    Usage example:

    .. code-block:: python

        LONG_TIMEOUT = 250  # seconds
        assert_that(event_tracer).described_as(
            "A set of events must occur within a long timeout "
            "AND no error code should be detected in the meantime."
        ).within_timeout(
            LONG_TIMEOUT
        ).with_early_stop(
            lambda event: event.has_attribute("longRunningCommandResult") and
                "error code 3: exception" in str(event.attribute_value)
        ).has_change_event_occurred(
            ...
        ).has_change_event_occurred(
            ...
        ).has_change_event_occurred(
            ...
        )

    NOTE: if you chain multiple ``with_early_stop`` assertions, at the moment
    only the last one will be considered. In the future, we may consider
    supporting multiple sentinel predicates. At the moment, if you want
    to have multiple sentinel predicates, you should combine them in a
    single function (e.g., with an ``and`` operator). At the moment,
    if you chain a ``with_early_stop(None)`` assertion after other
    ``with_early_stop`` assertions, it will deactivate them.

    NOTE: the behaviour of the early stop sentinel will likely not work
    for your old custom assertions. If you have some, please update them
    to use the new mechanisms and explicitly check the sentinel predicate
    as done in the new assertions.

    :param assertpy_context: The `assertpy` context object
        (It is passed automatically)
    :param sentinel_predicate: The sentinel predicate to stop the
        chained assertions evaluation early. It is a function that receives a
        :py:class:`~ska_tango_testing.integration.event.ReceivedEvent` and
        returns a boolean. If the predicate returns `True`, it means that
        it detected a condition that requires stopping the evaluation of
        the chained assertions.

        **IMPORTANT NOTE**: The sentinel predicate is evaluated every time
        a new event is received by the tracer. This means that it will evaluate
        a very heterogeneous set of events, so make it solid and robust.
    :return: The decorated assertion context, with the given sentinel predicate
        stored in the context 'early_stop' attribute.
    """
    assertpy_context.early_stop = sentinel_predicate
    return assertpy_context


def get_context_early_stop(
    assertpy_context: Any,
) -> Callable[[ReceivedEvent], bool] | None:
    """Retrieve the early stop sentinel from the assertpy context.

    (It is used internally by the chained assertions)

    This function retrieves the early stop sentinel from the assertpy context.
    It is used internally by the chained assertions to get the sentinel
    predicate and evaluate it.

    :param assertpy_context: The `assertpy` context object
        (It is passed automatically)
    :return: The sentinel predicate function or `None` if it is not set.
    """
    return getattr(assertpy_context, "early_stop", None)
