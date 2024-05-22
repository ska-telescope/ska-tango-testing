"""A Tango event which has been received by the ::class::`TangoEventTracer`."""

from datetime import datetime
from typing import Any, Union

import tango


class ReceivedEvent:
    """A Tango event received by the ::class::`TangoEventTracer`.

    This class is a wrapper around the Tango event data, which allows to
    access the most relevant information in a more user-friendly way. The main
    attributes are:

    - ::property::`device`: the device proxy that sent the event,
    - ::property::`device_name`: the name of the device that sent the event
        (accessible also through the ::method::`has_device`, which allows to
        check if the event comes from a given device name or using a
        device proxy instance),
    - ::property::`attribute_name`: the (short) name of the attribute that
        sent the event (accessible also through the ::method::`has_attribute`,
        which allows to check if the event comes from a given attribute name
        ignoring the case),
    - ::property::`attribute_value`: the new value of the attribute when
        the event was sent.
    - ::property::`attribute`: the full name of the attribute that sent the
        event.

    Other than that, the event data contains also:

    - ::property::`reception_time`: a timestamp of when the event was received
        by the tracer.



    If you need to access the full event data, you can use the
    ::attribute::`event_data` attribute to access the original Tango
    ::class::`EventData` object.

    NOTE: You can use this class interface to build predicates for the
    ::method::`TangoEventTracer.query_events` method, i.e.:

    .. code-block:: python

        query_result = tracer.query_events(
            lambda e: e.device_name == "sys/tg_test/1",
                    and e.attribute_name == "attribute1",
                    and e.attribute_value == 10,
            timeout=10)

    """

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
            f"attribute_value={self.attribute_value}, "
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
    def device(self) -> tango.DeviceProxy:
        """The device proxy that sent the event.

        :return: The device proxy.
        """
        return self.event_data.device

    @property
    def device_name(self) -> str:
        """The name of the device that sent the event.

        :return: The name of the device.
        """
        return self.event_data.device.dev_name()

    @property
    def attribute_name(self) -> str:
        """The (short) name of the attribute that sent the event.

        :return: The name of the attribute.
        """
        # TODO: Why if we use the following line, it occasionally
        # fails with a segmentation fault? Is event_data not a copy?
        # returnself.event_data.attr_value.name
        return self.event_data.attr_name.split("/")[-1].replace(
            "#dbase=no", ""
        )

    @property
    def attribute_value(self) -> Any:
        """The new value of the attribute when the event was sent.

        :return: The new value of the attribute.
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
        self, target_device_name: Union[str, tango.DeviceProxy]
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

        NOTE: A lower case comparison is used to avoid case sensitivity.

        :param target_attribute_name: The name of the attribute to check
            against.

        :return: True if the event comes from the given attribute.
        """
        return str.lower(self.attribute_name) == str.lower(
            target_attribute_name
        )

    def reception_age(self) -> float:
        """Return the age of the event in seconds since it was received.

        :return: The age of the event in seconds.
        """
        return (datetime.now() - self.reception_time).total_seconds()

    # @property
    # def attribute(self) -> str:
    #     """The full name of the attribute that sent the event.

    #     NOTE: This full name conainst the whole path to device, e.g.:
    #     'http://sys/tg_test/1/attribute1'.

    #     If you need to access only the short name of the attribute 4
    #     (e.g. 'attribute1'), use the ::property::`attribute_name`.
    #     """
    #     return self.event_data.attr_name
