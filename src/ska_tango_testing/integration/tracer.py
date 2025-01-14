"""Tango proxy client which can trace change events from Tango devices."""

from enum import Enum
from typing import Callable, SupportsFloat

import tango

from .event import ReceivedEvent
from .event.storage import EventStorage
from .event.subscriber import TangoSubscriber
from .query.base import EventQuery
from .query.n_events_match import NEventsMatchQuery


class TangoEventTracer:
    """Tango proxy client which can trace change events from Tango devices.

    MISSION: to represent a tango proxy client that can subscribe to
    change events from multiple attributes and multiple devices,
    store the received events as
    they are notified (in a thread-safe way), and support queries
    with timeouts to check if and when and who sent certain events.

    This class allows you to:

    - subscribe to change events for a specific attribute of a Tango device
      (see :py:meth:`subscribe_event`);
    - store and access the events in a thread-safe way
      (see :py:attr:`events`);
    - query the stored events based on a predicate function that
      selects which events satisfy some criteria and a timeout,
      which permits you to wait for that criteria to be satisfied
      (see :py:meth:`query_events`) or based on any custom query
      (see :py:meth:`evaluate_query`).

    Here there follows 3 usage examples: a first very minimal one,
    a second one more suitable for most of the end-users, and a third
    one that shows how you can evaluate any kind of custom object-queries.

    **Usage Example 1**: test where you subscribe to a device
    and assert that it exists exactly one state change event
    to a TARGET_STATE within 10 seconds:

    .. code-block:: python

        def test_attribute_change():

            tracer = TangoEventTracer()
            tracer.subscribe_event("sys/tg_test/1", "State")

            # do something that triggers the event
            # ...

            assert len(tracer.query_events(
                lambda e:
                    e.has_device("sys/tg_test/1") and
                    e.has_attribute("State") and
                    e.attribute_value == TARGET_STATE,
                timeout=10)) == 1

    **Usage Example 2**: as an end-user of this module, you can combine
    this tracer with `assertpy <https://assertpy.github.io/index.html>`_
    custom assertions to write readable and powerful tests. Here is an example
    of how to use the assertions we provide in
    :py:mod:`ska_tango_testing.integration.assertions`:

    .. code-block:: python

        from assertpy import assert_that

        def test_attribute_change(tracer): # tracer is a fixture

            tracer.subscribe_event("sys/tg_test/1", "State")

            # do something that triggers the event

            assert_that(tracer).described_as(
                "There must be a state change from "
                "INITIAL_STATE to TARGET_STATE within 10 seconds."
            ).within_timeout(10).has_change_event_occurred(
                device_name="sys/tg_test/1",
                attribute_name="State",
                attribute_value=TARGET_STATE,
                previous_value=INITIAL_STATE,
            )

    **Usage Example 3**: evaluate any kind of query. The usage shown
    in the first example is just a quick shortcut to use the tracer in
    a simplified way. The tracer, potentially, can evaluate any kind of
    query object, given it is a subclass of
    :py:class:`~ska_tango_testing.integration.query.base.EventQuery`.
    You can find a collection of (configurable) query objects
    in the :py:mod:`~ska_tango_testing.integration.query` module.
    Here an example of how you can make the same exact interrogation
    of the first example, but using query objects:

    .. code-block:: python

        query = NSateChangesQuery(
            device_name="sys/tg_test/1",
            attribute_name="State",
            attribute_value=TARGET_STATE,
            timeout=10,
        )
        tracer.evaluate_query(query)

    **Tracer Mechanics**: here it follows a brief explanation of how the
    tracer works internally. The tracer is a tool that captures, stores and
    interrogates events. It does so by using four main support classes:

    - :py:class:`~ska_tango_testing.integration.event.ReceivedEvent` is the
      class that represents the events captured by the tracer;
    - :py:class:`~ska_tango_testing.integration.event.subscriber.TangoSubscriber`
      is used to subscribe to the events and react to new events by storing
      them in the event storage;
    - :py:class:`~ska_tango_testing.integration.event.storage.EventStorage`
      is used to store the events in a thread-safe way and to update all
      the pending queries when a new event is received;
    - :py:class:`~ska_tango_testing.integration.query.base.EventQuery`
      and its subclasses are the interrogations on the stored events.

    The queries are reactive objects capable of putting the process in a
    waiting state until the query is satisfied or the timeout is reached
    and in the meantime auto-update themselves when new events are received.

    **Thread Safety**: the tracer is thread-safe. It uses a thread-safe
    storage for the events and a thread-safe subscriber to the events.
    The only part that is not yet fully thread-safe are the queries. The
    queries base class is thread-safe, but the custom queries you can
    write may expose variables that could be not thread-safe (so, don't
    access queries variables from outside until the evaluation is done
    and you will be safe; query base method such as ``status()``,
    ``describe()``, etc. are instead thread safe and can be accessed).
    """  # pylint: disable=line-too-long # noqa: E501

    def __init__(
        self, event_enum_mapping: dict[str, type[Enum]] | None = None
    ):
        """Initialize the event collection and the lock.

        :param event_enum_mapping: An optional mapping of attribute names
            to enums (to handle typed events).
        """
        # (thread-safe) storage for the received events
        self._events_storage = EventStorage()

        # (thread-safe) subscriber to the events
        self._subscriber = TangoSubscriber(event_enum_mapping)

    def __del__(self) -> None:
        """Teardown the object and unsubscribe from all subscriptions."""
        self.unsubscribe_all()
        self.clear_events()

    # #############################
    # Access to stored events

    @property
    def events(self) -> list[ReceivedEvent]:
        """A copy of the currently stored events (thread-safe).

        :return: A copy of the stored events.
        """  # noqa: D402
        return self._events_storage.events

    def clear_events(self) -> None:
        """Clear all stored events."""
        self._events_storage.clear_events()

    # #############################
    # Subscription and
    # event handling

    def subscribe_event(
        self,
        device_name: "str | tango.DeviceProxy",
        attribute_name: str,
        dev_factory: Callable[[str], tango.DeviceProxy] | None = None,
    ) -> None:
        """Subscribe to change events for a Tango device attribute.

        It's the same as subscribing to a change event in a Tango
        device, but the received events are stored in the tracer instance
        (in a thread-safe way) and can be accessed later with
        :py:meth:`query_events`, with :py:attr:`events` or with
        custom assertions. Every time a change event will happen on
        Tango device attribute, the tracer will receive it and store it.

        Usage example:

        .. code-block:: python

            # you can provide just the device name and the attribute name
            tracer.subscribe_event("sys/tg_test/1", "State")

            # if you already have a device proxy, you can pass it directly
            tracer.subscribe_event(device_proxy, "State")

            # if you have the name of the device, but for some reason
            # you don't want us to create the device proxy using the
            # default constructor DeviceProxy, you can provide a factory method

            def custom_factory(device_name: str) -> tango.DeviceProxy:
                return tango.DeviceProxy(device_name)

            tracer.subscribe_event(
                "sys/tg_test/1", "State",
                dev_factory=custom_factory
            )

        **NOTE**: when you subscribe to an event, you will automatically
        receive the current attribute value as an event (or, in other words,
        the last "change" that happened). Take this into account when you
        write your queries.

        :param device_name: The name of the Tango target device. Alternatively,
            if you already have a device proxy, you can pass it directly.
        :param attribute_name: The name of the attribute to subscribe to.
        :param dev_factory: A device factory method to get the device proxy.
            If not specified, the device proxy is created using the
            default constructor :py:class:`tango.DeviceProxy`.

        :raises tango.DevFailed: If the subscription fails. A common reason
            for this is that the attribute is not subscribable (because the
            developer didn't set it to be "event-firing" or pollable).
            An alternative reason is that the device cannot be
            reached or it has no such attribute.
        :raises ValueError: If the device_name is not a string or a
            DeviceProxy.
        """  # noqa: DAR402
        self._subscriber.subscribe_event(
            device_name,
            attribute_name,
            self._add_event,
            dev_factory=dev_factory,
        )

    def _add_event(self, event: ReceivedEvent) -> None:
        """Store an event and update all pending queries.

        NOTE: all pending queries are updated through a subscription mechanism
        to the events storage. Every time this method is called, all the
        pending queries are notified and can evaluate the new event.

        :param event: The event to add.
        """
        self._events_storage.store(event)

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all subscriptions."""
        self._subscriber.unsubscribe_all()

    # #############################
    # Querying stored
    # and future events

    def query_events(
        self,
        predicate: Callable[[ReceivedEvent], bool],
        timeout: SupportsFloat = 0.0,
        target_n_events: int = 1,
    ) -> list[ReceivedEvent]:
        """Query stored and future events with a predicate and a timeout.

        This method is a shortcut that lets you select the events that match
        a certain criteria (predicate), optionally waiting for a certain time
        span (timeout) if the criteria are not satisfied immediately.
        The method returns
        all the matching events or an empty list if there are any. The
        predicate is essentially a function that takes a
        :py:class:`~ska_tango_testing.integration.event.ReceivedEvent`
        as input and evaluates if the event
        matches the desired criteria (returning `True` if it does)
        or not (`False` otherwise).

        **NOTE**: If you don't provide a timeout, the method will evaluate
        all the events that are already stored and return immediately the
        matching ones. If you provide a timeout, the method will act as a
        a blocking operation that waits ``target_n_events`` to
        match the predicate or the timeout to be reached.

        Usage example:

        .. code-block:: python

            # (you already made the right subscriptions)

            # query just past events to get all events from a device X
            # with attribute Y
            all_events = tracer.query_events(
                lambda e: e.has_device("sys/tg_test/1") and
                          e.has_attribute("State")
                          # NOTE: making this call instead of
                          # e.attribute_value == "State" prevents
                          # case sensitivity issues
            )

            # query events aiming to get at least one event
            # from device X with attribute Y that has a certain value
            # (waiting at most 10 seconds if the event is not there yet)
            future_query = tracer.query_events(
                # you can use directly the device proxy instead of the name
                lambda e: e.has_device(X_dev_proxy) and
                          e.has_attribute("State") and
                          e.current_value == TARGET_STATE,
                timeout=10
            )

        **FINAL NOTE**: this method is a shortcut to use the tracer in a
        simplified way. The tracer, potentially, can evaluate any kind of
        query object. Please check :py:meth:`evaluate_query` for more.

        :param predicate: A function that takes an event as input and returns.
            True if the event matches the desired criteria.
        :param timeout: The time span in seconds to wait for a matching event
            (optional). If not specified or passed 0,
            the method returns immediately.

            **NOTE**: if the timeout is < 0 or infinite,
            it will be considered 0. None values are in theory not supported,
            but they are converted to 0.0 to guarantee retro-compatibility.

            **TECHNICAL NOTE**: Timeout may not always be a number but
            something that can be casted to a float. This is useful for
            guaranteeing retro-compatibility in custom assertions written
            before 0.7.2, where the timeout was a number and not an object
            and some users may still have code where they directly pass
            the timeout object, ignoring that now it is not a number anymore.

        :param target_n_events: How many events do you expect to find with this
            query? If in past events (events which happen prior to the moment
            in which the query is evaluated) you don't reach the target number,
            the method will wait till you reach the target number or you reach
            the timeout. Defaults to 1 so in case of a waiting loop, the method
            will return the first event.

            If you set this to a number greater than 1 (**and ``timeout``
            is not ``None``**) the method will wait until you reach the
            target number of events that match the predicate. E.g., if you
            set this to 10, at query time there are 4 matching events it will
            wait for 6 more events to match the predicate. If you set this
            to 10, at query time there are 12 matching events it will return
            immediately all the 12 matching events.

            It must be greater or equal to 1.

        :return: all matching events within the timeout
            period if there are any, or an empty list if there are none.

        :raises ValueError: If the timeout or the target number of events
            does not meet the requirements (see above).
        """  # noqa: DAR402
        # Create a query to get at least N matching
        # events within the timeout
        query = NEventsMatchQuery(
            lambda event, _: predicate(event), target_n_events, timeout
        )

        # Evaluate it
        self.evaluate_query(query)

        # extract and return the matching events
        return query.matching_events

    def evaluate_query(self, query: EventQuery) -> None:
        """Evaluate a query over the current and future captured events.

        A :py:class:`~ska_tango_testing.integration.query.EventQuery`
        is a query over the tracer's present and eventually future events
        (if a timeout is specified). This method takes an already built
        and not yet evaluated query object and evaluates it.
        The evaluation is a blocking operation that waits for the query
        to be satisfied or for the timeout to be reached.

        To know more about the queries, please check the
        :py:mod:`~ska_tango_testing.integration.query` module, where you
        will find the base class and some already built query objects
        you can use.

        This method returns nothing, because eventual query results are
        supposed to be accessed through the query object itself. The most
        basic and common result is its success status, which can be
        accessed through the
        :py:meth:`~ska_tango_testing.integration.query.EventQuery.succeeded`
        method.

        :param query: The query to evaluate.
        :raises ValueError: If the query you are trying to evaluate is already
            being evaluated by another thread.
        """  # pylint: disable=line-too-long # noqa: DAR402 E501
        query.evaluate(self._events_storage)
