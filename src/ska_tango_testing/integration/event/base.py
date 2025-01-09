"""A Tango change event received by some device to notify a change."""

from datetime import datetime
from typing import Any

import tango


class ReceivedEvent:
    """A Tango change event received by some device to notify a change.

    This class represents a received change event from a Tango device
    :py:attr:`device_name`, regarding an attribute :py:attr:`attribute_name`
    which contains a new value :py:attr:`attribute_value`. The event
    has been received at :py:attr:`reception_time` in this testing
    context.

    This class is a wrapper around the Tango :py:class:`tango.EventData`,
    which extracts and exposes the most relevant information for testing
    purposes. If you need to access the original Tango event data, you
    can use the :py:attr:`event_data` attribute.

    Since in SKAO tests not always the developers use the (string) device
    name, it's provided a method :py:meth:`has_device` to check if the
    event comes from a given device (the same method accepts a string too).

    Since the attribute name received by the Tango event is always lower
    case, it's provided a method :py:meth:`has_attribute` to check if the
    event comes from a given attribute (to make it case insensitive).

    A ReceivedEvent when printed as string will show the device name, the
    attribute name, the attribute value, and the reception time in
    a synthetic and human-readable way.
    """

    event_data: tango.EventData
    """The original received :py:class:`tango.EventData` object."""

    reception_time: datetime
    """The (local) timestamp of when the event was received."""

    def __init__(self, event_data: tango.EventData):
        """Initialise the ReceivedEvent with the event data.

        :param event_data: The event data.
        """
        # Store the whole event data to allow further inspection
        self.event_data = event_data

        # Further data
        self.reception_time = datetime.now()

    def __str__(self) -> str:
        """Return a string representation of the event.

        :return: the event as a string.
        """
        return (
            f"ReceivedEvent("
            f"device_name='{self.device_name}', "
            f"attribute_name='{self.attribute_name}', "
            f"attribute_value={str(self.attribute_value)}, "
            f"reception_time={self.reception_time})"
        )

    def __repr__(self) -> str:
        """Return a string representation of the event.

        :return: the event as a string.
        """
        return self.__str__()

    # ######################
    # EventData properties

    @property
    def device_name(self) -> str:
        """The name of the device that sent the event.

        Example: 'sys/tg_test/1'

        :return: The name of the device.
        """
        return self.event_data.device.dev_name()

    @property
    def attribute_name(self) -> str:
        """The (short) name of the attribute that sent the event.

        Examples: 'attribute1', 'state', etc.

        **IMPORTANT NOTE**: The attribute name is always lower case, as
        it is returned by the Tango event data. To avoid case
        sensitivity issues, always use lower case when comparing
        attribute names or use the :py:meth:`has_attribute` method.

        Example: an event from an attribute 'State'

        .. code-block:: python

            event.attribute_name # 'state'
            event.attribute_name == 'State' # False
            event.attribute_name == 'state' # True
            event.has_attribute('State') # True
            event.has_attribute('state') # True


        :return: The name of the attribute.
        """
        return self.event_data.attr_name.split("/")[-1].replace(
            "#dbase=no", ""
        )
        # TODO: Why if instead we use the following line, it occasionally
        # fails with a segmentation fault? Is event_data not a copy?
        # return self.event_data.attr_value.name

    @property
    def attribute_value(self) -> Any:
        """The new value of the attribute when the event was sent.

        :return: The new value of the attribute. The type of the value
            depends on the attribute type.
        """
        return self.event_data.attr_value.value

    @property
    def is_error(self) -> bool:
        """Check if the event is an error event.

        :return: True if the event is an error event, False otherwise.
        """
        if self.event_data.err is not None and self.event_data.err:
            return True
        return False

    # ######################
    # Additional properties
    # and methods

    def has_device(
        self, target_device_name: "str | tango.DeviceProxy"
    ) -> bool:
        """Check if the event comes from a given device.

        :param target_device_name: The name of the device
            or the device proxy to check against.

        :return: True if the event comes from the given device.
        """
        if isinstance(target_device_name, tango.DeviceProxy):
            target_device_name = target_device_name.dev_name()
        return self.device_name == target_device_name

    def has_attribute(self, target_attribute_name: str) -> bool:
        """Check if the event comes from a given attribute.

        **IMPORTANT NOTE**: A lower case comparison is used to avoid
        case sensitivity. This is preferred because attribute name
        in :py:class:`tango.EventData` is always lower case.

        Example: an event from an attribute 'State'

        .. code-block:: python

            event.attribute_name # 'state'
            event.attribute_name == 'State' # False
            event.attribute_name == 'state' # True
            event.has_attribute('State') # True
            event.has_attribute('state') # True


        :param target_attribute_name: The name of the attribute to check
            against.

        :return: True if the event comes from the given attribute.
        """
        return str.lower(self.attribute_name) == str.lower(
            target_attribute_name
        )

    def reception_age(self) -> float:
        """Return the age of the event in seconds since it was received.

        The age is calculated as the difference between the current time
        (local) and the (local) time when the event was received
        :py:attr:`reception_time`.

        :return: The age of the event in seconds.
        """
        return (datetime.now() - self.reception_time).total_seconds()
