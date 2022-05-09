"""This module provides a :py:class:`QueueGroup` class."""
from __future__ import annotations

import itertools
import weakref
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

ItemType = TypeVar("ItemType")


class Node:
    """A single node in a multiply-linked double-linked deque structure."""

    def __init__(self: Node, payload: Any) -> None:
        """
        Initialise a new instance.

        :param payload: the payload of the node.
        """
        self.prev: DefaultDict[Hashable, Optional[Node]] = defaultdict(None)
        self.next: DefaultDict[Hashable, Optional[Node]] = defaultdict(None)
        self.payload = payload
        self._dropped = False

    @property
    def dropped(self: Node) -> bool:
        """
        Return whether this node has been dropped.

        :return: whether this node has been dropped.
        """
        return self._dropped

    def drop(self: Node) -> None:
        """Drop this node."""
        # We don't want this node any more, but we can't just dike it out of
        # the data structure and let it be garbage-collected, because there
        # might be external references to it, e.g. from an iterator. But we can
        # weaken its internal references, thus allowing it to be
        # garbage-collected once the external references to it are all gone.
        # Diking it out of the data structure still has to happen, but we defer
        # that to the __del__ method.
        for category in self.next:
            # for the type checker
            prev_node = self.prev[category]
            assert prev_node is not None
            next_node = self.next[category]
            assert next_node is not None

            prev_node.next[category] = weakref.proxy(self)
            next_node.prev[category] = weakref.proxy(self)

        self._dropped = True

        # jettison the payload in case it is big enough to matter
        self.payload = None

    def __del__(self: Node) -> None:
        """Clean up before this node is deleted."""
        # Dike this node out of the data structure before it gets deleted
        # TODO: Not thread-safe -- this could be called from the GC thread
        # when a neighbouring node is updating this node's links. Fix might
        # be to make "next" and "prev" into properties, and then mediate all
        # modifications through a lock.
        for category in self.next:
            # for the type checker
            prev_node = self.prev[category]
            next_node = self.next[category]

            if prev_node is not None:
                prev_node.next[category] = next_node
            if next_node is not None:
                next_node.prev[category] = prev_node


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
        **characterizers: Optional[Callable[[ItemType], Dict]],
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
        characterizer = self._characterizers[category]
        if characterizer is None:
            characteristics = {}
        else:
            characteristics = characterizer(raw_item)

        node = Node((category, raw_item, characteristics))
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

            while True:
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
                if not self._node.dropped:
                    break

            return self._node


class MockConsumerGroup:
    """A group of consumers of items from a single producer."""

    def __init__(
        self: MockConsumerGroup,
        producer: Callable[[Optional[float]], ItemType],
        categorizer: Callable[[Any], str],
        timeout: Optional[float],
        **characterizers: Optional[Callable[[Any], Dict]],
    ) -> None:
        """
        Initialise a new instance.

        :param producer: the producer from which this consumer gets
            items
        :param categorizer: a callable that categorizes items.
        :param timeout: optional number of seconds to wait for an item.
            If omitted, the default is 1 second. If explicitly set to
            None, the wait is forever.
        :param characterizers: dictionary of characterizer callables
        """
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
    ) -> None:
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
        """
        self._group_view.assert_item(*args, lookahead=lookahead, **kwargs)

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
        try:
            _ = next(iter(self._iterable))
        except StopIteration:
            return

        raise AssertionError("Expected no item, but an item is available.")

    def assert_item(
        self: ConsumerAsserter,
        *args: Any,
        category: Optional[str] = None,
        lookahead: int = 1,
        **kwargs: Any,
    ) -> None:
        """
        Assert that an item is available in this view of the group.

        :param args: a single optional positional argument is allowed.
            If provided, it is asserted that there is an item available
            that is equal to the argument.
        :param category: optional category that we expect the
            item to belong to.
        :param lookahead: how many items to look through for the item
            that we are asserting. The default is 1, in which case we
            are asserting what the very next item will be. This will be
            the usual case in deterministic situations where we know
            the exact order in which items will arrive. In
            non-deterministic situations, we can provide a higher value.
            For example, a lookahead of 2 means that we are asserting
            the item will be one of the first two items.
        :param kwargs: characteristics that the item is expected to have

        :raises AssertionError: if the asserted item does not arrive
            in time
        """
        assert (
            len(args) <= 1
        ), "Only one positional argument to assert_item is permitted"

        for node in itertools.islice(iter(self._iterable), 0, lookahead):
            (item_category, raw_item, characteristics) = node.payload
            if category is not None and item_category != category:
                continue
            if len(args) == 1 and raw_item != args[0]:
                continue

            for key, value in kwargs.items():
                if key not in characteristics:
                    break
                if characteristics[key] != value:
                    break
            else:
                node.drop()
                return

        raise AssertionError(
            f"Expected matching item within the first {lookahead} items."
        )
