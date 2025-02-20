"""Tango proxy client which can log events from Tango devices."""

import logging
from enum import Enum
from typing import Callable

import tango

from .event import ReceivedEvent
from .event.subscriber import TangoSubscriber
from .event.typed import EventEnumMapper


# pylint: disable=duplicate-code
def DEFAULT_LOG_ALL_EVENTS(  # pylint: disable=invalid-name
    _: ReceivedEvent,
) -> bool:
    """Log all events.

    This is the default filtering rule for
    :py:class:`TangoEventLogger`. It logs all events without any filtering.
    You can write custom rules by defining a function that takes a
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

    You can write custom message builders by defining a function that takes a
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
        + f"{event.attribute_name} changed to {str(event.attribute_value)}."
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
    :py:class:`ska_tango_testing.integration.event.EventEnumMapper`
    class). Typed events attribute values will be logged using the
    corresponding Enum labels instead of the raw values.

    All messages are displayed with the `INFO` logging level, except the events
    containing errors that are displayed with the `ERROR` level.
    """

    def __init__(
        self, event_enum_mapping: dict[str, type[Enum]] | None = None
    ) -> None:
        """Initialise the Tango event logger.

        :param event_enum_mapping: An optional mapping of attribute names
            to enums (to handle typed events).
        """
        # (thread-safe) Tango devices subscriber
        self._subscriber = TangoSubscriber(event_enum_mapping)

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
        # define a callback to log an event using the given filtering rule
        # and a message builder
        def _callback(event: ReceivedEvent) -> None:
            """Log an event using a filtering rule and a message builder.

            :param event: The received event.
            """
            self._log_event(event, filtering_rule, message_builder)

        self._subscriber.subscribe_event(
            device_name, attribute_name, _callback, dev_factory
        )

    @staticmethod
    def _log_event(
        event: ReceivedEvent,
        filtering_rule: Callable[[ReceivedEvent], bool],
        message_builder: Callable[[ReceivedEvent], str],
    ) -> None:
        """Log an event using a message builder if it passes a filter.

        Given a received event, a filtering rule and a message builder, this
        method checks if the event passes the filter and if it does, it uses
        the message builder to generate the log message and log it.

        :param event: The received event.
        :param filtering_rule: The filtering rule to apply.
        :param message_builder: The message builder to use.
        """
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
        self._subscriber.unsubscribe_all()
