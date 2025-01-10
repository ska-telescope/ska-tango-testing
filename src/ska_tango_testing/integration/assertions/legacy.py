"""Legacy deprecated assertions code.

I keep it for retro-compatibility with old custom assertions that
may be still using it, but:

- it is not recommended to use it in new code
- it is marked as deprecated
- it is not covered by tests
- it will not receive updates, be guaranteed to work, or be supported
- it will be removed in future versions

"""

from typing import Any, Callable

import deprecation  # type: ignore

from ..event import ReceivedEvent
from ..tracer import TangoEventTracer
from .has_hasnt_events import get_context_tracer

ANY_VALUE = None


@deprecation.deprecated(
    deprecated_in="0.8.0",
    details="This method is deprecated and will likely be removed in future. "
    "It is replaced by "
    "`ska_tango_testing.integration.assertions.get_context_tracer`.",
)
def _get_tracer(assertpy_context: Any) -> TangoEventTracer:
    """Get the `TangoEventTracer` instance from the `assertpy` context.

    **WARNING**: This method is deprecated and will be removed in future.
    It is replaced by
    :py:func:`~ska_tango_testing.integration.assertions.get_context_tracer`.

    Helper method to get the
    :py:class:`~ska_tango_testing.integration.TangoEventTracer`
    instance from the `assertpy` context which is stored in the 'val'.
    It fails if the instance is not found.

    :param assertpy_context: The `assertpy` context object.

    :return: The `TangoEventTracer` instance.

    :raises ValueError: If the
        :py:class:`~ska_tango_testing.integration.TangoEventTracer`
        instance is not found (i.e., the assertion is not called with
        a tracer instance).
    """  # noqa: DAR402
    return get_context_tracer(assertpy_context)


@deprecation.deprecated(
    deprecated_in="0.8.0",
    details="This method is deprecated and will likely be removed in future. "
    "It is replaced by queries objects, which are able to print by "
    "themselves their details; see "
    "`ska_tango_testing.integration.query`.",
)
def _print_passed_event_args(
    device_name: str | None = ANY_VALUE,
    attribute_name: str | None = ANY_VALUE,
    attribute_value: Any | None = ANY_VALUE,
    previous_value: Any | None = ANY_VALUE,
    custom_matcher: Callable[[ReceivedEvent], bool] | None = None,
    target_n_events: int = 1,
) -> str:
    """Print the arguments passed to the event query.

    **WARNING**: This method is deprecated and will be removed in future.
    The assertions mechanism now is based on queries objects, which are
    able to print by themselves their details; see
    :py:mod:`~ska_tango_testing.integration.query`.

    Helper method to print the arguments passed to the event query in a
    human-readable format.

    :param device_name: The device name to match. If not provided, it will
        match any device name.
    :param attribute_name: The attribute name to match. If not provided,
        it will match any attribute name.
    :param attribute_value: The current value to match. If not provided,
        it will match any current value.
    :param previous_value: The previous value to match. If not provided,
        it will match any previous value.
    :param custom_matcher: An arbitrary predicate over the event. It is
        essentially a function or a lambda that takes an event and returns
        ``True`` if it satisfies your condition.
    :param target_n_events: The minimum number of events to match.
        If not provided, it defaults to 1.

    :return: The string representation of the passed arguments.
    """  # pylint: disable=too-many-arguments
    res = ""
    if device_name is not ANY_VALUE:
        res += f"device_name='{device_name}', "
    if attribute_name is not ANY_VALUE:
        res += f"attribute_name='{attribute_name}', "
    if attribute_value is not ANY_VALUE:
        res += f"attribute_value={str(attribute_value)}, "
    if previous_value is not ANY_VALUE:
        res += f"previous_value={str(previous_value)}, "
    if custom_matcher is not None:
        res += "custom_matcher=<custom predicate>, "
    if target_n_events != 1:
        res += f"target_n_events={target_n_events}, "

    return res
