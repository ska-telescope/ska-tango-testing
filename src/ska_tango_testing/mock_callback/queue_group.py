"""This module provides a :py:class:`QueueGroup` class."""
from __future__ import annotations

import queue
from collections import defaultdict
from threading import Condition
from typing import Any, DefaultDict, Hashable, List, Optional, Tuple


class QueueGroup:
    """
    This class provides an abstract data type for a group of queues.

    One puts an item to a queue with
    `queue_group.put(queue_name, item)`. This item will now be on the
    named queue, and can be retrieved from that queue with
    `item = queue_group.get_from(queue_name, timeout=1.0)`.
    Alternatively, we can get the next item from *any* queue in the
    group with `(group_name, item) = queue_group.get(timeout=1)`
    """

    def __init__(self: QueueGroup) -> None:
        """Initialise a new instance."""
        self._main_queue: List[Hashable] = []
        self._subqueues: DefaultDict[Hashable, List[Any]] = defaultdict(list)
        self._content_condition = Condition()

    # TODO: Why are DAR401 and DAR402 raised here?
    def get(
        self: QueueGroup, timeout: Optional[float] = None
    ) -> Tuple[Hashable, Any]:  # noqa: DAR401
        """
        Get the next item to be put onto any of the queues in this group.

        :param timeout: the time, in seconds, to block waiting for an
            item to become available. If omitted, or explicitly set to
            None, then we wait forever.

        :raises queue.Empty: if the queue is still empty at the end of
            the timeout period.

        :return: a (queue_name, item) tuple.
        """  # noqa: DAR402
        with self._content_condition:
            while len(self._main_queue) == 0:
                if not self._content_condition.wait(timeout=timeout):
                    raise queue.Empty()
            queue_name = self._main_queue.pop(0)
            return (queue_name, self._subqueues[queue_name].pop(0))

    # TODO: Why are DAR401 and DAR402 raised here?
    def get_from(
        self: QueueGroup, queue_name: Hashable, timeout: Optional[float] = None
    ) -> Any:  # noqa: DAR401
        """
        Get the next item to be put onto a specific queue in this group.

        :param queue_name: name of the queue from which to get the next
            item.
        :param timeout: the time, in seconds, to block waiting for an
            item to become available. If omitted, or explicitly set to
            None, then we wait forever.

        :raises queue.Empty: if the queue is still empty at the end of
            the timeout period.

        :return: a (queue_name, item) tuple.
        """  # noqa: DAR402
        with self._content_condition:
            while len(self._subqueues[queue_name]) == 0:
                if not self._content_condition.wait(timeout=timeout):
                    raise queue.Empty()
            self._main_queue.remove(queue_name)
            return self._subqueues[queue_name].pop(0)

    def put(self: QueueGroup, queue_name: Hashable, item: Any) -> None:
        """
        Put an item on a specified queue.

        :param queue_name: name of the queue on which to put the item.
        :param item: the item to put onto the specified queue
        """
        with self._content_condition:
            self._subqueues[queue_name].append(item)
            self._main_queue.append(queue_name)
            self._content_condition.notify_all()
