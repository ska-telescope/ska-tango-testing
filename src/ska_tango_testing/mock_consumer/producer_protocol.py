"""This module provides a mock callback class."""
from __future__ import annotations

from typing import Any, Optional

from typing_extensions import Protocol


class ProducerProtocol(Protocol):  # pylint: disable=too-few-public-methods
    """
    Interface specification for producers.

    In order for a consumer to be able to work with a producer, the
    producer must implement this get method, so that each call results
    in either an item is returned within the provided timeout period, or
    `queue.Empty` being raised at the end of the timeout period.
    """

    def get(self: ProducerProtocol, timeout: Optional[float] = 1.0) -> Any:
        """
        Return the next item.

        :param timeout: how long, in seconds, to wait for an item to
            arrive, before giving up and raising `queue.Empty`. The
            default is 1 second. A value of None means wait forever.

        :return: the next time produced

        :raises queue.Empty: if there is still no item available at the
            end of the timeout period
        """  # noqa: DAR202, DAR402
        ...
