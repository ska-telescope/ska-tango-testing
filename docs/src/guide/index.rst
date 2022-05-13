User guide
==========

The ``ska-tango-testing`` package provides test harness elements for SKA
Tango devices.

To date, the only element available is mock callables for testing
asynchronous callbacks.

Mock Callables
--------------
This subpackage addresses the problem of testing production code that
makes asynchronous calls to callables.

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

        callback_group.assert_call("status", "IN_PROGRESS")

        for letter in ["a", "b", "c", "d"]:
            callback_group["letters"].assert_call(letter)

        for number in [1, 2, 3, 4]:
            callback_group["numbers"].assert_call(number)

        callback_group.assert_call("status", "COMPLETED")

We now have a clean, readable test, with no sleeps.

Note that we can

* make assertions against the entire group, in which case we are
  asserting that the next call will be a specific call to a
  specific callback.

* use syntax like ``callback_group["letters"]`` to extract a particular
  callback, and then make assertions against that callback alone.
