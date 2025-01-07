"""Typed events behave like normal events, but with a typed attribute value."""
import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.event.typed import (
    EventEnumMapper,
    TypedEvent,
)

from .testing_utils.dummy_state_enum import DummyNonEnumClass, DummyStateEnum
from .testing_utils.eventdata_mock import create_eventdata_mock


@pytest.mark.integration_tracer
class TestTypedEvents:
    """Test the TypedEvent class and the EventEnumMapper class."""

    @staticmethod
    def test_create_typed_event() -> None:
        """The creation of a TypedEvent."""
        event_data = create_eventdata_mock("test/device/1", "state", 1)
        typed_event = TypedEvent(event_data, DummyStateEnum)

        assert_that(typed_event.enum_class).is_equal_to(DummyStateEnum)
        assert_that(typed_event.device_name).is_equal_to("test/device/1")
        assert_that(typed_event.attribute_name).is_equal_to("state")
        assert_that(typed_event.attribute_value).is_equal_to(
            DummyStateEnum.STATE_1
        )
        assert_that(str(typed_event.attribute_value)).is_equal_to(
            "DummyStateEnum.STATE_1"
        )

    @staticmethod
    def test_create_typed_event_with_invalid_enum() -> None:
        """The creation of a TypedEvent with an invalid enum."""
        event_data = create_eventdata_mock("test/device/1", "state", 1)

        # This should raise a TypeError
        assert_that(lambda: TypedEvent(event_data, DummyNonEnumClass)).raises(  # type: ignore # pylint: disable=line-too-long # noqa: E501
            TypeError
        )

    @staticmethod
    def test_event_enum_mapper_create_correct_typed_event() -> None:
        """The EventEnumMapper creates the correct TypedEvent."""
        event_data = create_eventdata_mock("test/device/1", "state", 1)
        typed_event = TypedEvent(event_data, DummyStateEnum)

        mapper = EventEnumMapper()
        mapper.map_attribute_to_enum("State", DummyStateEnum)

        ret_typed_event = mapper.get_typed_event(typed_event)

        assert_that(ret_typed_event).is_instance_of(TypedEvent)
        assert_that(ret_typed_event.enum_class).is_equal_to(DummyStateEnum)  # type: ignore # pylint: disable=line-too-long # noqa: E501
        assert_that(ret_typed_event.device_name).is_equal_to("test/device/1")
        assert_that(ret_typed_event.attribute_name).is_equal_to("state")
        assert_that(ret_typed_event.attribute_value).is_equal_to(
            DummyStateEnum.STATE_1
        )
        assert_that(str(ret_typed_event.attribute_value)).is_equal_to(
            "DummyStateEnum.STATE_1"
        )

    @staticmethod
    def test_event_enum_mapper_returns_non_typed_event_too() -> None:
        """The EventEnumMapper returns a non-TypedEvent if not mapped."""
        event_data = create_eventdata_mock("test/device/1", "state2", 1)
        normal_event = ReceivedEvent(event_data)

        mapper = EventEnumMapper()
        mapper.map_attribute_to_enum("State", DummyStateEnum)

        typed_event = mapper.get_typed_event(normal_event)

        assert_that(typed_event).is_instance_of(ReceivedEvent)
        assert_that(typed_event.device_name).is_equal_to("test/device/1")
        assert_that(typed_event.attribute_name).is_equal_to("state2")
        assert_that(typed_event.attribute_value).is_equal_to(1)
        assert_that(str(typed_event.attribute_value)).is_equal_to("1")

    @staticmethod
    def test_event_enum_mapper_raises_error_on_invalid_enum() -> None:
        """The EventEnumMapper raises an error on invalid enum."""
        mapper = EventEnumMapper()

        # This should raise a TypeError
        assert_that(
            lambda: mapper.map_attribute_to_enum("State", DummyNonEnumClass)  # type: ignore # pylint: disable=line-too-long # noqa: E501
        ).raises(TypeError)

    @staticmethod
    def test_event_enum_mapper_accepts_initial_mapping() -> None:
        """The EventEnumMapper accepts an initial mapping."""
        event_data = create_eventdata_mock("test/device/1", "state", 1)
        typed_event = TypedEvent(event_data, DummyStateEnum)
        mapper = EventEnumMapper({"State": DummyStateEnum})

        ret_typed_event = mapper.get_typed_event(typed_event)

        assert_that(ret_typed_event.enum_class).is_equal_to(DummyStateEnum)  # type: ignore # pylint: disable=line-too-long # noqa: E501
        assert_that(ret_typed_event.device_name).is_equal_to("test/device/1")
        assert_that(ret_typed_event.attribute_name).is_equal_to("state")
        assert_that(ret_typed_event.attribute_value).is_equal_to(
            DummyStateEnum.STATE_1
        )
        assert_that(str(typed_event.attribute_value)).is_equal_to(
            "DummyStateEnum.STATE_1"
        )

    @staticmethod
    def test_event_enum_mapper_fail_if_initial_mapping_invalid() -> None:
        """The EventEnumMapper raises an error on invalid initial mapping."""
        # This should raise a TypeError
        assert_that(
            lambda: EventEnumMapper({"State": DummyNonEnumClass})  # type: ignore # pylint: disable=line-too-long # noqa: E501
        ).raises(TypeError)
