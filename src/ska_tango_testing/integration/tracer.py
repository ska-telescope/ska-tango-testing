"""Tango proxy client which can trace change events from Tango devices.

MISSION: to represent a tango proxy client that can subscribe to
change events from multiple attributes and multiple devices,
store the received events as
they are notified (in a thread-safe way), and support queries
with timeouts to check if and when and who sent certain events.

The main class to do so is
:py:class:`~ska_tango_testing.integration.TangoEventTracer`, which
collects :py:class:`~ska_tango_testing.integration.event.ReceivedEvent`
instances and allows you to query them, directly or through custom
assertions
(:py:mod:`ska_tango_testing.integration.assertions`). To do so, it
uses a few supporting classes:

- :py:class:`~ska_tango_testing.integration.event_storage.EventStorage`
    to store the events in a thread-safe way and to notify the
    queries when new events are received;
- :py:class:`~ska_tango_testing.integration.subscriber.TangoSubscriber`
    to subscribe to the events and store them in the event storage.
- :py:class:`~ska_tango_testing.integration.queries.NEventsMatchQuery`
    to query the events with a predicate and a timeout.
"""

from enum import Enum
from typing import Callable, SupportsFloat

import tango

from .event import ReceivedEvent
from .event_storage import EventStorage
from .queries import NEventsMatchQuery
from .subscriber import TangoSubscriber


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
      (see :py:meth:`query_events`).

    Usage example 1: test where you subscribe to a device
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
                    e.current_value == TARGET_STATE,
                timeout=10)) == 1

    Queries are a powerful tool to make assertions on specific complex
    behaviours of a device. For example, you may want to check that
    a certain event is sent after another event, or that a certain
    event is sent only when a certain condition is satisfied.

    **IMPORTANT NOTE**: If you are an end-user of this module, you will
    probably use the tracer together with the already provided
    `assertpy <https://assertpy.github.io/index.html>`_
    custom assertions, which are implemented in
    :py:mod:`ska_tango_testing.integration.assertions`.
    Your code will likely look like this:

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
                current_value=TARGET_STATE,
                previous_value=INITIAL_STATE,
            )

    See :py:mod:`ska_tango_testing.integration.predicates`
    for more details.

    **NOTE**: some events attributes even if technically they are
    primitive types (like integers or strings), they can be
    semantically typed with an ``Enum`` (e.g., a state machine attribute can be
    represented as an integer, but it is semantically a state). To handle
    those cases, when you create an instance of the tracer, you can
    provide a mapping of attribute names to enums (see the
    :py:class:`ska_tango_testing.integration.typed_event.EventEnumMapper`
    class). When you subscribe to an event, the tracer will automatically
    convert the received event to the corresponding enum, so when you
    print the event as a string, you can see the state as a human readable
    label, instead of a raw value.

    Usage example 2: test where you subscribe to a device with a typed event

    .. code-block:: python

        import pytest
        from assertpy import assert_that
        from enum import Enum

        # define the enum (or import it from somewhere)
        class MyEnum(Enum):
            STATE1 = 1
            STATE2 = 2


        @pytest.fixture
        def typed_tracer():
            return TangoEventTracer(
                event_enum_mapping={
                    "State": MyEnum
                }
            )

        def test_attribute_change(typed_tracer):

            typed_tracer.subscribe_event("sys/tg_test/1", "State")

            # do something that triggers the event

            assert_that(tracer).described_as(
                "There must be a state change from "
                "STATE1 to STATE2 within 10 seconds."
            ).within_timeout(10).has_change_event_occurred(
                device_name="sys/tg_test/1",
                attribute_name="State",
                current_value=MyEnum.STATE2,
                previous_value=MyEnum.STATE1,
            )

            # If there you have a failure, the error message will
            # be more human readable:
            # - without the enum mapping, you would see the raw values
            #  of the states (e.g., "attribute_value=2")
            # - with the enum mapping, you see the enum labels
            #  (e.g., "attribute_value=MyEnum.STATE2")

    **NOTE**: when you subscribe to an event, you will automatically
    receive the current attribute value as an event (or, in other words,
    the last "change" that happened). Take this into account when you
    write your queries.

    **ANOTHER NOTE**: just a note about how event handling and queries with
    timeouts are implemented. The event collection is implemented through
    the tango ``subscribe_event`` method, which activates a callback
    that updates the internal list of events. Since the callback is
    asynchronous,
    the access to the events is protected by a lock (to avoid that
    different callbacks access the events at the same time, or indeed
    that a query accesses the events while they are being updated).
    The queries with timeouts are implemented by creating a sort of
    "pending query" object and waiting for its conditions to be satisfied
    through a signal. The pending queries are updated every time a new
    event happens and, when the conditions are met, the signal is set
    and the waiting thread is unlocked. Since the queries are accessed
    asynchronously by the main test thread and by the various callbacks,
    a further lock to protect them is added.
    A third (not essential) lock is used to protect the
    subscriptions, so they can potentially
    be created and deleted from different
    threads (it is not a primary use case, but it is technically possible).

    *To prevent the risk of deadlock we purposely avoided the acquiring of two
    locks together (in each point of the code it is acquired at most one
    of the three locks). To prevent the risk of infinite signal waits, when a
    wait happen, it's ensured that it has been specified a timeout. Moreover,
    waits don't ever keep locks. For now, locks aren't reentrant, so if you
    modify this code be careful to not acquire a lock that you already have.*
    """

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

        NOTE: all pending queries are updated trough a subscription mechanism
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

        Queries are a tool to retrieve events that match a certain criteria
        (predicate), optionally waiting for a certain time span (timeout) if
        the criteria are not satisfied immediately. The method returns
        all the matching events or an empty list if there are any. The
        predicate is essentially a function that takes a
        :py:class:`~ska_tango_testing.integration.event.ReceivedEvent`
        as input and evaluates if the event
        matches the desired criteria (returning `True` if it does)
        or not (`False` otherwise).

        The timeout is optional but highly recommended, because it allows
        you to wait for a certain event to happen (e.g., a state change)
        within a certain time span. Essentially, the query will "attend"
        that in :py:attr:`events` there will be at least `target_n_events`
        (which defaults to 1) that match the predicate.
        If the query is already satisfied, the method
        returns immediately. If not, the method waits for the timeout to be
        reached or the query to be satisfied.

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

        To write good queries you have to understand the predicate mechanism.
        The predicate can be as complex as you want, and inside it you can
        also access the list of stored events using :py:attr:`events`.
        Don't worry, everything is thread-safe and this will make you evaluate
        always the most updated list of events. See
        :py:mod:`ska_tango_testing.integration.predicates`
        for good examples of predicates.
        See also the
        :py:class:`~ska_tango_testing.integration.event.ReceivedEvent`
        class to understand how to access the event data.

        **IMPORTANT NOTE**: As an alternative to queries, for most of
        end-users we recommend using the already implemented
        `assertpy <https://assertpy.github.io/index.html>`_
        custom assertions provided by
        :py:mod:`ska_tango_testing.integration.assertions`.

        :param predicate: A function that takes an event as input and returns.
            True if the event matches the desired criteria.
        :param timeout: The time span in seconds to wait for a matching event
            (optional). If not specified or passed 0,
            the method returns immediately.

            A timeout can be None or something that can be casted to a float.
            If it is something that can be casted to a float, it must be
            greater than 0 and not infinite.

            **TECHNICAL NOTE**: Timeout may non be always a number but
            something that can be casted to a float. This is useful for
            guaranteeing retro-compatibility in custom assertions written
            before 0.7.2, where the timeout was a number and not an object
            and some users may still have code where they directly pass
            the timeout object, ignoring that now it is not a number anymore.

        :param target_n_events: How many events do you expect to find with this
            query? If in past events (events which happens prior to the moment
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
        # validate the timeout and the target number of events
        # and raise a ValueError if they are not correct
        timeout = self._validate_timeout(timeout)
        target_n_events = self._validate_target_n_events(target_n_events)

        # Create a query for the N events that match the predicate
        query = NEventsMatchQuery(
            lambda event, _: predicate(event), target_n_events, timeout
        )

        # Subscribe to the query and evaluate it
        self._events_storage.subscribe(query)
        query.evaluate()
        self._events_storage.unsubscribe(query)

        # extract and return the matching events
        return query.matching_events

    # -----------------------------
    # Input validators

    @staticmethod
    def _validate_timeout(timeout: SupportsFloat) -> float:
        """Validate the timeout and return it as a float.

        A timeout can be None or something that can be casted to a float. If
        it is something that can be casted to a float, it must be greater than
        0 and not infinite. This method performs these checks and returns the
        timeout as a float (or None).

        :param timeout: The timeout to validate.
        :return: The timeout as a float.
        :raises ValueError: If some of the stated conditions are not met.
        """
        if timeout is None:
            return 0.0

        timeout = float(timeout)

        if timeout < 0:
            raise ValueError(
                "The timeout must be greater than 0. "
                f"Instead, you provided {timeout}."
            )

        if timeout == float("inf"):
            raise ValueError(
                "The timeout must not be infinite. "
                "Instead, you provided float('inf') or something "
                "that when casted as float turns to become "
                "float('inf')."
            )

        return timeout

    @staticmethod
    def _validate_target_n_events(target_n_events: int) -> int:
        """Validate the target number of events and return it as an int.

        The target number of events must be greater or equal to 1. This method
        performs this check and returns the target number of events as an int.

        :param target_n_events: The target number of events to validate.
        :return: The target number of events as an int.
        :raises ValueError: If the target number of events is less than 1.
        """
        if target_n_events < 1:
            raise ValueError(
                "The target number of events must be greater or equal to 1. "
                f"Instead, you provided {target_n_events}."
            )

        return target_n_events
