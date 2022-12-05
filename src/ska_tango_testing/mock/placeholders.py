"""
This module provides some special cases for equality checking.

The only special case supported so far is `Anything`. This can be used
as a placeholder for assertions, in situations where any item should be
matched.

For example, suppose we want to assert a call with keyword arguments
`name`, `value` and `timestamp`, but we don't know exactly what the
value of the `timestamp` will be. One way to make such an assertion is

.. code-block:: python

    from ska_tango_testing.mock.placeholders import Anything

    mock_callback.assert_call(
        name="voltage",
        value=0.0,
        timestamp=Anything,
    )

and this assertion will match irrespective of the actual value of the
`timestamp` keyword.
"""
from typing import Any


class _Anything:  # pylint: disable=too-few-public-methods
    def __eq__(self, other: Any) -> bool:
        return True


Anything = _Anything()
