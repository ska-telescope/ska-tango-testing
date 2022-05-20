"""This module implements test harness for testing mock consumers."""
from __future__ import annotations

import multiprocessing
import queue
import threading
import time
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    List,
    NamedTuple,
    Optional,
    Type,
    Union,
)

import pytest
from _pytest.fixtures import SubRequest
from typing_extensions import Protocol

from ska_tango_testing import ItemType, MockConsumerGroup


class FakeItem(NamedTuple):
    """A item class for use in testing."""

    name: str
    value: Any
    quality: str


class TestingProducerProtocol(Protocol):
    """
    Interface specification for producers used in testing.

    This is an extension of `ProducerProtocol`, with an extra method
    that allows a test to schedule production of an item .
    """

    __test__: bool = False  # So that pytest doesn't try to collect this class

    def __call__(
        self: TestingProducerProtocol,
        timeout: Optional[float],
    ) -> ItemType:
        """
        Get the next item.

        :param timeout: Number of seconds to wait for an item to arrive,
            or None to wait forever

        :return: the next item

        :raises queue.Empty: if no item becomes available in time.
        """  # noqa: DAR202, DAR402
        ...

    def schedule_put(  # pylint: disable=no-self-use
        self: TestingProducerProtocol,
        delay: float,  # pylint: disable=unused-argument
        item: ItemType,  # pylint: disable=unused-argument
    ) -> None:
        """
        Schedule production of an item after a specified delay.

        :param delay: the time in seconds before the item should be
            produced.
        :param item: the item to be produced.
        """
        ...


class _QueueBasedProducer(TestingProducerProtocol):
    """
    A producer that puts produced items onto a queue.

    It gets its runner and queue from provided factories. If the runner
    factory is `threading.Thread`, then the queue factory might be
    `queue.SimpleQueue` or `queue.Queue`. If the runner factory is
    `multiprocessing.Process`, then the queue factory should probably be
    `multiprocessing.Queue`.
    """

    def __init__(  # pylint: disable=super-init-not-called
        self: _QueueBasedProducer,
        queue_factory: Union[
            Type[queue.SimpleQueue], Type[multiprocessing.Queue]
        ],
        runner_factory: Union[
            Type[threading.Thread], Type[multiprocessing.Process]
        ],
    ) -> None:
        """
        Initialise a new instance.

        :param queue_factory: callable that returns a queue to be
            used by this producer
        :param runner_factory: callable that return a
            `threading.Thread` or `multiprocessing.Process`
        """
        self._queue = queue_factory()
        self._runner_factory = runner_factory

    def __call__(
        self: _QueueBasedProducer, timeout: Optional[float]
    ) -> ItemType:
        """
        Return the next item produced.

        :param timeout: how long, in seconds, to wait for an item to
            arrive, before giving up and raising `queue.Empty`. The
            default is 1 second. A value of None means wait forever.

        :return: the next time produced
        """
        return self._queue.get(timeout=timeout)

    def schedule_put(
        self: _QueueBasedProducer, delay: float, item: ItemType
    ) -> None:
        """
        Schedule production of an item after a specified delay.

        :param delay: the time in seconds before the item should be
            produced.
        :param item: the item to be produced.
        """

        def _put_later(
            target_queue: queue.Queue, delay: float, item: Any
        ) -> None:
            time.sleep(delay)
            target_queue.put(item)

        self._runner_factory(
            target=_put_later, args=(self._queue, delay, item)
        ).start()


class _PipeBasedProducer(TestingProducerProtocol):
    """A producer that pushes items down a `multiprocessing.Pipe`."""

    def __init__(  # pylint: disable=super-init-not-called
        self: _PipeBasedProducer,
    ) -> None:
        """Initialise a new instance."""
        self._sender_lock = multiprocessing.Lock()
        (self._receiver, self._sender) = multiprocessing.Pipe(False)

    # TODO: Why are DAR401 and DAR402 raised here?
    def __call__(
        self: _PipeBasedProducer, timeout: Optional[float]
    ) -> ItemType:  # noqa: DAR401
        """
        Return the next item produced.

        :param timeout: how long, in seconds, to wait for an item to
            arrive, before giving up and raising `queue.Empty`. The
            default is 1 second. A value of None means wait forever.

        :return: the next time produced

        :raises queue.Empty: if there is still no item available at the
            end of the timeout period
        """  # noqa: DAR402
        if self._receiver.poll(timeout):
            return self._receiver.recv()
        raise queue.Empty()

    def schedule_put(
        self: _PipeBasedProducer, delay: float, item: ItemType
    ) -> None:
        """
        Schedule production of an item after a specified delay.

        :param delay: the time in seconds before the item should be
            produced.
        :param item: the item to be produced.
        """

        def _put_later(
            sender: multiprocessing.connection.Connection,
            delay: float,
            item: Any,
        ) -> None:
            time.sleep(delay)
            with self._sender_lock:
                sender.send(item)

        multiprocessing.Process(
            target=_put_later, args=(self._sender, delay, item)
        ).start()


@pytest.fixture(
    name="producer",
    params=[
        "threading",
        "multiprocessing_with_queue",
        "multiprocessing_with_pipe",
    ],
)
def producer_fixture(request: SubRequest) -> TestingProducerProtocol:
    """
    Return a producer for use in testing.

    This fixture is parametrised to return a producer from each of its
    three producer factories. Thus, any test that uses this fixture will
    be run three times, once against each producer type.

    :param request: A pytest object giving access to the requesting test
        context.

    :return: a producer for use in testing
    """
    factories = {
        "threading": lambda: _QueueBasedProducer(
            queue.SimpleQueue, threading.Thread
        ),
        "multiprocessing_with_queue": lambda: _QueueBasedProducer(
            multiprocessing.Queue, multiprocessing.Process
        ),
        "multiprocessing_with_pipe": _PipeBasedProducer,
    }
    factory = factories[request.param]
    return factory()


@pytest.fixture(name="categories")
def categories_fixture() -> List[Hashable]:
    """
    Return a list of the categories used in testing.

    :return: a list of the categories used in testing.
    """
    return ["status", "voltage", "current"]


@pytest.fixture(name="item_library")
def item_library_fixture() -> Dict[str, FakeItem]:
    """
    Return a library of items for use in testing.

    :return: a library of items for use in testing.
    """
    return {
        "voltage_1": FakeItem("voltage", pytest.approx(11.1), "OK"),
        "voltage_2": FakeItem("voltage", pytest.approx(22.2), "OK"),
        "voltage_3": FakeItem("voltage", pytest.approx(33.3), "OK"),
        "bad_voltage": FakeItem("voltage", pytest.approx(99999.9), "PHOOEY"),
        "current_1": FakeItem("current", pytest.approx(10.0), "OK"),
        "current_2": FakeItem("current", pytest.approx(11.1), "OK"),
        "current_3": FakeItem("current", pytest.approx(12.2), "OK"),
        "status_connected": FakeItem("status", "CONNECTED", "OK"),
        "status_disconnected": FakeItem("status", "DISCONNECTED", "OK"),
    }


@pytest.fixture()
def voltage(item_library: Dict[str, FakeItem]) -> FakeItem:
    """
    Return an item from the item library for a voltage.

    This is just syntactic sugar for the benefit of all the tests that
    only need one item.

    :param item_library: a library of items for use in testing

    :return: an item from the item library for a voltage.
    """
    return item_library["voltage_1"]


@pytest.fixture(name="categorizer")
def categorizer_fixture() -> Callable[[FakeItem], Hashable]:
    """
    Return a callable that returns an item's category.

    :return: a callable that can be called with an item, and returns the
        item's category
    """
    return lambda item: item.name


@pytest.fixture(name="characterizer")
def characterizer_fixture() -> Callable[[Dict], Dict]:
    """
    Return a callable that extracts an item's characteristics.

    :return: a callable that extracts an item's characteristics.
    """

    def _characteristics(characteristics: Dict) -> Dict:
        item = characteristics["item"]
        characteristics.update(
            {
                "name": item.name,
                "value": item.value,
                "quality": item.quality,
            }
        )
        return characteristics

    return _characteristics


@pytest.fixture()
def consumer_group(
    producer: TestingProducerProtocol,
    categorizer: Callable[[FakeItem], str],
    characterizer: Callable[[FakeItem], Dict],
    categories: List[str],
) -> MockConsumerGroup:
    """
    Return a consumer group that is ready to consume items from its producers.

    :param producer: the producer that the consumer will consume from.
    :param categorizer: a callable that categorizes an items.
    :param characterizer: a callable that looks at an item and returns
        item characteristics that we might want to assert against.
    :param categories: names of the queues into which items will be

    :return: a consumer group.
    """
    category_filters = {category: characterizer for category in categories}
    return MockConsumerGroup(producer, categorizer, 1.0, **category_filters)
