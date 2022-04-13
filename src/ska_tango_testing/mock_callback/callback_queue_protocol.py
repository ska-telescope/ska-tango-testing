"""This module provides a protocol specification for a callback's queue."""
from __future__ import annotations

from typing import Optional
from unittest.mock import Mock

from typing_extensions import Protocol


class MockCallbackQueueProtocol(Protocol):
    """
    Protocol specification for a callback's queue.

    Any class that implements this protocol can be passed to a callback
    for use as its underlying queue mechanism.
    """

    def put(self: MockCallbackQueueProtocol, called_mock: Mock) -> None:
        """
        Put a called mock onto the queue.

        :param called_mock: a :py:class:`unittest.mock.Mock` that has
            already been called.
        """
        ...

    def get(
        self: MockCallbackQueueProtocol, timeout: Optional[float] = None
    ) -> Mock:
        """
        Get a called mock off the queue.

        :param timeout: how long to block for the queue have have
            something for us to get. If None, we block forever.

        :return: a :py:class:`unittest.mock.Mock` that has already been
            called.
        """  # noqa: DAR202
        # https://github.com/terrencepreilly/darglint/issues/178
        ...
