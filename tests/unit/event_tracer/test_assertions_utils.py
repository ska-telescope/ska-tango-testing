"""Unit tests for the event_tracer.assertions_utils module."""


# Unit tests using pytest and assertpy

import time
from datetime import datetime

import pytest
from assertpy import assert_that

from ska_tango_testing.integration.assertions_utils import (
    ChainedAssertionsTimeout,
)


@pytest.mark.integration_tracer
class TestChainedAssertionsTimeout:
    """Test the ChainedAssertionsTimeout class."""

    @staticmethod
    def test_initialization() -> None:
        """A chained assertion timeout initializes with the correct timeout."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)
        assert_that(cat.initial_timeout).is_equal_to(timeout_value)
        assert_that(cat.start_time).is_instance_of(datetime)

    @staticmethod
    def test_get_remaining_timeout_initial() -> None:
        """The remaining timeout is nearly the same as the initial timeout."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)
        remaining_timeout = cat.get_remaining_timeout()
        assert_that(remaining_timeout).is_close_to(
            timeout_value, tolerance=0.1
        )

    @staticmethod
    def test_get_remaining_timeout_after_sleep() -> None:
        """The remaining timeout decreases after a sleep."""
        timeout_value = 2
        cat = ChainedAssertionsTimeout(timeout_value)
        time.sleep(1)
        remaining_timeout = cat.get_remaining_timeout()
        assert_that(remaining_timeout).is_close_to(1, tolerance=0.1)

    @staticmethod
    def test_get_remaining_timeout_after_full_timeout() -> None:
        """The remaining timeout is zero after the full timeout."""
        timeout_value = 1
        cat = ChainedAssertionsTimeout(timeout_value)
        time.sleep(1)
        remaining_timeout = cat.get_remaining_timeout()
        assert_that(remaining_timeout).is_equal_to(0)

    @staticmethod
    def test_get_remaining_timeout_edge_case() -> None:
        """The remaining timeout is zero when the initial timeout is zero."""
        timeout_value = 0
        cat = ChainedAssertionsTimeout(timeout_value)
        remaining_timeout = cat.get_remaining_timeout()
        assert_that(remaining_timeout).is_equal_to(0)
