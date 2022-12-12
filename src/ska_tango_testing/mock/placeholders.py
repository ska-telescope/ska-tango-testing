"""
This module provides some special cases for equality checking.

Two special cases are provided: `Anything` and `OneOf`:

* `Anything` can be used as a placeholder for assertions, in situations
   where any item should be matched.

   For example, suppose we want to assert a call with keyword arguments
   `name`, `value` and `timestamp`, but we don't know exactly what the
   value of the `timestamp` will be. One way to make such an assertion
   is

   .. code-block:: python

       from ska_tango_testing.mock.placeholders import Anything

       mock_callback.assert_call(
           name="voltage",
           value=0.0,
           timestamp=Anything,
       )

   and this assertion will match irrespective of the actual value of the
   `timestamp` keyword.

* `OneOf` can be used as a placeholder for assertions, in situations
   where we want to assert that the item will be a member of a specified
   set. See below for details.
"""
from typing import Any


class _Anything:  # pylint: disable=too-few-public-methods
    def __eq__(self, other: Any) -> bool:
        return True


Anything = _Anything()


class OneOf:  # pylint: disable=too-few-public-methods
    """
    Equality placeholder that is equal if any of its args is equal.

    When first initialised, an object of this class is provided with
    some number of arguments. Whenever we check if this object is equal
    to some other object, it returns True if and only if the other
    object is equal to one of its arguments.

    This can be thus used as an assertion placeholder in situations
    where one does not know precisely what value will be returned:

    .. code-block:: python

        from ska_tango_testing.mock.placeholders import OneOf

        mock_callback.assert_call(
            name="state",
            value=OneOf(DevState.ON, DevState.ALARM),
        )

    and this assertion will match as long as one of the arguments to
    `OneOf` is met.
    """

    def __init__(self, *options: Any) -> None:
        """
        Initialise a new instance.

        :param options: any number of options against which to check
            equality.
        """
        self._options = options

    def __eq__(self, other: Any) -> bool:
        """
        Check for equality with another object.

        This object is considered equal to the other object if and only
        if the other object is equal to any of this object's options.

        :param other: the object against which to test for equality.

        :return: whether the other object is equal to any of this
            placeholders options.
        """
        for option in self._options:
            if option == other:
                return True
        return False
