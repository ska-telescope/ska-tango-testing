"""Verify the custom assertions are exposed by assertpy."""


import pytest
from assertpy import assert_that

from ska_tango_testing.integration.tracer import TangoEventTracer


@pytest.mark.integration_tracer
class TestAssertionsAreExposed:
    """Verify the custom assertions are exposed by assertpy.

    Each of the custom assertions should be accessible and callable
    from an assertpy ``assert_that`` instance.
    """

    @staticmethod
    def _assert_exposes(tracer: TangoEventTracer, assertion_name: str) -> None:
        """Check that a custom assertion is accessible and callable.

        :param tracer: The `TangoEventTracer` instance.
        :param assertion_name: The name of the custom assertion.
        """
        custom = getattr(assert_that(tracer), assertion_name, None)
        assert_that(custom).described_as(
            f"Expected the custom assertion '{assertion_name}' "
            "to be exposed."
        ).is_not_none()
        assert_that(callable(custom)).described_as(
            f"Expected the custom assertion '{assertion_name}' "
            "to be a callable."
        ).is_true()

    def test_has_change_event_occurred_is_exposed(
        self, tracer: TangoEventTracer
    ) -> None:
        """The ``has_change_event_occurred`` assertion is exposed.

        :param tracer: The `TangoEventTracer` instance.
        """
        self._assert_exposes(tracer, "has_change_event_occurred")

    def test_hasnt_change_event_occurred_is_exposed(
        self, tracer: TangoEventTracer
    ) -> None:
        """The `hasnt_change_event_occurred` assertion is exposed.

        :param tracer: The `TangoEventTracer` instance.
        """
        self._assert_exposes(tracer, "hasnt_change_event_occurred")

    def test_within_timeout_is_exposed(self, tracer: TangoEventTracer) -> None:
        """The ``within_timeout`` assertion is exposed.

        :param tracer: The `TangoEventTracer` instance.
        """
        self._assert_exposes(tracer, "within_timeout")
