User guide
==========

The ``ska-tango-testing`` package provides test harness elements for SKA
Tango devices.

There are three levels of functionality: mock consumers, mock callables,
and mock Tango event callbacks

Mock Consumers
--------------
The `ska_tango_testing.consumer` module provides `MockConsumer` and
`MockConsumerGroup` classes that address the problem of testing
production code that produces items asynchronously.

This module is low-level. It is powerful and flexible, but takes a bit
to set up. It requires

* a `producer`.  This is a callable that is called with a timeout, and
  either returns an item once it becomes available, or raises `Empty` if
  no item has been produced at the end of the timeout period. The
  producer is the interface to the production code. The production code
  under test might actually contain something that can serve as a
  producer (for example, if the production code drops items onto a
  queue, then that queue's `get` method will serve). Alternatively, your
  test harness might have to wrap the production code with something
  that provides this `producer` interface.

* a `categorizer`. This is a callable that sorts items into categories
  that can be asserted on individually.

* `characterizers`. By default, assertions are made against a dictionary
  with two entries: an `item` entry contains the item that has been
  produced, and the `category` entry contains the category that it has
  been sorted into. Thus, we can assert what the item is, and we can
  assert what category it belongs to.

  If the item is complex and/or non-deterministic, however, we might not
  be able to construct an item to assert with. For example, suppose the
  item is an `Event`, with fields `name`, `value` and `timestamp`. We
  generally cannot predict the timestamp values, so we cannot construct
  an equivalent `item` that would let us `assert_item(item)`.

  A `characterizer` addresses this by modifying the dictionary that
  assertions are made against. In our example, we might provde a
  characterizer that inserts "name" and "value" items into the
  dictionary, thus allowing us to `assert_item(name="foo", value="bah")`
  and hence asserting against the bits that matter, while ignoring the
  timestamp.

With these things in place, here are some of the things that you can do
in your tests:

* `group.assert_no_item()` -- assert that no item at all is produced
   within the timeout period.

* `group.assert_item()` -- assert that an item is produced. (This call
   would consume an item without really asserting anything about it, so
   wouldn't be used much.)

* `group.assert_item(item)` -- assert that the next item produced
  (across the whole group) is equal to `item`.

* `group.assert_item(category="voltage")` -- assert that the next item
   produced belongs to category "voltage".

* `group.assert_item(item, category="voltage")` -- assert that the next
   item produced (across the whole group) is equal to item and belongs
   to category "voltage"

* `group.assert_item(name="voltage", value=pytest.approx(15.0))` --
   assert that the next item has a "name" characteristic equal to
   "voltage", and a "value" characteristic approximately equal to 15.0.
   (This assertion would require a characterizer to extract the "name"
   and "value" attributes from the item.)

* `group.assert_item(item, lookahead=2)` -- assert that one of the next
   two items produced is equal to item.

* `group["voltage"].assert_item()` -- assert that an item has been
   produced in the "voltage" category

* `group["voltage"].assert_item(item)` -- assert that the next item in
   category "voltage" is equal to item

* `group["voltage"].assert_item(value=pytest.approx(15.0))` -- assert
   that the next item in category "voltage" has a "value" characteristic
   approximately equal to 15.0. (This assertion would require a
   characterizer to extract the "value" attribute from the item.)

* `group["voltage"].assert_item(item, lookahead=2)` -- assert that one
   of the next two items in the "voltage" category are equal to `item`.


Mock Callables
--------------
Mock callables build on mock consumers to addresses the problem of
testing production code that makes asynchronous calls to callables.

An example
^^^^^^^^^^
Consider this example:

.. code-block:: python

    def do_asynchronous_work(
        status_callback: Callable[[str], None],
        letter_callback: Callable[[str], None],
        number_callback: Callable[[int], None],
    ) -> None:
        def call_letters() -> None:
            for letter in ["a", "b", "c", "d"]:
                time.sleep(0.1)
                letter_callback(letter)

        letter_thread = threading.Thread(target=call_letters)

        def call_numbers() -> None:
            for number in [1, 2, 3, 4]:
                time.sleep(0.1)
                number_callback(number)

        number_thread = threading.Thread(target=call_numbers)

        def run() -> None:
            status_callback("IN_PROGRESS")

            letter_thread.start()
            number_thread.start()

            letter_thread.join()
            number_thread.join()

            status_callback("COMPLETED")

        work_thread = threading.Thread(target=run)
        work_thread.start()

We can test this example by testing that callbacks are called in the
order expected. What we expect is that:

* The first call will be a call of "IN_PROGRESS" to the status callback

* The numbers callback will be called consecutively with "1", "2", "3"
  and "4".

* The letters callback will be called consecutively with "a", "b", "c"
  and "d".

* The global order in which the number and letter callbacks are called
  is nondeterministic. One possible ordering is "1", "a",
  "2", "b", "3", "c", "d", "4"; but there are many other possibilities.

* The final call will be a call of "COMPLETED" to the status callback.

Testing with a ``unittest.mock``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It is extremely hard to test asynchronous code like this using a
standard ``unittest.mock.Mock``. A test might look something like this:

.. code-block:: python

    def test_do_asynchronous_work_using_unittest_mock() -> None:
        status_callback = unittest.mock.Mock()
        letters_callback = unittest.mock.Mock()
        numbers_callback = unittest.mock.Mock()

        do_asynchronous_work(
            status_callback,
            letters_callback,
            numbers_callback,
        )

        time.sleep(0.05)

        status_callback.assert_called_once_with("IN_PROGRESS")
        status_callback.reset_mock()

        time.sleep(0.1)
        letters_callback.assert_called_once_with("a")
        letters_callback.reset_mock()
        numbers_callback.assert_called_once_with(1)
        numbers_callback.reset_mock()

        time.sleep(0.1)
        letters_callback.assert_called_once_with("b")
        letters_callback.reset_mock()
        numbers_callback.assert_called_once_with(2)
        numbers_callback.reset_mock()

        time.sleep(0.1)
        letters_callback.assert_called_once_with("c")
        letters_callback.reset_mock()
        numbers_callback.assert_called_once_with(3)
        numbers_callback.reset_mock()

        time.sleep(0.1)
        letters_callback.assert_called_once_with("d")
        numbers_callback.assert_called_once_with(4)

        status_callback.assert_called_once_with("COMPLETED")

Note that we start by sleeping for 0.05 seconds: long enough to make it
unlikely that the test code will outrun the code under test, and assert
a call before it has been made... but not so long that a callback will
have been called more than once.

We then sleep for 0.1 seconds in the test, whenever the code under test
sleeps for 0.1 seconds. It's easy to do this when you know the exact
code timings. However real-world code won't contain sleeps of known
duration. Rather, they will do things like file I/O, network I/O, or
waiting for a lock, which have unknown and variable time costs. In such
cases, it is difficult or even impossible to tune the sleeps in your
test so that the test passes reliably. One tends to err on the side of
caution by sleeping for longer than necessary.

In short, tests like this one are extremely brittle, and often very
slow.

Testing with ``ska_tango_testing.callable``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``MockCallable`` and ``MockCallableGroup`` classes simplify testing
behaviour like this, removing the need for tuned sleeps, and ensuring
that the test takes no longer than necessary to run:

.. code-block:: python

    def test_do_asynchronous_work_using_mock_callback_group() -> None:
        callback_group = MockCallableGroup()

        do_asynchronous_work(
            callback_group["status"],
            callback_group["letters"],
            callback_group["numbers"],
        )

        callback_group.assert_against_call("status", "IN_PROGRESS")

        for letter in ["a", "b", "c", "d"]:
            callback_group["letters"].assert_against_call(letter)

        for number in [1, 2, 3, 4]:
            callback_group["numbers"].assert_against_call(number)

        callback_group.assert_against_call("status", "COMPLETED")

We now have a clean, readable test, with no sleeps.

Note that we can

* make assertions against the entire group, in which case we are
  asserting that the next call will be a specific call to a
  specific callback.

* use syntax like ``callback_group["letters"]`` to extract a particular
  callback, and then make assertions against that callback alone.


Mock Tango Event callbacks
--------------------------
A common use case for testing against callbacks in SKA is the callbacks
that are called when Tango events are received. We can effectively test
Tango device simply by using these callbacks to monitor changes in
device state.

The `MockTangoEventCallbackGroup` class is a subclass of
`MockCallableGroup` with built-in characterizers that extract the key
information from `tango.EventData` instances. Specifically, it extracts
the attribute name, value and quality, and stores them under keys
"attribute_name", "attribute_value" and "attribute_quality"
respectively.

.. code-block:: python

    device_under_test.On()
    callbacks.assert_against_call("command_status", attribute_value="QUEUED")

    # We can't be completely sure which of these two will arrive first,
    # so lets give the first one a lookahead of 2.
    callbacks.assert_against_call(
        "command_status", attribute_value="IN_PROGRESS", lookahead=2
    )
    callbacks.assert_against_call("command_progress", attribute_value="33")

    callbacks.assert_against_call("command_progress", attribute_value="66")

    callbacks.assert_against_call("device_state", attribute_value=DevState.ON)
    callbacks.assert_against_call(
        "device_status", attribute_value="The device is in ON state."
    )

    callbacks.assert_against_call("command_status", attribute_value="COMPLETED")
    callbacks.assert_not_called()
