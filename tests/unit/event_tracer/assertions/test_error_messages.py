"""Tests for verifying error messages in custom assertions."""

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.tracer import TangoEventTracer

from ..testing_utils.populate_tracer import add_event, delayed_add_event


@pytest.mark.integration_tracer
class TestAssertionsErrorMessages:
    """Assertions error messages contains all relevant information."""

    @staticmethod
    def test_error_message_contains_captured_events(
        tracer: TangoEventTracer,
    ) -> None:
        """Verify error message contains captured events.

        :param tracer: The `TangoEventTracer` instance.
        """
        event1 = add_event(tracer, "device1", 100, 1)
        event2 = add_event(tracer, "device1", 200, 2)

        with pytest.raises(AssertionError) as exc_info:
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_value=300,
            )
        assert_that(str(exc_info.value)).described_as(
            "The error message should contain the captured events"
        ).contains("Events captured by TANGO_TRACER").contains(
            str(event1), str(event2)
        )

    @staticmethod
    def test_error_message_contains_query_details(
        tracer: TangoEventTracer,
    ) -> None:
        """Verify error message contains query details.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 1)
        add_event(tracer, "device1", 200, 2)

        with pytest.raises(AssertionError) as exc_info:
            assert_that(tracer).has_change_event_occurred(
                device_name="device1",
                attribute_value=300,
            )
        assert_that(str(exc_info.value)).described_as(
            "Query details should be included in the error message"
        ).contains("TANGO_TRACER Query details").contains(
            "device_name='device1'", "attribute_value=300"
        )

    @staticmethod
    def test_error_message_contains_timeout_info(
        tracer: TangoEventTracer,
    ) -> None:
        """Verify error message contains timeout information.

        :param tracer: The `TangoEventTracer` instance.
        """
        delayed_add_event(tracer, "device1", 100, 2)

        with pytest.raises(AssertionError) as exc_info:
            assert_that(tracer).within_timeout(1).has_change_event_occurred(
                device_name="device1",
                attribute_value=100,
            )
        assert_that(str(exc_info.value)).described_as(
            "The error message should contain the timeout information"
        ).contains(
            "FAILURE REASON: The query condition was not met "
            "within the 1.0 seconds timeout"
        )

    @staticmethod
    def test_error_message_contains_early_stop_info(
        tracer: TangoEventTracer,
    ) -> None:
        """Verify error message contains early stop information.

        :param tracer: The `TangoEventTracer` instance.
        """
        add_event(tracer, "device1", 100, 1)

        with pytest.raises(AssertionError) as exc_info:
            assert_that(tracer).with_early_stop(
                lambda e: e.attribute_value == 100
            ).within_timeout(3).hasnt_change_event_occurred(
                device_name="device1",
                attribute_value=100,
            )
        assert_that(str(exc_info.value)).described_as(
            "The error message should contain the early stop information"
        ).contains(
            "FAILURE REASON: An early stop condition was triggered"
        ).described_as(
            "The error message should contain a reference "
            "to estimated remaining time"
        ).contains(
            " seconds before the timeout"
        )
