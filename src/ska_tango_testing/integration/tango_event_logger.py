"""Tango proxy client which can log events from Tango devices."""

import logging
import threading
from typing import Callable, Dict, List, Optional

import tango

from .received_event import ReceivedEvent


def DEFAULT_LOG_ALL_EVENTS(  # pylint: disable=invalid-name
    _: ReceivedEvent,
) -> bool:
    """Log all events.

    This is the default filtering rule for the TangoEventLogger. It logs all
    events without any filtering.

    :param _: The received event.

    :return: always True.
    """
    return True


def DEFAULT_LOG_MESSAGE_BUILDER(  # pylint: disable=invalid-name
    event: ReceivedEvent,
) -> str:
    """Log the event in a human-readable format.

    This is the default message builder for the TangoEventLogger. It logs the
    event in a human-readable format, including the device name,
    attribute name, and the new value of the attribute.

    :param event: The received event.

    :return: The message to log.
    """
    return (
        f"    EVENT_LOGGER:\tAt {event.reception_time}, {event.device_name} "
        + f"{event.attribute_name} changed to {event.attribute_value}."
    )


class TangoEventLogger:
    """A Tango event logger that logs change events from Tango devices.

    The logger subscribes to change events from a Tango device attribute and
    logs them using a filtering rule and a message builder. By default, all
    events are logged in a human-readable format.

    The logger can be used to log events from multiple devices and attributes.

    Usage example 1: Given a device A, with two attributes X and Y, log all
    change events from X and only the events from Y which have a value greater
    than 10.

    .. code-block:: python

        logger = TangoEventLogger()
        logger.log_events_from_Device("A", "X")
        logger.log_events_from_Device(
            "A", "Y",
            filtering_rule=lambda e: e.attribute_value > 10
        )

    Usage example 2: Given the device A of the previous example, log all change
    events from Y, but costumize the message to say if the value > 10 or
    not.

    .. code-block:: python

        logger = TangoEventLogger()
        logger.log_events_from_Device(
            "A", "Y",
            message_builder=lambda e:
                DEFAULT_LOG_MESSAGE_BUILDER(e) + \
                f"(Value > 10: {e.attribute_value > 10})"
        )

    """

    def __init__(self) -> None:
        """Initialise the Tango event logger."""
        self._subscription_ids: Dict[tango.DeviceProxy, List[int]] = {}
        self.lock = threading.Lock()

    def __del__(self) -> None:
        """Unsubscribe from all events when the logger is deleted."""
        self.unsubscribe_all()

    def log_events_from_device(  # pylint: disable=too-many-arguments
        self,
        device_name: str,
        attribute_name: str,
        filtering_rule: Callable[
            [ReceivedEvent], bool
        ] = DEFAULT_LOG_ALL_EVENTS,
        message_builder: Callable[
            [ReceivedEvent], str
        ] = DEFAULT_LOG_MESSAGE_BUILDER,
        dev_factory: Optional[Callable[[str], tango.DeviceProxy]] = None,
    ) -> None:
        """Log change events from a Tango device attribute.

        :param device_name: The name of the Tango target device.
        :param attribute_name: The name of the attribute to subscribe to.
        :param filtering_rule: A function that takes a received event and
            returns whether it should be logged or not. By default, all events
            are logged.
        :param message_builder: A function that takes a received event and
            returns the (str) message to log. By default, it logs the event
            in a human-readable format.
        :param dev_factory: A device factory method to get the device proxy.
            If not specified, the device proxy is created using the
            default constructor :class::`tango.DeviceProxy`.

        :raises tango.DevFailed: If the subscription fails. A common reason
            for this is that the attribute is not subscribable (because the
            developer didn't set it to be "event-firing" or pollable).
            An alternative reason is that the device cannot be
            reached or it has no such attribute.
        :raises ValueError: If the device_name is not a str or a Tango
            DeviceProxy instance.
        """  # noqa: DAR402
        if isinstance(device_name, str):
            if dev_factory is None:
                dev_factory = tango.DeviceProxy

            device_proxy = dev_factory(device_name)
        elif isinstance(device_name, tango.DeviceProxy):
            device_proxy = device_name
        else:
            raise ValueError(
                "The device_name must be the name of a Tango device (as a str)"
                "or a Tango DeviceProxy instance. Instead, it is of type "
                f"{type(device_name)}."
            )

        device_proxy = dev_factory(device_name)

        def _callback(event_data: tango.EventData) -> None:
            """Log the received event using the filtering rule and mex builder.

            :param event_data: The received event data.
            """
            self._log_event(event_data, filtering_rule, message_builder)

        # subscribe to the change event
        subid = device_proxy.subscribe_event(
            attribute_name, tango.EventType.CHANGE_EVENT, _callback
        )

        # store the subscription id
        with self.lock:
            if device_proxy not in self._subscription_ids:
                self._subscription_ids[device_proxy] = []
            self._subscription_ids[device_proxy].append(subid)

    @staticmethod
    def _log_event(
        # self,
        event_data: tango.EventData,
        filtering_rule: Callable[[ReceivedEvent], bool],
        message_builder: Callable[[ReceivedEvent], str],
    ) -> None:
        """Log an event using a message builder if it passes a filter.

        Given a received event, a filtering rule and a message builder, this
        method checks if the event passes the filter and if it does, it uses
        the message builder to generate the log message and log it.

        :param event_data: The received event data.
        :param filtering_rule: The filtering rule to apply.
        :param message_builder: The message builder to use.
        """
        received_event = ReceivedEvent(event_data)

        # if event passes the filter, log it using the message builder
        if not filtering_rule(received_event):
            return

        # log as error or info depending on the event
        if received_event.is_error:
            logging.error(message_builder(received_event))

        logging.info(message_builder(received_event))

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all events."""
        with self.lock:
            for device_proxy, subids in self._subscription_ids.items():
                for subid in subids:
                    device_proxy.unsubscribe_event(subid)
            self._subscription_ids.clear()
