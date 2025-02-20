"""Manager for Tango device event subscriptions."""

import logging
import threading
from collections import defaultdict
from enum import Enum
from typing import Callable

import tango

import ska_tango_testing

from .base import ReceivedEvent
from .typed import EventEnumMapper


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
        self, event_enum_mapping: dict[str, type[Enum]] | None = None
    ) -> None:
        """Initialise the subscriber.

        :param event_enum_mapping: Optional mapping of attribute names
            to event types (Enum). If you specify this, the event data
            will be converted to the appropriate type before being passed
            to the user-defined callback and so eventual prints, string
            conversions etc. will be more readable.
        """
        # set the mapping between event attribute names and enum types
        self.attribute_enum_mapping = EventEnumMapper(event_enum_mapping)
        """Mapping of attribute names to event types (Enum)."""

        # The subscription ids are stored in 2 levels dictionary:
        # - the first level is the device proxy
        # - the second level key is the attribute name (lowercase)
        self._subscription_ids: dict[
            tango.DeviceProxy, dict[str, int]
        ] = defaultdict(dict)

        # A lock is used to protect eventual concurrent access to the
        # subscription ids
        self._subscriptions_lock = threading.Lock()

        # Logger to log unusual occurrences
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

        **NOTE**: if you subscribe to the same attribute of the same device
        multiple times, the subscription will NOT be duplicated.

        **TECHNICAL NOTE**: This method is thread-safe. The subscription ID is
        stored in a thread-safe way to allow concurrent subscriptions and
        un-subscriptions.
        """  # noqa: DAR402
        # create the device proxy if needed. Raise an error if the device_name
        # is not a string or DeviceProxy
        device = self._get_or_create_device(device_name, dev_factory)

        # If the subscription already exists, do not duplicate it
        if self._does_subscription_exist(device, attribute_name):
            return

        # subscribe to the Tango device attribute with the given callback
        subscription_id = device.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            lambda event_data: self._on_receive_tango_event(
                event_data, callback
            ),
        )

        # store the subscription id for the device
        self._store_subscription_id(device, attribute_name, subscription_id)

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all active subscriptions."""
        with self._subscriptions_lock:
            for device, attributes in self._subscription_ids.items():
                for _, subscription_id in attributes.items():
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
    # Handlers for subscription ids management (lock protected)

    def _does_subscription_exist(
        self, device: tango.DeviceProxy, attribute_name: str
    ) -> bool:
        """Check if a subscription exists for the given device and attribute.

        :param device: The device proxy to check
        :param attribute_name: The attribute name to check
        :return: True if a subscription exists, False otherwise
        """
        with self._subscriptions_lock:
            return attribute_name.lower() in self._subscription_ids[device]

    def _store_subscription_id(
        self,
        device: tango.DeviceProxy,
        attribute_name: str,
        subscription_id: int,
    ) -> None:
        """Store the subscription ID for the given device and attribute.

        :param device: The device proxy
        :param attribute_name: The attribute name
        :param subscription_id: The subscription ID
        """
        with self._subscriptions_lock:
            self._subscription_ids[device][
                attribute_name.lower()
            ] = subscription_id

    def _unset_subscription_id(
        self, device: tango.DeviceProxy, attribute_name: str
    ) -> int:
        """Unset the subscription ID for the given device and attribute.

        :param device: The device proxy
        :param attribute_name: The attribute name
        :return: The subscription ID that was unset
        """
        with self._subscriptions_lock:
            curr_id = self._subscription_ids[device][attribute_name.lower()]
            del self._subscription_ids[device][attribute_name.lower()]
            return curr_id

    # ------------------------------------------------------------------------
    # Other private methods

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

    def _on_receive_tango_event(
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
