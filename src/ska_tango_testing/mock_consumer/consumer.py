"""This module provides a mock consumer class, for testing producers."""
from __future__ import annotations

import queue
from collections import deque
from typing import Any, Callable, Optional

from .producer_protocol import ProducerProtocol


class MockConsumer:
    """
    This class implements a mock consumer.

    A mock consumer is given a producer to act upon. The only
    requirement of that producer is that it have a `get(timeout)` method
    that either returns an item when one becomes available, or raises
    `queue.Empty` at the end of the timeout period. The mock consumer is
    used to assert on the sequence of items returned from repeated calls
    to this `get` method.
    """

    def __init__(
        self: MockConsumer,
        producer: ProducerProtocol,
        timeout: float = 1.0,
        characterizer: Optional[Callable[[Any], dict[str, Any]]] = None,
    ) -> None:
        """
        Initialise a new mock consumer instance.

        :param producer: the producer from which this consumer gets
            items.
        :param timeout: the maximum time to wait, in seconds, for an
            item to become available. The default is 1.0 seconds. A
            value of `None` means wait forever.
        :param characterizer: An optional callable that creates a
            keyword dictionary out of each item.

            For simple items, such as ints or floats or strs, we can
            directly compare the items to our expected item, e.g.
            `mock_consumer.assert_next_item(3)`. But for more complex
            items, this not may be possible. Consider, for example, a
            situation where the item is a `FooEvent` containing a name,
            a value, and a timestamp. The presence of a timestamp makes
            it impossible to construct an `expected_item` that would
            allow us to `mock_consumer.assert_next_item(expected_item)`.
            Instead, we provide an characterizer that constructs a
            dictionary of item characteristics, with `name` and `value`
            keys (we might choose to include or omit a `timestamp` key.
            We can then
            `mock_consumer.assert_of_next_item(name="foo", value="bah")`.
        """
        self._deque: deque[dict[str, Any]] = deque()
        self._producer = producer
        self._characterizer = characterizer
        self._timeout = timeout

    @property
    def timeout(self: MockConsumer) -> Optional[float]:
        """
        Return the timeout for this callback.

        :return: the timeout for this callback.
        """
        return self._timeout

    def assert_no_item(self: MockConsumer, **kwargs: Optional[float]) -> None:
        """
        Assert that an item is not produced within the timeout period.

        This is a slow method because it has to wait the full timeout
        period in order to determine that the call has not arrived. An
        optional timeout parameter is provided for situations where you
        are happy for the assertion to pass after a shorter wait time.

        :param kwargs: additional keyword arguments. The only supported
            argument is "timeout", which, if provided, sets the timeout,
            in seconds. If None, the callback will never timeout. If not
            provided, the default is the value provided to the
            initializer method.

        :raises AssertionError: if an item was produced.
        """
        if len(self._deque) == 0:
            try:
                item = self._producer.get(
                    timeout=kwargs.get("timeout", self._timeout)
                )
            except queue.Empty:
                return

            characteristics = {"_raw": item}
            if self._characterizer is not None:
                characteristics.update(self._characterizer(item))

            self._deque.append(characteristics)

        raise AssertionError(
            "Expected no item to be available. " + self._items_available_str()
        )

    def assert_item(
        self: MockConsumer,
        *args: Any,
        lookahead: int = 1,
        **kwargs: Any,
    ) -> None:
        """
        Assert on an item that is expected to be produced.

        It can be called in two ways:

        For simple items that can be checked using equality, use a
        single positional argument: `consumer.assert_item(1)`.

        For more complex items that cannot be checked using equality,
        use keyword arguments to assert on characteristics of the
        expected item (as specified by the `characterizer` provided at
        initialisation):
        `consumer.assert_item(name="adminMode", value=AdminMode.ONLINE)`.

        By default, this method only looks at the next produced item.
        However a `lookahead` argument is provided for nondeterministic
        cases where an item is expected but might not be the very next
        item. For example, if `lookahead` is 3, this method will examine
        the next three items, in order, looking for a matching item.

        If a sufficient number of items have not been produced yet, this
        method will wait up to the specified timeout for each item to be
        produced.

        :param args: positional arguments. The only supported
            positional argument is the expected item.

        :param lookahead: number of items to check for the expected
            item.

        :param kwargs: keyword arguments. These are used to specify
            characteristics of the expected item.

        :raises ValueError: if called with more than one positional
            argument.

        :raises AssertionError: if a sufficient number of items are not
            produced within the specified timeout period, or if the
            items produced do not contain a matching item.
        """
        timeout = kwargs.pop("timeout", self._timeout)

        if len(args) > 1:
            raise ValueError(
                f"{self.__class__.__name__} accepts zero or one positional "
                "arguments."
            )
        if len(args) == 1:
            kwargs["_raw"] = args[0]

        for i in range(lookahead):
            if len(self._deque) == i:
                try:
                    item = self._producer.get(timeout=timeout)
                except queue.Empty:
                    break

                characteristics = {"_raw": item}
                if self._characterizer is not None:
                    characteristics.update(self._characterizer(item))

                self._deque.append(characteristics)

            for key, value in kwargs.items():
                if self._deque[i][key] != value:
                    break
            else:
                del self._deque[i]
                return

        raise AssertionError(
            f"Expected matching item within the first {lookahead} items. "
            + self._items_available_str()
        )

    def _items_available_str(self: MockConsumer) -> str:
        if len(self._deque) == 0:
            return "No items available."

        return "Items available:\n" + "\n    ".join(
            str(item["_raw"]) for item in self._deque
        )
