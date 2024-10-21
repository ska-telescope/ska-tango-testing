"""This module tests the ska_tango_testing version."""
import ska_tango_testing


def test_version() -> None:
    """Test that the ska_tango_testing version is as expected."""
    assert ska_tango_testing.__version__ == "0.7.3"
