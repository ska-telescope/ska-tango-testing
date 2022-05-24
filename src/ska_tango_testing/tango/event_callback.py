"""This module provides for testing against Tango event callbacks."""
from __future__ import annotations

from typing import Any, Dict, Optional

from ska_tango_testing.callable import MockCallableGroup
from ska_tango_testing.consumer import CharacterizerType


def _event_characterizer_factory(
    assert_no_error: bool = True,
) -> CharacterizerType:
    def _event_characterizer(
        characteristics: Dict[str, Any]
    ) -> Dict[str, Any]:
        assert not characteristics["call_kwargs"]
        assert len(characteristics["call_args"]) == 1
        event = characteristics["call_args"][0]

        if assert_no_error:
            assert (
                not event.err
            ), f"Received failed change event: error stack is {event.errors}."
        else:
            characteristics["event_error"] = event.err
            characteristics["event_error_stack"] = event.errors

        if event.attr_value:
            attribute_data = event.attr_value
            characteristics["attribute_name"] = attribute_data.name
            characteristics["attribute_value"] = attribute_data.value
            characteristics["attribute_quality"] = attribute_data.quality

        return characteristics

    return _event_characterizer


class MockTangoEventCallbackGroup(MockCallableGroup):
    """This class implements a group of Tango change event callbacks."""

    def __init__(
        self: MockTangoEventCallbackGroup,
        *callables: str,
        timeout: Optional[float] = 1.0,
        assert_no_error: bool = True,
    ) -> None:
        """
        Initialise a new instance.

        :param callables: positional arguments providing the names of callables
            in this group.
        :param timeout: number of seconds to wait for the callable to be
            called, or None to wait forever. The default is 1.0 seconds.
        :param assert_no_error: defaults to True, in which case this
            callback group will assert that each event to arrive is not
            an error event. Tests can then proceed on that assumption.
            If False, this callback group will not assert that events
            are not error events, but rather will return "err" and
            "errors" values. Tests then have to be written to check for
            error events.
        """
        callbacks = {
            callable: _event_characterizer_factory(assert_no_error)
            for callable in callables
        }
        super().__init__(timeout=timeout, **callbacks)

    def assert_change_event(
        self,
        callback_name: str,
        attribute_value: Any,
        lookahead: Optional[int] = None,
    ) -> None:
        """
        Assert that the callback received a change event with the given value.

        :param callback_name: name of the callback that we are asserting
            to have been called
        :param attribute_value: new value of the attribute for which the
            change event has been sent
        :param lookahead:  The number of calls to examine in search of a
            matching call. The default is 1, which means we are
            asserting against the *next* call.

        :raises AssertionError: if the asserted call has not occurred
            within the timeout period
        """
        try:
            self.assert_against_call(
                callback_name,
                attribute_value=attribute_value,
                lookahead=lookahead or 1,
            )
        except AssertionError:
            raise  # pylint: disable=try-except-raise

    class _EventCallback:
        def __init__(
            self, underlying_callable: MockCallableGroup._Callable
        ) -> None:
            """
            Initialise a new instance.

            :param underlying_callable: the callable object that this
                callback will use.
            """
            self._callable = underlying_callable

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self._callable(*args, **kwargs)

        def __getattr__(self, attr: str) -> Any:
            return getattr(self._callable, attr)

        def assert_change_event(
            self,
            attribute_value: Any,
            lookahead: Optional[int] = None,
        ) -> None:
            """
            Assert a change event with the given value.

            :param attribute_value: new value of the attribute for which
                the change event has been sent
            :param lookahead:  The number of calls to examine in search
                of a matching call. The default is 1, which means we are
                asserting against the *next* call.

            :raises AssertionError: if the asserted call has not
                occurred within the timeout period
            """
            try:
                self._callable.assert_against_call(
                    attribute_value=attribute_value,
                    lookahead=lookahead or 1,
                )
            except AssertionError:
                raise  # pylint: disable=try-except-raise

    def __getitem__(  # type: ignore[override]
        self, callback_name: str
    ) -> MockTangoEventCallbackGroup._EventCallback:
        """
        Return a standalone Tango event callback for the specified name.

        This can be passed to the caller to be actually called, and it
        can also be used to assert calls.

        :param callback_name: name of the callback sought.

        :return: a standalone mock Tango event callback
        """
        return self._EventCallback(super().__getitem__(callback_name))
