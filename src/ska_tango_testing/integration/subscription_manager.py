"""Manager for Tango device event subscriptions."""

import logging
import threading
from collections import defaultdict
from enum import Enum
from typing import Callable, Dict

import tango

import ska_tango_testing

from .event import ReceivedEvent
from .typed_event import EventEnumMapper


class TangoSubscriber:
    """Manager for Tango device event subscriptions.

    This class manages subscriptions to Tango device change events in a
    thread-safe way. It allows you to:

    - subscribe to change events for specific device attributes, providing
      a callback that will be called when events are received
    - automatically convert event values to enum types when appropriate
    - safely unsubscribe from all events when done

    Usage example:

    .. code-block:: python

        def my_callback(event: ReceivedEvent) -> None:
            print(f"Received event: {event}")

        # Create manager with optional enum mapping
        manager = TangoSubscriptionManager({
            "State": MyStateEnum
        })

        # Subscribe to events
        manager.subscribe_event("sys/tg_test/1", "State", my_callback)

        # ... do something ...

        # Clean up
        manager.unsubscribe_all()

    **NOTE**: When you subscribe to an event, the callback will be called
    with the current attribute value as an event.

    **TECHNICAL NOTE**: The subscriptions are protected by a lock to ensure
    thread safety, potentially you can subscribe/unsubscribe from different
    threads (even if this probably will not be needed).
    """

    def __init__(
        self, event_enum_mapping: Dict[str, type[Enum]] | None = None
    ) -> None:
        """Initialize the subscriber.

        :param event_enum_mapping: Optional mapping of attribute names
            to event types (Enum). If you specify this, the event data
            will be converted to the appropriate type before being passed
            to the user-defined callback and so eventual prints, string
            conversions etc. will be more readable.
        """
        # set the mapping between event attribute names and enum types
        self.attribute_enum_mapping = EventEnumMapper(event_enum_mapping)
        """Mapping of attribute names to event types (Enum)."""

        # The subscription ids are stored in a dictionary with the device
        # proxy as key and a list of subscription ids as value.
        self._subscription_ids: Dict[
            tango.DeviceProxy, list[int]
        ] = defaultdict(list)

        # A lock is used to protect eventual concurrent access to the
        # subscription ids
        self._subscriptions_lock = threading.Lock()

        # Logger to log weird things
        self._logger = logging.getLogger(self.__class__.__name__)

    def __del__(self) -> None:
        """Clean up by unsubscribing from all subscriptions."""
        self.unsubscribe_all()

    # ------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------

    def subscribe_event(
        self,
        device_name: "str | tango.DeviceProxy",
        attribute_name: str,
        callback: Callable[[ReceivedEvent], None],
        dev_factory: Callable[[str], tango.DeviceProxy] | None = None,
    ) -> None:
        """Subscribe to change events for a Tango device attribute.

        This method sets up a subscription to CHANGE_EVENT
        events for a specific attribute of a Tango device.
        When an event is received, it is:

        1. Wrapped in a ReceivedEvent object
        2. Converted to the appropriate enum type if configured
        3. Passed to the provided callback function

        :param device_name: Either a device name (str) or an existing
            DeviceProxy.
            If a string is provided, a new DeviceProxy will be created using
            the dev_factory (or tango.DeviceProxy if no factory is provided).
        :param attribute_name: Name of the device attribute to subscribe to.
            Case-sensitive, should match exactly the attribute name in the
            device.
        :param callback: Function that will be called for each received event.
            Must accept a single ReceivedEvent parameter.
        :param dev_factory: Optional factory function to create
            DeviceProxy instances. Useful for testing or custom proxy creation.
            If None, tango.DeviceProxy will be used.
        :raises ValueError: If the device_name is not a string or DeviceProxy


        **NOTE**: Upon subscription, you will immediately receive an event with
        the current value of the attribute.

        **TECHNICAL NOTE**: This method is thread-safe. The subscription ID is
        stored in a thread-safe way to allow concurrent subscriptions and
        unsubscriptions.
        """  # noqa: DAR402
        # create the device proxy if needed. Raise an error if the device_name
        # is not a string or DeviceProxy
        device = self._get_or_create_device(device_name, dev_factory)

        # subscribe to the Tango device attribute with the given callback
        subscription_id = device.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            lambda event_data: self._call_callback(event_data, callback),
        )

        # store the subscription id for the device
        # TODO: may we store the attribute name as well?
        with self._subscriptions_lock:
            self._subscription_ids[device].append(subscription_id)

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all active subscriptions."""
        with self._subscriptions_lock:
            for device, subscription_ids in self._subscription_ids.items():
                for subscription_id in subscription_ids:
                    try:
                        device.unsubscribe_event(subscription_id)
                    except tango.EventSystemFailed as exception:
                        self._logger.warning(
                            f"Failed to unsubscribe from event: {exception}"
                        )
                    except KeyError as exception:
                        self._logger.warning(
                            f"Failed to unsubscribe from event: {exception}"
                        )
            self._subscription_ids.clear()

    # ------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------

    @staticmethod
    def _get_or_create_device(
        device_name: "str | tango.DeviceProxy",
        dev_factory: Callable[[str], tango.DeviceProxy] | None = None,
    ) -> tango.DeviceProxy:
        """Get an existing device proxy or create a new one.

        :param device_name: The name of the device or a DeviceProxy instance
        :param dev_factory: Optional factory function to create device proxies
        :return: A DeviceProxy instance
        :raises ValueError: If the device_name is not a string or DeviceProxy
        """
        # create the device proxy if needed (using the provided factory
        # or the default one)
        if isinstance(device_name, str):
            dev_factory = dev_factory or ska_tango_testing.context.DeviceProxy
            return dev_factory(device_name)

        # If the device_name is already a DeviceProxy, return it
        if isinstance(device_name, tango.DeviceProxy):
            return device_name

        # If the device_name is neither a string nor a DeviceProxy,
        # raise a value error
        raise ValueError(
            "The device_name must be the name of a Tango device (as a str)"
            "or a Tango DeviceProxy instance. Instead, it is of type "
            f"{type(device_name)}."
        )

    def _call_callback(
        self,
        event_data: tango.EventData,
        callback: Callable[[ReceivedEvent], None],
    ) -> None:
        """Process event data and call user callback.

        :param event_data: Raw event data from Tango
        :param callback: User callback to be called with the processed event
        """
        # create a ReceivedEvent from the event data
        event = ReceivedEvent(event_data)

        # Type it if needed
        event = self.attribute_enum_mapping.get_typed_event(event)

        # Call the user-defined callback
        callback(event)
