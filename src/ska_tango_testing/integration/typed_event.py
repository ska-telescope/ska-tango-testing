"""Extension of the event system to permit to "type" the event with Enums.

Many Tango devices attributes in the SKA project are state machines, and
their states are represented as Enums. This module extends the event system
to permit to "type" the event with Enums, so when the event is received, the
state is automatically converted to the corresponding Enum. This is useful
so when you print the event as a string, you can see the state as a human
readable label, instead of an integer number.

Concretely, this is achieved defining two new classes:

- :py:class:`ska_tango_testing.integration.typed_event.TypedEvent`,
  which is a subclass of
  :py:class:`ska_tango_testing.integration.event.ReceivedEvent`, and
- :py:class:`ska_tango_testing.integration.typed_event.EventEnumMapper`,
  which is a class that permits the association of attribute names with
  Enums.
"""

from enum import Enum

import tango

from ska_tango_testing.integration.event import ReceivedEvent


def _fail_if_type_not_enum(enum_class: type) -> None:
    """Check if the given class is an Enum, and raise an error if not.

    :param enum_class: The class to check.
    :raises TypeError: if the class is not an Enum.
    """
    if not issubclass(enum_class, Enum):
        raise TypeError(
            f"enum_class must be a subclass of Enum, not {type(enum_class)}"
        )


class TypedEvent(ReceivedEvent):
    """A ReceivedEvent that is typed with an Enum.

    This class is a subclass of
    :py:class:`ska_tango_testing.integration.event.ReceivedEvent`
    that adds the
    possibility to associate an Enum with an attribute name. This is useful
    for state machine attributes, so when the event is received, the state
    is automatically converted to the corresponding Enum. This is useful
    so when you print the event as a string, you can see the state as a
    human readable label, instead of an integer number.

    To use this class, you need to define an Enum that represents the states
    of the attribute, and then associate the attribute name with the Enum
    using the :py:class:`EventEnumMapper` class.

    Usage example:

    .. code-block:: python

        from enum import Enum

        class MyEnum(Enum):
            STATE1 = 1
            STATE2 = 2
            STATE3 = 3

        event = TypedEvent(event_data, MyEnum)

        print(event.attribute_value_as_str)  # MyEnum.STATE1
    """

    def __init__(
        self, event_data: tango.EventData, enum_class: type[Enum]
    ) -> None:
        """Create a new TypedEvent.

        :param event_data: The event data received from Tango.
        :param enum_class: The Enum class to use for the attribute value.
        :raises TypeError: if enum_class is not an Enum.
        """  # noqa: DAR402
        super().__init__(event_data)
        _fail_if_type_not_enum(enum_class)
        self.enum_class = enum_class

    @property
    def attribute_value(self) -> Enum:
        """The attribute value, eventually casted to the given enum.

        :return: the attribute value, eventually converted to an enum.
        """
        attr_value = super().attribute_value
        return self.enum_class(attr_value)


class EventEnumMapper:
    """A class to map attribute names to Enums.

    This class permits to associate attribute names with Enums. This is
    useful for state machine attributes, so when the event is received, the
    state is automatically converted to the corresponding Enum. This is
    useful so when you print the event as a string, you can see the state
    as a human readable label, instead of an integer number.

    You use this class as follows:

    - you create an instance of the class,
    - you associate attribute names with Enums using the method
      :py:meth:`map_attribute_to_enum` (or passing an initial dictionary),
    - you use the :py:meth:`get_typed_event` method to eventually get a
      typed event starting from whatever
      :py:class:`ska_tango_testing.integration.event.ReceivedEvent`.

    Usage example:

    .. code-block:: python

        from enum import Enum

        class MyEnum(Enum):
            STATE1 = 1
            STATE2 = 2
            STATE3 = 3

        mapper = EventEnumMapper()
        mapper.map_attribute_to_enum("State", MyEnum)
        # or equivalently
        # mapper = EventEnumMapper({"State": MyEnum})


        typed_event = mapper.get_typed_event(event_w_state_as_attr_name)
        # (this now is a TypedEvent with the attribute value as MyEnum)

        unchanged_event = mapper.get_typed_event(event_wo_state_as_attr_name)
        # (this is still just a ReceivedEvent)
    """

    def __init__(self, mapping: dict[str, type[Enum]] | None = None) -> None:
        """Create a new EventEnumMapper.

        :param mapping: An optional dictionary to map attribute names to Enums.
            By default, it is an empty dictionary.

        :raises TypeError: if any of the values in the mapping is not an Enum.
        """  # noqa: DAR402
        self._mapping = mapping if mapping is not None else {}

        # Check that all the values in the mapping are Enums
        for enum_class in self._mapping.values():
            _fail_if_type_not_enum(enum_class)

    def map_attribute_to_enum(
        self, attribute_name: str, enum_class: type[Enum]
    ) -> None:
        """Associate an attribute name with an Enum.

        :param attribute_name: The name of the attribute to associate.
        :param enum_class: The Enum to associate.

        :raises TypeError: if enum_class is not an Enum.
        """  # noqa: DAR402
        _fail_if_type_not_enum(enum_class)
        self._mapping[attribute_name] = enum_class

    def get_typed_event(self, event: ReceivedEvent) -> ReceivedEvent:
        """Get a ``TypedEvent`` if the attribute is associated with an Enum.

        :param event: The event to type.
        :return: The
            :py:class:`TypedEvent` instance if the attribute is
            associated with an Enum, the original event otherwise.
        """
        for attr_name, enum_class in self._mapping.items():
            # NOTE: We use the has_attribute method to avoid case sensitivity
            if event.has_attribute(attr_name):
                return TypedEvent(event.event_data, enum_class)
        return event
