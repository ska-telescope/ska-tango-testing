"""Tango proxy client which can log events from Tango devices."""

import logging
import threading
from collections import defaultdict
from enum import Enum
from typing import Callable

import tango

import ska_tango_testing.context
from ska_tango_testing.integration.typed_event import EventEnumMapper

from .event import ReceivedEvent


# pylint: disable=duplicate-code
def DEFAULT_LOG_ALL_EVENTS(  # pylint: disable=invalid-name
    _: ReceivedEvent,
) -> bool:
    """Log all events.

    This is the default filtering rule for
    :py:class:`TangoEventLogger`. It logs all events without any filtering.
    You can write custom rules defining a function that takes a
    received event and returns a boolean. For example:

    .. code-block:: python

        def custom_filter(e: ReceivedEvent) -> bool:
            return e.attribute_value > 10

        logger.log_events_from_device(
            device, "attribute_name",
            filtering_rule=custom_filter
        )

    It could also be an inline lambda function. For example:

    .. code-block:: python

        logger.log_events_from_device(
            device, "attribute_name",
            # log only events with attribute_value > 10
            filtering_rule=lambda e: e.attribute_value > 10
        )


    :param _: The received event.

    :return: always True.
    """
    return True


def DEFAULT_LOG_MESSAGE_BUILDER(  # pylint: disable=invalid-name
    event: ReceivedEvent,
) -> str:
    """Log the event in a human-readable format.

    This is the default message builder for :py:class:`TangoEventLogger`.
    It logs the events in a human-readable format, including the device name,
    attribute name, and the new value of the attribute.

    You can write custom message builders defining a function that takes a
    received event and returns a string. For example:

    .. code-block:: python

        def custom_message_builder(e: ReceivedEvent) -> str:
            return (
                f"CUSTOM MESSAGE: At {e.reception_time}, {e.device_name} "
                + f"{e.attribute_name} changed to {e.attribute_value}."
            )

        logger.log_events_from_device(
            device, "attribute_name",
            message_builder=custom_message_builder
        )

    It could also be an inline lambda function. For example:

    .. code-block:: python

        logger.log_events_from_device(
            device, "attribute_name",
            # log using to string default method
            message_builder=lambda e: str(e)
        )

    :param event: The received event.

    :return: The message that will be logged.
    """
    return (
        f"    EVENT_LOGGER: At {event.reception_time}, {event.device_name} "
        + f"{event.attribute_name} changed to {event.attribute_value_as_str}."
    )


class TangoEventLogger:
    """A Tango event logger that logs change events from Tango devices.

    The logger subscribes to change events from a Tango device attribute and
    logs them using a filtering rule and a message builder. By default, all
    events are logged in a human-readable format.

    The logger can be used to log events from multiple devices and attributes.

    Usage example:

    .. code-block:: python

        logger = TangoEventLogger()

        # log all events from attribute "attr" of device "A"
        logger.log_events_from_device("A", "attr")

        # log only events from attribute "attr2" of device "A"
        # when value > 10
        logger.log_events_from_device(
            "A", "attr2",
            filtering_rule=lambda e: e.attribute_value > 10
        )

        # display a custom message when "B" changes its state
        logger.log_events_from_device(
            "B", "State",
            message_builder=lambda e:
                f"B STATE CHANGED INTO {e.attribute_value}"
        )

    **NOTE**: some events attributes even if technically they are
    primitive types (like integers or strings), they can be
    semantically typed with an ``Enum`` (e.g., a state machine attribute can be
    represented as an integer, but it is semantically a state). To handle
    those cases, when you create an instance of the logger, you can
    provide a mapping of attribute names to enums (see the
    :py:class:`ska_tango_testing.integration.typed_event.EventEnumMapper`
    class). When you subscribe to an event, the tracer will automatically
    convert the received event to the corresponding enum.

    All messages are displayed with the `INFO` logging level, except the events
    containing errors that are displayed with the `ERROR` level.
    """

    def __init__(
        self, event_enum_mapping: dict[str, type[Enum]] | None = None
    ) -> None:
        """Initialize the Tango event logger.

        :param event_enum_mapping: An optional mapping of attribute names
            to enums (to handle typed events).
        """
        # subscription ids for each device
        self._subscription_ids: dict[
            tango.DeviceProxy, list[int]
        ] = defaultdict(list)

        # lock to protect the subscription ids
        self.lock = threading.Lock()

        # mapping of attribute names to enums (to handle typed events)
        self.attribute_enum_mapping: EventEnumMapper = EventEnumMapper(
            event_enum_mapping
        )

    def __del__(self) -> None:
        """Unsubscribe from all events when the logger is deleted."""
        self.unsubscribe_all()

    def log_events_from_device(  # pylint: disable=too-many-arguments
        self,
        device_name: "str | tango.DeviceProxy",
        attribute_name: str,
        filtering_rule: Callable[
            [ReceivedEvent], bool
        ] = DEFAULT_LOG_ALL_EVENTS,
        message_builder: Callable[
            [ReceivedEvent], str
        ] = DEFAULT_LOG_MESSAGE_BUILDER,
        dev_factory: Callable[[str], tango.DeviceProxy] | None = None,
    ) -> None:
        """Log change events from a Tango device attribute.

        This method subscribes to change events from a Tango device attribute
        and logs them using a filtering rule and a message builder. By default,
        all events are logged in a human-readable format.

        Usage example:

        .. code-block:: python

            logger = TangoEventLogger()

            # log all events from attribute "attr" of device "A"
            logger.log_events_from_device("A", "attr")

            # log only events from attribute "attr2" of device "A"
            # when value > 10
            logger.log_events_from_device(
                "A", "attr2",
                filtering_rule=lambda e: e.attribute_value > 10
            )

            # display a custom message when "B" changes its state
            logger.log_events_from_device(
                "B", "State",
                message_builder=lambda e:
                    f"B STATE CHANGED INTO {e.attribute_value}"
            )

            # subscribe specifying a custom device factory
            def custom_factory(device_name: str) -> tango.DeviceProxy:
                return tango.DeviceProxy(device_name)

            logger.log_events_from_device(
                "A", "attr",
                dev_factory=custom_factory
            )

        **NOTE**: when you subscribe to an event, you will automatically
        receive the current attribute value as an event (or, in other words,
        the last "change" that happened). Take this into account.

        :param device_name: The name of the Tango target device (e.g.,
            "sys/tg_test/1") or a :py:class:`tango.DeviceProxy` instance.
        :param attribute_name: The name of the attribute to subscribe to.
        :param filtering_rule: A function that takes a received event and
            returns whether it should be logged or not. By default, all events
            are logged. See :py:func:`DEFAULT_LOG_ALL_EVENTS` for more details.
        :param message_builder: A function that takes a received event and
            returns the (str) message to log. By default, it logs the event
            in a human-readable format. See
            :py:func:`DEFAULT_LOG_MESSAGE_BUILDER` for more details.
        :param dev_factory: A device factory method to get the device proxy.
            If not specified, the device proxy is created using the
            default constructor :py:class:`tango.DeviceProxy`.

        :raises tango.DevFailed: If the subscription fails. A common reason
            for this is that the attribute is not subscribable (because the
            developer didn't set it to be "event-firing" or pollable).
            An alternative reason is that the device cannot be
            reached or it has no such attribute.
        :raises ValueError: If device_name is not a string or a
            :py:class:`tango.DeviceProxy` instance.
        """  # noqa: DAR402
        if isinstance(device_name, str):
            dev_factory = (
                dev_factory or ska_tango_testing.context.DeviceProxy
            )  # tango.DeviceProxy
            device_proxy = dev_factory(device_name)
        elif isinstance(device_name, tango.DeviceProxy):
            device_proxy = device_name
        else:
            raise ValueError(
                "The device_name must be the name of a Tango device (as a str)"
                "or a Tango DeviceProxy instance. Instead, it is of type "
                f"{type(device_name)}."
            )

        def _callback(event_data: tango.EventData) -> None:
            """Log an event using a filtering rule and a message builder.

            :param event_data: The received event data.
            """
            self._log_event(event_data, filtering_rule, message_builder)

        # subscribe to the change event
        sub_id = device_proxy.subscribe_event(
            attribute_name, tango.EventType.CHANGE_EVENT, _callback
        )

        # store the subscription id
        with self.lock:
            self._subscription_ids[device_proxy].append(sub_id)

    # @staticmethod
    def _log_event(
        self,
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
        event = ReceivedEvent(event_data)

        # the event may be typed with an Enum
        event = self.attribute_enum_mapping.get_typed_event(event)

        # if the filter check fails, the message is not logged
        if not filtering_rule(event):
            return

        # if the event has an error, log it as an error
        if event.is_error:
            logging.error(message_builder(event))

        # otherwise, log it normally
        logging.info(message_builder(event))

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all events."""
        with self.lock:
            for device_proxy, sub_ids in self._subscription_ids.items():
                for sub_id in sub_ids:
                    device_proxy.unsubscribe_event(sub_id)
            self._subscription_ids.clear()
