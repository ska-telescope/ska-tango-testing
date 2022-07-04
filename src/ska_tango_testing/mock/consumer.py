"""This module provides a :py:class:`QueueGroup` class."""
from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from queue import Empty
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Hashable,
    Iterable,
    Optional,
    TypeVar,
)

CharacterizerType = Callable[[Dict[str, Any]], Dict[str, Any]]

ItemType = TypeVar("ItemType")


logger = logging.getLogger("ska_tango_testing.mock")


class Node:  # pylint: disable=too-few-public-methods
    """A single node in a multiply-linked double-linked deque structure."""

    def __init__(self: Node, payload: Any) -> None:
        """
        Initialise a new instance.

        :param payload: the payload of the node.
        """
        self.prev: DefaultDict[Hashable, Optional[Node]] = defaultdict(None)
        self.next: DefaultDict[Hashable, Optional[Node]] = defaultdict(None)
        self.payload = payload

    def drop(self: Node) -> None:
        """Drop this node."""
        # It's safe to dike this out of the data structure, because our use
        # case only uses one iterator at a time, and this method won't be
        # called until that one iterator has found the item it is looking for,
        # so won't be used again. We therefore know that there are no external
        # references to this node that will be left dangling by us dropping it.
        for category in self.next:
            # for the type checker
            prev_node = self.prev[category]
            next_node = self.next[category]

            if prev_node is not None:
                prev_node.next[category] = next_node
            if next_node is not None:
                next_node.prev[category] = prev_node

        self.prev.clear()
        self.next.clear()
        self.payload = None


class MultiDeque:  # pylint: disable=too-few-public-methods
    """
    A multiply-linked doubly-linked list, with deque-like interface.

    We can append a new node to as many categories as we want, and we
    can consume a node regardless of its position.
    """

    def __init__(self: MultiDeque, *categories: Hashable) -> None:
        """
        Initialise a new instance.

        :param categories: the categories supported by this structure.
        """
        self.first = Node(None)
        self.last = Node(None)

        for category in categories:
            self.first.prev[category] = None
            self.first.next[category] = self.last
            self.last.prev[category] = self.first
            self.last.next[category] = None

    def __del__(self: MultiDeque) -> None:
        """Prepare to delete this object."""
        # This data structure is full of cyclic references that prevent python
        # from doing ref-count-based garbage collection. Let's make it easier
        # for the garbage collector by manually cleaning these references up.
        # That way, if the ref-count for *this class* drops to zero, that
        # should be enough to ensure the entire data structure gets collected.
        for category in list(self.first.next.keys()):
            node = self.first
            while True:
                node.payload = None
                next_node = node.next.pop(category)
                if next_node is None:
                    break
                del next_node.prev[category]
                node = next_node

    def append(self: MultiDeque, node: Node, *categories: Hashable) -> None:
        """
        Append a node to specific categories.

        :param node: the node to be appended
        :param categories: positional arguments specifying the
            categories in which this node should be appended.
        """
        for category in categories:
            node.next[category] = self.last
            node.prev[category] = self.last.prev[category]

            # for the type checker
            prev_node = self.last.prev[category]
            assert prev_node is not None

            prev_node.next[category] = node
            self.last.prev[category] = node


class ItemGroup:
    """A data structure comprising multiple deques, backed by a producer."""

    GROUP_HOOK = "__ItemGroup_group"

    def __init__(
        self: ItemGroup,
        producer: Callable[[Optional[float]], ItemType],
        categorizer: Callable[[ItemType], str],
        timeout: Optional[float],
        **characterizers: Optional[CharacterizerType],
    ) -> None:
        """
        Initialise a new instance.

        :param producer: the producer from which this consumer gets
            items
        :param categorizer: a callable that categorizes an items.
        :param timeout: Number of seconds to wait for an item. A value
            of None means wait forever..
        :param characterizers: callables that extract item
            characteristics that we might want to test against.
        """
        self._multi_deque = MultiDeque(self.GROUP_HOOK, *characterizers.keys())
        self._producer = producer
        self._categorizer = categorizer
        self._characterizers = characterizers
        self._timeout = timeout

    @property
    def first(self: ItemGroup) -> Node:
        """
        Return the "first" node.

        This is a sentinel node, not the node containing the first data.

        :return: the first (sentinel) node.
        """
        return self._multi_deque.first

    @property
    def last(self: ItemGroup) -> Node:
        """
        Return the last node.

        This is a sentinel node, not the node containing the last data.

        :return: the last (sentinel) node.
        """
        return self._multi_deque.last

    def poll_producer(self: ItemGroup) -> None:
        """
        Poll the producer for an item.

        If a new item is available, append it to the data structure.

        :raises Empty: if no item is available
        """
        try:
            raw_item = self._producer(self._timeout)
        except Empty:
            # TODO: Log this.
            raise

        category = self._categorizer(raw_item)
        characteristics = {
            "item": raw_item,
            "category": category,
        }
        characterizer = self._characterizers[category]
        if characterizer is not None:
            characteristics = characterizer(characteristics)

        node = Node(characteristics)
        self._multi_deque.append(node, self.GROUP_HOOK, category)
        assert "__ItemGroup_group" in self.first.next

    def __getitem__(self: ItemGroup, category: Hashable) -> Iterable:
        """
        Return an iterable for a specified category.

        :param category: the category for which an iterable is required

        :return: an iterable for the category.
        """

        class _Iterable:  # pylint: disable=too-few-public-methods
            def __init__(
                self: _Iterable, item_group: ItemGroup, category: Hashable
            ):
                """
                Initialise a new instance.

                :param item_group: the data structure that backs this
                    iterable.
                :param category: the category for which this iterable
                    provides an iterator
                """
                self._item_group = item_group
                self._category = category

            def __iter__(self: _Iterable) -> ItemGroup.Iterator:
                """
                Return an iterator over the category.

                :return: an iterator over the category.
                """
                return ItemGroup.Iterator(self._item_group, self._category)

        return _Iterable(self, category)

    def __iter__(self: ItemGroup) -> ItemGroup.Iterator:
        """
        Return an iterator over the entire group.

        :return: an iterotor over the entire group.
        """
        return ItemGroup.Iterator(self, self.GROUP_HOOK)

    class Iterator:
        """An iterator for an specific category of an item group."""

        def __init__(
            self: ItemGroup.Iterator,
            item_group: ItemGroup,
            category: Hashable,
        ):
            """
            Initialise a new instance.

            :param item_group: the data structure that backs this
                iterator
            :param category: the category to iterate over
            """
            self._item_group = item_group
            self._category = category

            self._node = item_group.first

        def __iter__(self: ItemGroup.Iterator) -> ItemGroup.Iterator:
            """
            Return this iterator.

            :return: this iterator.
            """
            return self

        def __next__(self: ItemGroup.Iterator) -> Node:
            """
            Return the next node in this iterator.

            That is, return the node that comes after the current node,
            in the category over which we are iterating. If a next node
            is not present, this method polls the producer for new data
            before returning StopIteration

            :return: the next node

            :raises StopIteration: when this iterator is exhausted.
            """
            # https://docs.python.org/3/library/stdtypes.html#iterator.__next__
            # "Once an iterator's __next__() method raises StopIteration, it
            # must continue to do so on subsequent calls. Implementations that
            # do not obey this property are deemed broken."
            if self._node is self._item_group.last:
                raise StopIteration

            while self._node.next[self._category] is self._item_group.last:
                try:
                    self._item_group.poll_producer()
                except Empty:
                    # for the type checker
                    assert self._item_group.last is not None
                    self._node = self._item_group.last

                    raise StopIteration from Empty

            # for the type checker
            next_node = self._node.next[self._category]
            assert next_node is not None

            self._node = next_node

            return self._node


class MockConsumerGroup:
    """A group of consumers of items from a single producer."""

    _tracebackhide_ = True

    def __init__(
        self: MockConsumerGroup,
        producer: Callable[[Optional[float]], ItemType],
        categorizer: Callable[[Any], str],
        timeout: Optional[float],
        *consumers: str,
        **special_consumers: Optional[Callable[[Any], Dict]],
    ) -> None:
        """
        Initialise a new instance.

        :param producer: the producer from which this consumer gets
            items
        :param categorizer: a callable that categorizes items.
        :param timeout: optional number of seconds to wait for an item.
            If omitted, the default is 1 second. If explicitly set to
            None, the wait is forever.
        :param consumers: list of simple consumers in this group
        :param special_consumers: keyword arguments specifying special
            consumers in this group. Consumers are special if they have
            their own characterizer. Here, each key-value pair is the
            name of the consumer and the characterizer that it uses.
        """
        characterizers = {
            **special_consumers,
            **{consumer: None for consumer in consumers},
        }

        self._item_group = ItemGroup(
            producer, categorizer, timeout, **characterizers
        )
        self._group_view = ConsumerAsserter(self._item_group)

        self._views = {
            category: ConsumerAsserter(self._item_group[category])
            for category in characterizers
        }

    def assert_no_item(self: MockConsumerGroup) -> None:
        """Assert that no item is available in any category."""
        self._group_view.assert_no_item()

    def assert_item(
        self: MockConsumerGroup, *args: Any, lookahead: int = 1, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Assert that an item is available in any category.

        :param args: a single optional positional argument is allowed.
            If provided, it is asserted that there is an item available
            that is equal to the argument.
        :param lookahead: how many items to look through for the item
            that we are asserting. The default is 1, in which case we
            are asserting what the very next item will be. This will be
            the usual case in deterministic situations where we know
            the exact order in which items will arrive. In
            non-deterministic situations, we can provide a higher value.
            For example, a lookahead of 2 means that we are asserting
            the item will be one of the first two items.
        :param kwargs: characteristics that the item is expected to have

        :return: the matched item
        """
        return self._group_view.assert_item(
            *args, lookahead=lookahead, **kwargs
        )

    def __getitem__(
        self: MockConsumerGroup,
        category: str,
    ) -> ConsumerAsserter:
        """
        Return a view on a particular category.

        :param category: name of the category

        :return: a view on the category
        """
        return self._views[category]


class ConsumerAsserter:
    """A class that asserts against, and consume, available items."""

    _tracebackhide_ = True

    def __init__(
        self: ConsumerAsserter,
        iterable: Iterable,
    ) -> None:
        """
        Initialise a new instance.

        :param iterable: an iterable from which can be obtained an
            iterator of available items.
        """
        self._iterable = iterable

    def assert_no_item(self: ConsumerAsserter) -> None:
        """
        Assert that no item is available in this view of the group.

        :raises AssertionError: if an item is available
        """
        logger.debug("assert_no_item: Asserting no item available.")
        try:
            node = next(iter(self._iterable))
        except StopIteration:
            logger.debug("assert_no_item passed.")
            return

        logger.info(
            "assert_no_item failed; item retrieved is '%s'.",
            repr(node.payload),
        )
        raise AssertionError("Expected no item, but an item is available.")

    def assert_item(
        self: ConsumerAsserter,
        *args: Any,
        lookahead: int = 1,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Assert that an item is available in this view of the group.

        :param args: a single optional positional argument is allowed.
            If provided, it is asserted that there is an item available
            that is equal to the argument.
        :param lookahead: how many items to look through for the item
            that we are asserting. The default is 1, in which case we
            are asserting what the very next item will be. This will be
            the usual case in deterministic situations where we know
            the exact order in which items will arrive. In
            non-deterministic situations, we can provide a higher value.
            For example, a lookahead of 2 means that we are asserting
            the item will be one of the first two items.
        :param kwargs: characteristics that the item is expected to have

        :returns: the matched item

        :raises AssertionError: if the asserted item does not arrive
            in time
        """
        assert (
            len(args) <= 1
        ), "Only one positional argument to assert_item is permitted"

        log_clauses = []
        if args:
            log_clauses.append(f"exactly equal to {repr(args[0])}")
        if kwargs:
            log_clauses.append(f"with characteristics {kwargs}")
        logger.debug(
            "assert_item: Asserting item within next %d item(s), %s.",
            lookahead,
            ", and ".join(log_clauses),
        )

        for node in itertools.islice(iter(self._iterable), 0, lookahead):
            if len(args) == 1 and node.payload["item"] != args[0]:
                logger.debug(
                    "assert_item: Positional argument does not exactly equal "
                    "item '%s'.",
                    repr(node.payload["item"]),
                )
                continue

            for key, value in kwargs.items():
                if key not in node.payload:
                    logger.debug(
                        "assert_item: No '%s' characteristic in item '%s'.",
                        key,
                        repr(node.payload),
                    )
                    break
                if node.payload[key] != value:
                    logger.debug(
                        "assert_item: '%s' characteristic is not '%s' in item "
                        "'%s'.",
                        key,
                        value,
                        repr(node.payload),
                    )
                    break
            else:
                payload = node.payload
                node.drop()
                logger.debug(
                    "assert_item passed: found matching item '%s'.",
                    repr(payload),
                )
                return payload

        logger.debug(
            "assert_item failed: no matching item within the first %d items",
            lookahead,
        )

        raise AssertionError(
            f"Expected matching item within the first {lookahead} items."
        )
