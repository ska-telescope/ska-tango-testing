"""Unit tests for the ReceivedEvent class."""

from unittest.mock import MagicMock

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.event.base import ReceivedEvent
from tests.unit.event_tracer.testing_utils.dev_proxy_mock import (
    create_dev_proxy_mock,
)

from ..testing_utils.eventdata_mock import create_eventdata_mock


@pytest.mark.integration_tracer
class TestReceivedEvent:
    """Tests for the ReceivedEvent class.

    A few unit tests to cover ReceivedEvent class tricky situations.
    """

    @staticmethod
    def test_attribute_name_is_extracted_from_a_simple_path() -> None:
        """The attribute name is extracted from a simple path."""
        event_data = create_eventdata_mock("test/device/1", "test_attr", 42)
        event_data.attr_name = "tango://127.0.0.1:8080/test/device/1/test_attr"

        event = ReceivedEvent(event_data)

        assert_that(event.attribute_name).is_equal_to("test_attr")

    @staticmethod
    def test_attribute_name_is_extracted_from_a_complex_path() -> None:
        """The attribute name is extracted from a complex path."""
        event_data = create_eventdata_mock("test/device/1", "test_attr", 42)
        event_data.attr_name = (
            "tango://127.0.0.1:8080/test/device/1/test_attr#dbase=no"
        )

        event = ReceivedEvent(event_data)

        assert_that(event.attribute_name).is_equal_to("test_attr")

    @staticmethod
    def test_attribute_value_is_extracted_correctly() -> None:
        """The attribute value is extracted correctly."""
        event_data = create_eventdata_mock(
            "test/device/1", "test_attr", {"key": "value"}
        )
        event = ReceivedEvent(event_data)

        assert_that(event.attribute_value).is_equal_to({"key": "value"})

    @staticmethod
    def test_attribute_value_handles_none_values() -> None:
        """The attribute value handles None values."""
        event_data = create_eventdata_mock("test/device/1", "test_attr", None)

        event_data.attr_value = None
        event = ReceivedEvent(event_data)
        assert_that(event.attribute_value).is_none()

        event_data.attr_value = {}
        event = ReceivedEvent(event_data)
        assert_that(event.attribute_value).is_none()

        event_data.attr_value = MagicMock()
        event_data.attr_value.value = None
        event = ReceivedEvent(event_data)

    @staticmethod
    def test_has_attribute_is_case_insensitive() -> None:
        """The has_attribute method is case insensitive."""
        event_data = create_eventdata_mock("test/device/1", "test_attr", 42)
        event = ReceivedEvent(event_data)

        assert_that(event.has_attribute("test_attr")).is_true()
        assert_that(event.has_attribute("Test_Attr")).is_true()
        assert_that(event.has_attribute("TEST_ATTR")).is_true()
        assert_that(event.has_attribute("testAttr")).is_false()

    @staticmethod
    def test_has_device_supports_both_device_proxy_and_name() -> None:
        """The has_device method supports both device proxy and name."""
        event_data = create_eventdata_mock("test/device/1", "test_attr", 42)
        event = ReceivedEvent(event_data)

        assert_that(event.has_device("test/device/1")).is_true()
        assert_that(event.has_device("test/device/2")).is_false()
        assert_that(
            event.has_device(create_dev_proxy_mock("test/device/1"))
        ).is_true()
        assert_that(
            event.has_device(create_dev_proxy_mock("test/device/2"))
        ).is_false()

    @staticmethod
    def test_str_representation_is_human_readable() -> None:
        """The str representation is human-readable."""
        event_data = create_eventdata_mock("test/device/1", "test_attr", 42)
        event = ReceivedEvent(event_data)

        assert_that(str(event)).contains("ReceivedEvent").contains(
            "device_name='test/device/1'"
        ).contains("attribute_name='test_attr'").contains(
            "attribute_value=42"
        ).contains(
            "reception_time="
        )
