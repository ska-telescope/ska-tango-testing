"""Test the ChainedAssertionsTimeout class."""


# Unit tests using pytest and assertpy

import time

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.assertions import ChainedAssertionsTimeout


@pytest.mark.integration_tracer
class TestChainedAssertionsTimeout:
    """Test the ChainedAssertionsTimeout class."""

    @staticmethod
    def test_initialization() -> None:
        """A chained assertion timeout initializes with the correct timeout."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)
        assert_that(cat.initial_timeout).is_equal_to(timeout_value)
        assert_that(cat.start_time).is_none()

    @staticmethod
    def test_initialization_factory_method_reuses_passed_object() -> None:
        """When a timeout object is passed to the factory, it is reused."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)

        cat2 = ChainedAssertionsTimeout.get_timeout_object(cat)

        assert_that(cat2).is_equal_to(cat).is_instance_of(
            ChainedAssertionsTimeout
        )

    @staticmethod
    def test_initialization_factory_method_creates_new_object() -> None:
        """When a number is passed to the factory, a new object is created."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)

        cat2 = ChainedAssertionsTimeout.get_timeout_object(2)

        assert_that(cat2).is_not_equal_to(cat).is_instance_of(
            ChainedAssertionsTimeout
        )

    @staticmethod
    def test_get_remaining_timeout_before_start_is_initial_value() -> None:
        """Before starting the remaining timeout is the initial value."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)

        assert_that(cat.get_remaining_timeout()).is_equal_to(timeout_value)

    @staticmethod
    def test_get_remaining_timeout_decreases_after_sleep() -> None:
        """The remaining timeout decreases after a sleep."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)

        cat.start()
        assert_that(cat.get_remaining_timeout()).is_close_to(2, tolerance=0.1)
        time.sleep(1)

        assert_that(cat.get_remaining_timeout()).is_close_to(1, tolerance=0.1)

    @staticmethod
    def test_get_remaining_timeout_after_full_timeout() -> None:
        """The remaining timeout is zero after the full timeout."""
        timeout_value = 1
        cat = ChainedAssertionsTimeout(timeout_value)

        cat.start()
        time.sleep(1)

        assert_that(cat.get_remaining_timeout()).is_equal_to(0)

    @staticmethod
    def test_get_remaining_timeout_of_large_timeout_value() -> None:
        """The remaining timeout is computed correctly for a large value.

        NOTE: this test has been added since with the previous implementation
        (which was essentially a call of ``timedelta.seconds``) for large
        values of timeout, the remaining timeout was not computed correctly.
        """
        timeout_value = 24 * 60 * 60 + 5  # 24 hours + 5s
        cat = ChainedAssertionsTimeout(timeout_value)

        cat.start()

        assert_that(cat.get_remaining_timeout()).is_close_to(
            timeout_value, tolerance=0.1
        ).is_not_close_to(5, tolerance=0.1)

    @staticmethod
    def test_get_remaining_timeout_edge_case() -> None:
        """The remaining timeout is zero when the initial timeout is zero."""
        timeout_value = 0
        cat = ChainedAssertionsTimeout(timeout_value)

        cat.start()
        time.sleep(0.1)

        assert_that(cat.get_remaining_timeout()).is_equal_to(0)

    @staticmethod
    def test_timeout_object_when_cast_to_num_returns_remaining_time() -> None:
        """The timeout object when used as a num returns the remaining time.

        The returned float value is the remaining time in seconds.

        NOTE: This test is added to guarantee that a
        ChainAssertionsTimeout object can be passed to the ``timeout``
        parameter of the ``query_events`` method of the EventTracer
        (for retro-compatibility with the previous implementations
        of events custom assertions).
        """
        timeout_value = 3
        cat = ChainedAssertionsTimeout(timeout_value)
        cat.start()

        assert_that(float(cat)).is_close_to(3, tolerance=0.1)
        time.sleep(1)
        assert_that(float(cat)).is_close_to(2, tolerance=0.1)
