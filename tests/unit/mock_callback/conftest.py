"""This module implements test harness."""
import threading
from typing import Any, Callable

import pytest
from _pytest.fixtures import SubRequest

from ska_tango_testing.mock_callback import (
    MockCallback,
    MockCallbackGroup,
    QueueGroup,
)


@pytest.fixture(scope="session")
def schedule_call() -> Callable:
    """
    Return a callable used to schedule a call to a callback at a future time.

    :return: a callable.
    """

    def _schedule_call(
        delay: float, callback_to_call: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        threading.Timer(delay, callback_to_call, args, kwargs).start()

    return _schedule_call


@pytest.fixture()
def queue_group() -> QueueGroup:
    """
    Return a queue group for testing.

    This is a pytest fixture.

    :return: a queue group for testing.
    """
    return QueueGroup()


@pytest.fixture(
    params=[
        lambda: MockCallback(timeout=1.0),
        lambda: MockCallbackGroup()["test"],
    ]
)
def callback(request: SubRequest) -> MockCallback:
    """
    Return a callback to be used in testing.

    This fixture is parametrized to return callbacks in two ways: direct
    creation of a callback, and accessing a callback from within a
    group.

    :param request: A pytest object giving access to the requesting test
        context.

    :return: a callback to be used in testing
    """
    return request.param()


@pytest.fixture()
def callback_group() -> MockCallbackGroup:
    """
    Return a callback group to be used in testing.

    :return: a callback group
    """
    return MockCallbackGroup()
