"""This module implements test harness for testing mock callables."""
import threading
from typing import Any, Callable

import pytest

from ska_tango_testing.mock import MockCallable, MockCallableGroup


@pytest.fixture()
def mock_callable() -> MockCallable:
    """
    Return a standalone mock callable.

    :return: a standalone mock callable.
    """
    return MockCallable()


@pytest.fixture()
def callable_group() -> MockCallableGroup:
    """
    Return the callable group under test.

    :return: the callable group under test.
    """
    return MockCallableGroup("a", "b", "c", timeout=1.0)


@pytest.fixture(scope="session")
def schedule_call() -> Callable:
    """
    Return a callable used to schedule a call to a callback at a future time.

    :return: a callable.
    """

    def _schedule_call(
        delay: float, callable_to_call: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        threading.Timer(delay, callable_to_call, args, kwargs).start()

    return _schedule_call
