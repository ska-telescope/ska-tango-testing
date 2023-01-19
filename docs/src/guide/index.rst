User guide
==========

The :py:mod:`ska_tango_testing` package provides test harness elements
for SKA Tango devices.


Tango test contexts
-------------------
A test context provides a consistent interface to different deployments
of Tango. This allows you to write your test against that interface, and
know that it will work the same, regardless of whether you are testing
in a lightweight context or against a fully deployed Tango system.

The advantage of this is, you do not need to develop tests against a
full Tango deployment, which is very slow to develop against, because it
needs to be reset after every test run. Instead, you can develop your
tests against a lightweight Tango test context, with a much faster
development cycle. Once test development is complete, and all tests are
passing in that lightweight Tango test context, the tests can be run
against a full Tango deployment, *without changing the tests*.

Two context managers are provided:

* :py:class:`~ska_tango_testing.context.TrueTangoContextManager`
  supports testing against a full Tango system that has already been
  deployed. Because Tango is assumed already to be fully deployed, there
  is little for this manager to do.

  .. code-block:: python

    with TrueTangoContextManager() as context:
        signal_generator = context.get_device("lab/signalgenerator/1")
        spectrum_analyser = context.get_device("lab/spectrumanalyser/1")

        # test your devices...

* :py:class:`~ska_tango_testing.context.ThreadedTestTangoContextManager`
  supports testing in a lightweight Tango test context, using threads
  for asynchrony. (Using threads instead of processes allows tests to
  make use of testing strategies that assume shared memory, such as
  mocks, patches and dependency injection.)

  Because this context manager has to launch the devices under test in a
  lightweight Tango test context before the tests can be run, we need to
  tell it about the devices that it should deploy. For each device, we
  must provide the device name, the device class, and any device
  properties. This is done with the
  :py:meth:`~ska_tango_testing.context.ThreadedTestTangoContextManager.add_device`
  method. This method must be called *before* the `with` syntax is used
  to enter the context.

  .. code-block:: python

    context_manager = ThreadedTestTangoContextManager()
    context_manager.add_device(
        "lab/signalgenerator/1",
        SignalGeneratorDevice,
        Host="siggen.lab.example.com",
        Port=5024,
    )
    context_manager.add_device(
        "lab/spectrumanalyser/1",
        SpectrumAnalyserDevice,
        Host="specan.lab.example.com",
        Port=5024,
    )
    with context_manager as context:
        signal_generator = context.get_device("lab/signalgenerator/1")
        spectrum_analyser = context.get_device("lab/spectrumanalyser/1")

        # test your devices...

  Unfortunately, there is a known bug in the underlying
  :py:class:`tango.test_context.MultiDeviceTestContext` that this class
  uses:  it cannot service :py:class:`tango.DeviceProxy` requests that
  are specified with a device name; such requests must been specified
  with a Tango resource locator. (For more information see pytango issue
  https://gitlab.com/tango-controls/pytango/-/issues/459.)
  
  This bug makes it necessary to patch :py:class:`tango.DeviceProxy`, to
  convert device names into resource locators. To achieve this, a
  drop-in replacement :py:class:`ska_tango_testing.context.DeviceProxy`
  is provided. Until the bug is fixed, production code should use this
  class instead of :py:class:`tango.DeviceProxy`.

  :py:class:`~ska_tango_testing.context.ThreadedTestTangoContextManager`
  also supports mock devices. This is done with the
  :py:meth:`~ska_tango_testing.context.ThreadedTestTangoContextManager.add_mock_device`
  method:

  .. code-block:: python

    context_manager = ThreadedTestTangoContextManager()
    context_manager.add_device(
        "lab/controller/1",
        LabControllerDevice,
        SignalGeneratorName="lab/siggen/1",
        SpectrumAnalyserName="lab/spectana/1",
    )

    context_manager.add_mock_device(
        "lab/siggen/1",
        unittest.mock.Mock(**signal_generator_mock_config)
    )
    context_manager.add_mock_device(
        "lab/spectana/1",
        unittest.mock.Mock(**spectrum_analyser_mock_config)
    )
    with context_manager as context:
        controller = context.get_device("lab/controller/1")
        signal_generator = context.get_device("lab/siggen/1")
        spectrum_analyser = context.get_device("lab/spectana/1")

        # Test that when we tell the lab controller to turn everything on,
        # the signal generator and spectrum analyser are told to turn on.
        controller.On()
        signal_generator.On.assert_called_once_with()
        spectrum_analyser.On.assert_called_once_with()
  

Mock consumers
--------------
The :py:class:`~ska_tango_testing.mock.MockConsumerGroup` class
addresses the problem of testing production code that produces items
asynchronously. It is low-level, powerful and flexible, but takes a bit
to set up. It requires

* a `producer`.  This is a callable that is called with a timeout, and
  either returns an item once it becomes available, or raises
  :py:exc:`queue.Empty` if no item has been produced at the end of the
  timeout period. The producer is the interface to the production code.
  The production code under test might actually contain something that
  can serve as a producer (for example, if the production code drops
  items onto a queue, then that queue's `get` method will serve).
  Alternatively, your test harness might have to wrap the production
  code with something that provides this `producer` interface.

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
  an equivalent `item` that would let us ``assert_item(item)``.

  A `characterizer` addresses this by modifying the dictionary that
  assertions are made against. In our example, we might provide a
  characterizer that inserts "name" and "value" items into the
  dictionary, thus allowing us to
  ``assert_item(name="foo", value="bah")`` and hence asserting against
  the bits that matter, while ignoring the timestamp.

With these things in place, here are some of the things that you can do
in your tests:

* ``group.assert_no_item()`` -- assert that no item at all is produced
  within the timeout period.

* ``group.assert_item()`` -- assert that an item is produced. (This call
  would consume an item without really asserting anything about it, so
  wouldn't be used much.)

* ``group.assert_item(item)`` -- assert that the next item produced
  (across the whole group) is equal to ``item``.

* ``group.assert_item(category="voltage")`` -- assert that the next item
  produced belongs to category "voltage".

* ``group.assert_item(item, category="voltage")`` -- assert that the
  next item produced (across the whole group) is equal to item and
  belongs to category "voltage".

* ``group.assert_item(name="voltage", value=pytest.approx(15.0))`` --
  assert that the next item has a "name" characteristic equal to
  "voltage", and a "value" characteristic approximately equal to 15.0.
  (This assertion would require a characterizer to extract the "name"
  and "value" attributes from the item.)

* ``group.assert_item(item, lookahead=2)`` -- assert that one of the
  next two items produced is equal to ``item``.

* ``group["voltage"].assert_item()`` -- assert that an item has been
  produced in the "voltage" category.

* ``group["voltage"].assert_item(item)`` -- assert that the next item in
  category "voltage" is equal to ``item``.

* ``group["voltage"].assert_item(value=pytest.approx(15.0))`` -- assert
  that the next item in category "voltage" has a "value" characteristic
  approximately equal to 15.0. (This assertion would require a
  characterizer to extract the "value" attribute from the item.)

* ``group["voltage"].assert_item(item, lookahead=2)`` -- assert that one
  of the next two items in the "voltage" category are equal to
  ``item``.


Mock callables
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
  is nondeterministic. One possible ordering is "1", "a", "2", "b", "3",
  "c", "d", "4"; but there are many other possibilities.

* The final call will be a call of "COMPLETED" to the status callback.

Testing with a ``unittest.mock``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It is extremely hard to test asynchronous code like this using a
standard :py:class:`unittest.mock.Mock`. A test might look something
like this:

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

Testing with mock callables
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The :py:class:`~ska_tango_testing.mock.MockCallable` and
:py:class:`~ska_tango_testing.mock.MockCallableGroup` classes simplify
testing behaviour like this, removing the need for tuned sleeps, and
ensuring that the test takes no longer than necessary to run:

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


Mock Tango event callbacks
--------------------------
A common use case for testing against callbacks in SKA is the callbacks
that are called when Tango events are received. We can effectively test
Tango device simply by using these callbacks to monitor changes in
device state.

The
:py:class:`~ska_tango_testing.mock.tango.MockTangoEventCallbackGroup`
class is a subclass of
:py:class:`~ska_tango_testing.mock.MockConsumerGroup` with
built-in characterizers that extract the key information from
:py:class:`tango.EventData` instances. Specifically, it extracts the
attribute name, value and quality, and stores them under keys
"attribute_name", "attribute_value" and "attribute_quality"
respectively.

.. code-block:: python

    device_under_test.On()
    callbacks.assert_change_event("command_status", "QUEUED")

    # We can't be completely sure which of these two will arrive first,
    # so lets give the first one a lookahead of 2.
    callbacks.assert_change_event("command_status", "IN_PROGRESS", lookahead=2)
    callbacks.assert_change_event("command_progress", "33")
    callbacks.assert_change_event("command_progress", "66")

    callbacks.assert_change_event("device_state", DevState.ON)
    callbacks.assert_change_event(
        "device_status", "The device is in ON state."
    )

    callbacks.assert_change_event("command_status", "COMPLETED")
    callbacks.assert_not_called()

For spectrum and image attributes, the values in Tango change events are
numpy arrays. However assertions should be expressed using python lists:

.. code-block:: python

    # The change event will actually contain a numpy array,
    # but this assertion will still pass if the elements are the same
    callbacks.assert_change_event("levels", [1, 2, 1, 3, 2])


Return values
-------------
All methods that assert the presence of an item, such as
:py:meth:`~ska_tango_testing.mock.MockConsumerGroup.assert_item`,
:py:meth:`~ska_tango_testing.mock.MockCallableGroup.assert_call`,
:py:meth:`~ska_tango_testing.mock.MockCallableGroup.assert_against_call`
and
:py:meth:`~ska_tango_testing.mock.tango.MockTangoEventCallbackGroup.assert_change_event`,
return the matched item. This is useful as a diagnostic tool when
developing tests. Suppose, for example, that you are writing a test, and
the assertion

.. code-block:: python

    callback.assert_call(power=PowerState.ON)

fails unexpectedly. *Why* has it failed? Did the call not arrive? Is the
value wrong? Was the value provided as a position argument rather than
a keyword argument? Are there additional arguments?

The assertion made by ``assert_call`` is quite strict; in our example,
it asserts that the call arguments are *exactly*
`(power=PowerState.ON)`. We can relax this assertion to make it pass.
For example,

.. code-block:: python

    callback.assert_against_call(power=PowerState.ON)

asserts only that the call *contains* the keyword argument
`power=PowerState.ON`. Assuming that this more relaxed assertion passes,
we can review the details of the match:

.. code-block:: pycon

    >>> call_details = callback.assert_against_call(power=PowerState.ON)
    >>> print(call_details)
    {'call_args': (,), 'call_kwargs': {'power': PowerState.ON, 'fault': False}}

Thus we see why our original assertion failed: the call also had a
```fault``` keyword argument. If this is not an bug in the production
code, then we can now tighten up our test assertion again:

.. code-block:: python

    callback.assert_call(power=PowerState.ON, fault=False)

Logging
-------
The :py:mod:`ska_tango_testing.mock` subpackage logs to the
"ska_tango_testing.mock" logger. These logs exist to allow diagnosis of
issues within :py:class:`ska_tango_testing` itself, but may also assist with
diagnosis of test failures.

Consider again the example above, of a test that fails on the line

.. code-block:: python

    callback.assert_call(power=PowerState.ON)

where ``callback`` is a
:py:class:`~ska_tango_testing.mock.callable.MockCallable`. To diagnose
this failure, we can inspect the logs of the "ska_tango_testing.mock"
logger. In pytest, this is done via the
:py:obj:`~_pytest.logging.caplog` fixture:

.. code-block:: python

    caplog.set_level(logging.DEBUG, logger="ska_tango_testing.mock")
    callback.assert_call(power=PowerState.ON)

Running this test will now produce the following logs:

.. code-block:: text

    DEBUG    ska_tango_testing.mock:consumer.py:470 assert_item: Asserting item within next 1 item(s), with characteristics {'category': 'component_state', 'call_args': (), 'call_kwargs': {'power': <PowerState.ON: 4>}}.
    DEBUG    ska_tango_testing.mock:consumer.py:496 assert_item: 'call_kwargs' characteristic is not '{'power': <PowerState.ON: 4>}' in item '{'category': 'component_state', 'call_args': (), 'call_kwargs': {'power': <PowerState.ON: 4>, 'fault': False}}'.
    DEBUG    ska_tango_testing.mock:consumer.py:510 assert_item failed: no matching item within the first 1 items

Thus we see why our assertion failed: the call also had a `fault`
keyword argument. If this is not an bug in the production code, then we
can now tighten up our test assertion again:

.. code-block:: python

    callback.assert_call(power=PowerState.ON, fault=False)


Assertion placeholders
----------------------
Placeholders allow for flexibility in assertions by broadening the range
of items that an assertion can match. So far, the only placeholder
available is `Anything`. This matches any item at all.

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

Placeholders can be used in assertions anywhere that a specific item can
by used:

* In a `MockConsumer` assertion, it can replace an item or a category or
  any characteristics
* In a `MockCallable` or `MockCallableGroup` assertion, it can
  substitute for a positional or keyword argument
* In a `MockTangoEventCallbackGroup`, it can substitute for an entire
  event, or for an event characteristic.
