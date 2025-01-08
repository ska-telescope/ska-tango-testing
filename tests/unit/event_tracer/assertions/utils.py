"""Utilities for testing custom assertions."""


def expected_error_message_has_event(
    detected_n_events: int = 0,
    expected_n_events: int = 1,
    timeout: int | None = None,
) -> str:
    """Create a regular expression for error message validation.

    This method returns a regex pattern fragment intended
    to match the start of an error message when an event assertion fails.
    It is parametrized with the number of detected events (defaults to
    0, since it is the most common case), the number of expected events
    (defaults to 1, since it is the most common case) and the timeout
    value (defaults to None, since in most of the tests it is not
    specified).

    :param detected_n_events: The number of events detected.
    :param expected_n_events: The number of events expected.
    :param timeout: The timeout value. By default, it is not specified.
    :return: The regex pattern fragment to match the start of
        the error message.
    """
    res = rf"(?:Expected to find {expected_n_events} event\(s\) "
    res += "matching the predicate "

    if timeout is not None:
        res += f"within {timeout} seconds"
    else:
        res += "in already existing events"
    res += f", but only {detected_n_events} found.)"

    return res


def expected_error_message_hasnt_event(
    detected_n_events: int = 1,
    expected_n_events: int = 1,
    timeout: int | None = None,
) -> str:
    """Create a regular expression for hasnt event error message.

    This method returns a regex pattern fragment intended
    to match the start of an error message when an event assertion fails
    in the hasnt assertion. It is parametrized with the number of detected
    events and the (not) expected number of events (both defaults to
    1, since most of the times you were expecting less than 1 event and
    instead you found exactly 1 event), and the timeout value (defaults
    to None, since in most of the tests it is not specified).

    :param detected_n_events: The number of events detected.
    :param expected_n_events: The number of events expected. It is intended
        as "less than" expected_n_events, so it defaults to 1 (because
        most of the times you want no events).
    :param timeout: The timeout value. By default, it is not specified.
    :return: The regex pattern fragment to match the start of
        the error message.
    """
    res = rf"(?:Expected to NOT find {expected_n_events} event\(s\) "
    res += "matching the predicate "

    if timeout is not None:
        res += f"within {timeout} seconds"
    else:
        res += "in already existing events"
    res += f", but {detected_n_events} were found.)"

    return res
