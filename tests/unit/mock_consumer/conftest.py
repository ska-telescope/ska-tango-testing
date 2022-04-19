"""This module implements test harness for testing mock consumers."""
from __future__ import annotations

import multiprocessing
import queue
import threading
import time
from typing import Any, Callable, Optional, Type, Union

import pytest
from _pytest.fixtures import SubRequest
from typing_extensions import Protocol

from ska_tango_testing.mock_consumer import MockConsumer, ProducerProtocol


class TestingProducerProtocol(ProducerProtocol, Protocol):
    """
    Interface specification for producers used in testing.

    This is an extension of `ProducerProtocol`, with an extra method
    that allows a test to schedule production of an item .
    """

    def schedule_put(
        self: TestingProducerProtocol, delay: float, item: Any
    ) -> None:
        """
        Schedule production of an item after a specified delay.

        :param delay: the time in seconds before the item should be
            produced.
        :param item: the item to be produced.
        """
        ...


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
    Return a producer to test the consumer under test against.

    This pytest fixture is parametrized to return three kinds of
    producer: a thread that pushes to a queue.SimpleQueue, a process
    that pushes to a multiprocessing.Queue, and a process that pushes to
    a multiprocessing.Pipe.

    :param request: A pytest object giving access to the requesting test
        context.

    :return: a producer to be used in testing
    """

    class QueueBasedProducer:
        """
        A producer that puts produced items onto a queue.

        It gets its runner and queue from provided factories. If the
        runner factory is `threading.Thread`, then the queue factory
        might be `queue.SimpleQueue` or `queue.Queue`. If the runner
        factory is `multiprocessing.Process`, then the queue factory
        should probably be `multiprocessing.Queue`.
        """

        def __init__(
            self: QueueBasedProducer,
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

        def get(
            self: QueueBasedProducer, timeout: Optional[float] = None
        ) -> Any:
            """
            Return the next item produced.

            :param timeout: how long, in seconds, to wait for an item to
                arrive, before giving up and raising `queue.Empty`. The
                default is 1 second. A value of None means wait forever.

            :return: the next time produced
            """
            return self._queue.get(timeout=timeout)

        def schedule_put(
            self: QueueBasedProducer, delay: float, item: Any
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

    class PipeBasedProducer:
        """A producer that pushes items down a `multiprocessing.Pipe`."""

        def __init__(self: PipeBasedProducer) -> None:
            """Initialise a new instance."""
            (self._receiver, self._sender) = multiprocessing.Pipe(False)

        # TODO: Why are DAR401 and DAR402 raised here?
        def get(
            self: PipeBasedProducer, timeout: Optional[float] = None
        ) -> Any:  # noqa: DAR401
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
            self: PipeBasedProducer, delay: float, item: Any
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
                sender.send(item)

            multiprocessing.Process(
                target=_put_later, args=(self._sender, delay, item)
            ).start()

    producers: dict[str, Callable[[], TestingProducerProtocol]] = {
        "threading": lambda: QueueBasedProducer(
            queue.SimpleQueue,
            threading.Thread,
        ),
        "multiprocessing_with_queue": lambda: QueueBasedProducer(
            multiprocessing.Queue, multiprocessing.Process
        ),
        "multiprocessing_with_pipe": PipeBasedProducer,
    }

    return producers[request.param]()


@pytest.fixture()
def consumer(producer: ProducerProtocol) -> MockConsumer:
    """
    Return a consumer that is ready to consume items from its producer.

    :param producer: the producer that the consumer will consume from.

    :return: a consumer.
    """

    def name_value_splitter(item: str) -> dict:
        (name, value_str) = item.split("=", maxsplit=1)
        return {"name": name, "value": int(value_str)}

    return MockConsumer(producer, characterizer=name_value_splitter)
