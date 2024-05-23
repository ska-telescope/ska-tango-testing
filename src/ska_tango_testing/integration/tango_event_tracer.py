"""Tango proxy client which can trace events from Tango devices.

MISSION: to represent a tango proxy client that can subscribe
to change events of attributes of device proxies, store them as
they are notified (in a thread-safe way), and support queries
with timeouts to check if and when and who sent certain events.
"""

import logging
import threading

# import time
# from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Union

import tango

from .received_event import ReceivedEvent


class _EventQuery:
    """Class to keep track of queries and their status.

    It can be waited and unlocked by multiple threads.
    """

    def __init__(
        self,
        predicate: Callable[[ReceivedEvent], bool],
        target_n_events: int = 1,
        timeout: Optional[int] = None,
    ) -> None:
        """Create query object with a predicate and a target number of events.

        :param predicate: A function that takes an event as input and returns
            True if the event matches the desired criteria.
        :param target_n_events: How many events do you expect to find with this
            query? If in past events you don't reach the target number, the
            method will wait till you reach the target number or you reach
            the timeout. Defaults to 1 so in case of a waiting loop, the method
            will return the first event.
        :param timeout: The time span in seconds to wait for a matching event
            (optional). If not specified, the method returns immediately.
        """
        self.predicate = predicate
        self.target_n_events = target_n_events
        self.timeout = timeout

        # list of events that match the predicate, collected so far
        self.matching_events: List[ReceivedEvent] = []

        # event to signal that the query is done
        self.thread_event = threading.Event()

    def update_with_events(self, events: List[ReceivedEvent]) -> None:
        """Update the list of matching events with new events.

        Between the new events, only the ones that match the predicate
        and are not already in the list of matching events are added.

        :param events: The list of new events to check.
        """
        self.matching_events = [e for e in events if self.predicate(e)]

        # for e in events:
        #     if self.predicate(e) and e not in self.matching_events:
        #         self.matching_events.append(e)
        # (some events that are already in the list may became invalid because
        # of new conditions... for safety, we remove all and re-add them)

    def is_done(self) -> bool:
        """Check if the query is done.

        :return: True if the query is done, False otherwise.
        """
        return len(self.matching_events) >= self.target_n_events

    def try_unlock(self) -> None:
        """Try to unlock the query if it is done.

        If the query is done, the thread event is set to unlock the
        waiting threads.
        """
        if self.is_done():
            # logging.info("Query done! Unlocking the thread.")
            self.thread_event.set()
            return
        # logging.info("Query not yet done. Waiting..")

    def wait(self) -> None:
        """Wait for the query to be done.

        This call will lock your thread until the query is done or
        the timeout is reached.
        """
        if self.timeout is None or self.is_done():
            return
        self.thread_event.wait(self.timeout)


class TangoEventTracer:
    """Tango proxy client which can trace events from Tango devices.

    MISSION: to represent a tango proxy client that can subscribe to
    change events of attributes of device proxies, store them as
    they are notified (in a thread-safe way), and support queries
    with timeouts to check if and when and who sent certain events.

    This class allows you to:

    - subscribe to change events for a specific attribute of a Tango device,
    - store and access the events (in a thread-safe way),
    - query the stored events based on a predicate function and a timeout,
    - clear all stored events (in a thread-safe way), .

    Usage example 1: test where you subscribe to a device
    and query an attribute change event.

    .. code-block:: python

        def test_attribute_change():

            tracer = TangoEventTracer()
            tracer.subscribe_event("sys/tg_test/1", "attribute1")

            # do something that triggers the event
            # ...

            assert len(tracer.query_events(
                lambda e: e.device_name == "sys/tg_test/1",
                timeout=10)) == 1

    """

    def __init__(self) -> None:
        """Initialize the event collection and the lock."""
        # set of received events
        self._events: List[ReceivedEvent] = []

        # lock for thread safety in event handling
        self._events_lock = threading.Lock()

        # dictionary of subscription ids (foreach device proxy
        # are stored the subscription ids of the subscribed attributes)
        self._subscription_ids: Dict[tango.DeviceProxy, List[int]] = {}

        # lock for thread safety in subscription handling
        self._subscriptions_lock = threading.Lock()

        # list of pending queries
        self._pending_queries: List[_EventQuery] = []

        # lock for pending queries
        self._query_lock = threading.Lock()

    def __del__(self) -> None:
        """Teardown the object and unsubscribe from all subscriptions.

        (else they will be kept alive and they may cause segfaults)
        """
        self.unsubscribe_all()
        self.clear_events()

    # #############################
    # Access to stored events

    @property
    def events(self) -> List[ReceivedEvent]:
        """A copy of the currently stored events (thread-safe).

        :return: A copy of the stored events.
        """  # noqa: D402
        with self._events_lock:
            return self._events.copy()

    def clear_events(self) -> None:
        """Clear all stored events."""
        with self._events_lock:
            self._events.clear()

    # #############################
    # Subscription and
    # event handling

    def subscribe_event(
        self,
        device_name: Union[str, tango.DeviceProxy],
        attribute_name: str,
        dev_factory: Optional[Callable[[str], tango.DeviceProxy]] = None,
    ) -> None:
        """Subscribe to change events for a Tango device attribute.

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
        if isinstance(device_name, str):
            if dev_factory is None:
                device_proxy = tango.DeviceProxy(device_name)
            else:
                device_proxy = dev_factory(device_name)
        elif isinstance(device_name, tango.DeviceProxy):
            device_proxy = device_name
        else:
            raise ValueError(
                "The device_name must be the name of a Tango device (as a str)"
                "or a Tango DeviceProxy instance. Instead, it is of type "
                f"{type(device_name)}."
            )

        # subscribe to the change event
        subid = device_proxy.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            self._event_callback,
        )

        # store the subscription id
        with self._subscriptions_lock:
            if device_proxy not in self._subscription_ids:
                self._subscription_ids[device_proxy] = []
            self._subscription_ids[device_proxy].append(subid)

    def _event_callback(self, event: tango.EventData) -> None:
        """Capture the received events and store them.

        This method is called as a callback when an event is received.

        :param event: The event data object.
        """
        # logging.info("Received event. Current state: %s", self._events)

        if event.err:
            logging.error("Error in event callback: %s", event.errors)
            return

        try:
            self._add_event(ReceivedEvent(event))
        except BaseException as exception:  # pylint: disable=broad-except
            logging.error("Error while processing event: %s", exception)

    def _add_event(self, event: ReceivedEvent) -> None:
        """Store an event and update all pending queries.

        :param event: The event to add.
        """
        with self._events_lock:
            self._events.append(event)

        # logging.info("Trying unlocking %s pending queries.",
        #              str(len(self._pending_queries)))

        # update all pending queries
        with self._query_lock:
            for query in self._pending_queries:
                query.update_with_events(self.events)
                query.try_unlock()

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all subscriptions."""
        with self._subscriptions_lock:
            for device_proxy, device_sub_ids in self._subscription_ids.items():
                for subscription_id in device_sub_ids:
                    try:
                        device_proxy.unsubscribe_event(subscription_id)
                    except tango.DevFailed as dev_failed_exception:
                        logging.warning(
                            "Error while unsubscribing from event: %s",
                            dev_failed_exception,
                        )
            self._subscription_ids.clear()

    # #############################
    # Querying stored
    # and future events

    def query_events(
        self,
        predicate: Callable[[ReceivedEvent], bool],
        timeout: Optional[int] = None,
        target_n_events: int = 1,
    ) -> List[ReceivedEvent]:
        """Query stored an future events with a predicate and a timeout.

        :param predicate: A function that takes an event as input and returns.
            True if the event matches the desired criteria.
        :param timeout: The time span in seconds to wait for a matching event
            (optional). If not specified, the method returns immediately.
        :param target_n_events: How many events do you expect to find with this
            query? If in past events you don't reach the target number, the
            method will wait till you reach the target number or you reach
            the timeout. Defaults to 1 so in case of a waiting loop, the method
            will return the first event.

        :return: all matching events within the timeout
            period, an empty list otherwise.
        """
        # we aim to get a certain target number of events
        # that match a predicate
        # within a certain timeout
        query = _EventQuery(predicate, target_n_events, timeout)
        query.update_with_events(self.events)

        # if the query is already done, return the matching events
        if query.is_done():
            return query.matching_events

        # logging.info("Waiting for query to be done.")

        # wait for the query to be done
        self._wait_query(query)

        # return the result (whatever it is)
        return query.matching_events

    def _wait_query(self, query: _EventQuery) -> None:
        """Wait for a query to be done in a thread-safe way.

        The query is marked as pending and then waited for. When the query
        is satisfied or a timeout is reached, the query is unlocked
        and the process continues.

        :param query: The query object to wait for.
        """
        # add the query to the list of pending queries
        with self._query_lock:
            self._pending_queries.append(query)

        # wait for the query to be done (or the timeout to be reached)
        query.wait()

        # remove the query from the list of pending queries
        with self._query_lock:
            self._pending_queries.remove(query)
