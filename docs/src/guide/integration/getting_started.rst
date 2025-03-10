.. _getting_started_tracer:

Getting started with TangoEventTracer
-------------------------------------

Testing Tango devices and systems can be a challenging task. One of the
most common problems is verifying that certain events occur in the SUT
and that they happen in the correct order. This is particularly true when
dealing with integration tests, where you have multiple devices
and potentially multiple subsystems interacting with each other.
To address this challenge, in
:py:mod:`ska_tango_testing.integration` we provide a set of
tools to help you with that. 

The main tool is a class called
:py:class:`~ska_tango_testing.integration.TangoEventTracer`
that allows you to:

- subscribe to change events on Tango device attributes;
- automatically collect the events in the background, and store them, handling
  them in a thread-safe way;
- query them, using a predicate to filter the
  events you are interested in and a timeout mechanism to wait
  for them to happen if they are not already there;
- make assertions over them, with the support of the customizable
  assertion library
  `assertpy <https://assertpy.github.io/index.html>`_ and some additional
  assertion methods provided by
  :py:mod:`ska_tango_testing.integration.assertions`.


Basic usage
~~~~~~~~~~~

The most basic usage of :class:`~ska_tango_testing.integration.TangoEventTracer`
is to create an instance of it, subscribe to the events you are interested in,
and then use the assertion methods to verify that the events happened as
you expected.

.. code-block:: python

    # import assertion library entry point
    # (no need to import all the assertion methods you use) 
    from assertpy import assert_that

    # tool to trace change events from tango devices
    from ska_tango_testing.integration import TangoEventTracer

    def test_a_device_changes_state_when_triggered(other_device_proxy):

        # 1. create a tracer instance
        tracer = TangoEventTracer()

        # 2. subscribe to change events from a device and an attribute
        tracer.subscribe_event("sys/tg_test/1", "obsState")

        # (or alternatively, do it by passing directly a device proxy)
        tracer.subscribe_event(other_device_proxy, "otherAttribute")
        tracer.subscribe_event(other_device_proxy, "otherAttribute2")

        # 3. do something that triggers the event
        # ...

        # 4. use an assertion to check a state change happened
        #    or will happen within a timeout
        assert_that(tracer).described_as(
            "The device should change state"
        ).within_timeout(10).has_change_event_occurred(
            device_name="sys/tg_test/1",
            attribute_name="obsState",
            current_value="ON",
            previous_value="OFF",
        )

        # (we can also check only past events without using a timeout)
        # (descriptor is optional too)
        assert_that(tracer).has_change_event_occurred(
            device_name=other_device_proxy,  # name can be a device proxy
            # attribute_name = ..., 
            current_value=123,
            # previous_value = ..., 

            # all parameters are optional, so this assertion will match
            # events both from "otherAttribute" and "otherAttribute2"
            # (i.e., the two attributes that the tracer is subscribed to)
            # and with any previous value
        )

**Comments on the code**

1. We create an instance of
   :py:class:`~ska_tango_testing.integration.TangoEventTracer` (which is the
   main tool we provide to trace events from Tango devices).
2. We subscribe to the events we are interested in, using a very similar
   syntax you would use with the :py:mod:`tango` ``subscribe_event``
   method (in detail, we are subscribing to ``CHANGE_EVENT`` on the specified
   attribute). All the received events are stored in the tracer, 
   and you can query them later.
3. We assume that some action (not shown in the code) triggers the event we
   are interested in (which can be a blocking call or an asynchronous one).
4. We use the assertion method
   :py:func:`~ska_tango_testing.integration.assertions.has_change_event_occurred`
   to check that the
   event happened as expected. The method takes the device name or a device
   proxy, 
   the attribute name, the expected value, and the previous value. 
   The method will first verify if such an event is already in the tracer,
   and if not, it will wait for it to happen, up to a timeout of 10 seconds
   (optionally specified with the method
   :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
   ). If it fails, it will raise an assertion error with a detailed message
   which includes a description of the context (provided with ``described_as``)
   and the state of the tracer at the moment of the assertion. More on
   this in the next section.

Quick explanation of the assertion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since not everyone is familiar with it, let's spend a few words to explain how
we make an assertion in the code above.

`assertpy <https://assertpy.github.io/index.html>`_ is a powerful assertion
library that allows you to write expressive assertions. Essentially:

- through the entry point ``assert_that`` (the only thing you need to import),
  you point to the object of your assertion (the thing you want to check);
- through the method ``described_as`` you can optionally specify a custom
  message to be printed when the assertion fails (usually to describe the
  expected behaviour, the context and the motivation of the assertion);
- after that construct, you can chain other assertions, each of which
  will check a specific condition on the object of the assertion.

As you can see in the `documentation <https://assertpy.github.io/index.html>`_,
the library already provides a lot of assertion methods (mostly to check
primitive types, collections, and strings), but you can easily extend it.
In the code above, we used two custom methods:

- :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
  is used to (optionally) specify a timeout for the assertion, which is a
  maximum time limit to wait for the event to happen
  (if it has not already happened).
  Timeouts are a good tool to avoid explicit ``sleep`` instructions or 
  custom `synchronization` calls to "await" asynchronous conditions happening. 
  If not specified, the default timeout is 0 seconds,
  so the assertion will fail immediately if the event is not already in the
  tracer.
- :py:func:`~ska_tango_testing.integration.assertions.has_change_event_occurred`
  is an assertion method that checks if a change event has occurred

  - on a specific device and attribute,
  - with a specific current value,
  - and with a specific previous value (determined by the most recent previous
    event on the same attribute and on the same device).

  **ANOTHER NOTE**: a further parameter called ``min_n_events`` permits you
  to specify a minimum number of events that must be present in the tracer
  to make the assertion pass. This is useful when you want to check repeated
  events. Example:

  .. code-block:: python

    # at least 3 times there must be a transition from OFF to ON
    assert_that(tracer).has_change_event_occurred(
        device_name="sys/tg_test/1",
        attribute_name="State",
        current_value="ON",
        previous_value="OFF",
        min_n_events=3
    )


We chose this approach for the assertions because of its intuitive
and expressive syntax, which is very close to natural language
and permits you to write very readable tests. Moreover, as we will see
in the next section, it also allows for very detailed error messages
in case of failure. 

Two notes on the usage of assertions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **OPTIONALITY OF PARAMETERS**: all those parameters are optional,
  so you can use the method to
  make more generic checks (e.g., assert the presence of events with
  any previous value, any device, any attribute name, etc.). Example:

  .. code-block:: python

    # check that at least one event with a state change from OFF to ON
    # is present in the tracer, from any device and any attribute
    assert_that(tracer).has_change_event_occurred(
        current_value="ON",
        previous_value="OFF",
    )

- **CHAINING OF ASSERTIONS**: `assertpy` allows you to chain multiple
  assertions on the same object. In this context, we used that feature to
  permit the sharing of the timeout between multiple assertions. When you chain
  multiple
  :py:func:`~ska_tango_testing.integration.assertions.has_change_event_occurred`
  assertions, the timeout specified with the method
  :py:func:`~ska_tango_testing.integration.assertions.within_timeout`
  will be shared between all the assertions. In practice, this means that
  all the events must happen within the same timeout. 

  .. code-block:: python

    # the three devices must change state within 10 seconds
    assert_that(tracer).within_timeout(10).has_change_event_occurred(
        device_name="sys/tg_test/1",
        attribute_name="State",
        current_value="ON",
        previous_value="OFF",
    ).has_change_event_occurred(
        device_name="sys/tg_test/2",
        attribute_name="State",
        current_value="OFF",
        previous_value="ON",
    ).has_change_event_occurred(
        device_name="sys/tg_test/3",
        attribute_name="State",
        current_value="ON",
        previous_value="OFF",
    )

  When you call this, concretely:
  
  - the first event is given the whole timeout of 10 seconds,
  - the next assertion is given the remaining time (if any),
  - if there is no remaining time, the assertion will have a timeout of 0
    seconds and will fail immediately if the condition is not satisfied
    with the already present events.

  *IMPORTANT NOTE*: the sharing of a timeout between multiple assertions
  is supported only since version 0.7.2 of `ska-tango-testing`. If you are
  using an older version, each of the chained assertions will be given the initial timeout
  (not decreased by the previous assertions).


Error messages and debugging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An important advantage of the combination of `assertpy` assertions
and :py:class:`~ska_tango_testing.integration.TangoEventTracer`
is the possibility to provide very detailed, evocative and context-rich
error messages in case of failure.

As we have already seen, the ``described_as`` method allows you to specify
a custom message to describe the assertion, its meaning and the
expected behaviour at a high level. Our custom assertions, on the other hand,
allow for very detailed error messages, that will include
all the details of the passed parameters and the state of the tracer. 

Let's see a real example of a failed assertion taken from
`ska-tmc-mid-integration <https://gitlab.com/ska-telescope/ska-tmc/ska-tmc-mid-integration/>`_
tests. In a
`PyTest BDD Context <https://pytest-bdd.readthedocs.io/en/stable/>`_
we are verifying a series of state transitions on a group of devices. Let's
take this step:

.. code-block:: python

    @then(
      parsers.parse("TMC subarray {subarray_id} transitioned to ObsState IDLE")
    )
    def tmc_subarray_idle(
        central_node_mid, subarray_id
        event_tracer: TangoEventTracer, # (here tracer is a fixture)
    ):
        """Checks if SubarrayNode's obsState attribute value is IDLE"""
        central_node_mid.set_subarray_id(subarray_id)
    
        assert_that(event_tracer).described_as(
            f"Subarray node device ({central_node_mid.subarray_node.dev_name()})"
            " is expected to be in IDLE obsState"
        ).within_timeout(TIMEOUT).exists_event(
            central_node_mid.subarray_node, "obsstate", ObsState.IDLE
        )


Let's say we miss an expected event (maybe because of a bug in the code under test
or a too short timeout). The error message will be something like this:

.. code-block:: text

    E   AssertionError: [Subarray node device (ska_mid/tm_subarray_node/1) is expected to be in IDLE obsState] Expected to find an event matching the predicate within 10 seconds, but none was found.
    E           
    E   Events captured by TANGO_TRACER:
    E   ReceivedEvent(device_name='ska_mid/tm_central/central_node', attribute_name='telescopestate', attribute_value=OFF, reception_time=2024-05-15 10:38:10.896276)
    E   ReceivedEvent(device_name='ska_mid/tm_central/central_node', attribute_name='longrunningcommandresult', attribute_value=('1715769334.990096_176823959159016_TelescopeOff', '0'), reception_time=2024-05-15 10:38:10.897194)
    E   ReceivedEvent(device_name='mid-csp/control/0', attribute_name='state', attribute_value=ON, reception_time=2024-05-15 10:38:10.913552)
    E   ReceivedEvent(device_name='mid-csp/control/0', attribute_name='state', attribute_value=ON, reception_time=2024-05-15 10:38:10.913874)
    E   ReceivedEvent(device_name='mid-csp/subarray/01', attribute_name='state', attribute_value=ON, reception_time=2024-05-15 10:38:10.914714)
    E   ReceivedEvent(device_name='ska_mid/tm_central/central_node', attribute_name='telescopestate', attribute_value=UNKNOWN, reception_time=2024-05-15 10:38:10.954448)
    E   ReceivedEvent(device_name='ska_mid/tm_central/central_node', attribute_name='telescopestate', attribute_value=ON, reception_time=2024-05-15 10:38:10.954650)
    E   ReceivedEvent(device_name='ska_mid/tm_central/central_node', attribute_name='longrunningcommandresult', attribute_value=('1715769490.9011297_193925981572059_TelescopeOn', 'Error in calling SetStandbyFPMode() command on [<ska_tmc_common.adapters.DishAdapter object at 0x732d42a1f400>, <ska_tmc_common.adapters.DishAdapter object at 0x732d42a1c550>, <ska_tmc_common.adapters.DishAdapter object at 0x732d42a1f340>, <ska_tmc_common.adapters.DishAdapter object at 0x732d42a1f7f0>] ska_mid/tm_leaf_node/d0001: DevFailed[\nDevError[\n    desc = ska_tmc_common.exceptions.CommandNotAllowed: The invocation of the SetStandbyFPMode command on this device is not allowed. Reason: The current dish mode is 3. The command has NOT been executed. This device will continue with normal operation.\n           \n  origin = Traceback (most recent call last):\n  File "/usr/local/lib/python3.10/dist-packages/tango/device_server.py", line 85, in wrapper\n    return get_worker().execute(fn, *args, **kwargs)\n  File "/usr/local/lib/python3.10/dist-packages/tango/green.py", line 101, in execute\n    return fn(*args, **kwargs)\n  File "/app/src/ska_tmc_dishleafnode/dish_leaf_node.py", line 327, in is_SetStandbyFPMode_allowed\n    return self.component_manager.is_setstandbyfpmode_allowed()\n  File "/app/src/ska_tmc_dishleafnode/manager/component_manager.py", line 899, in is_setstandbyfpmode_allowed\n    raise CommandNotAllowed(\nska_tmc_common.exceptions.CommandNotAllowed: The invocation of the SetStandbyFPMode command on this device is not allowed. Reason: The current dish mode is 3. The command has NOT been executed. This device will continue with normal operation.\n\n  reason = PyDs_PythonError\nseverity = ERR]\n\nDevError[\n    desc = Failed to execute command_inout on device ska_mid/tm_leaf_node/d0001, command SetStandbyFPMode\n  origin = virtual Tango::DeviceData Tango::Connection::command_inout(const string&, const Tango::DeviceData&) at (/src/cppTango/cppapi/client/devapi_base.cpp:1338)\n  reason = API_CommandFailed\nseverity = ERR]\n]'), reception_time=2024-05-15 10:38:10.958907)
    E   ReceivedEvent(device_name='ska_mid/tm_central/central_node', attribute_name='longrunningcommandresult', attribute_value=('1715769490.9011297_193925981572059_TelescopeOn', '3'), reception_time=2024-05-15 10:38:10.959159)
    E   ReceivedEvent(device_name='ska_mid/tm_subarray_node/1', attribute_name='obsstate', attribute_value=0, reception_time=2024-05-15 10:38:11.047595)
    E   ReceivedEvent(device_name='mid-csp/subarray/01', attribute_name='obsstate', attribute_value=0, reception_time=2024-05-15 10:38:11.088411)
    E   ReceivedEvent(device_name='ska_mid/tm_subarray_node/1', attribute_name='obsstate', attribute_value=1, reception_time=2024-05-15 10:38:11.103342)
    E   ReceivedEvent(device_name='mid-csp/subarray/01', attribute_name='obsstate', attribute_value=1, reception_time=2024-05-15 10:38:11.135468)
    E   ReceivedEvent(device_name='mid-csp/subarray/01', attribute_name='obsstate', attribute_value=2, reception_time=2024-05-15 10:38:13.136576)
    E           
    E   TANGO_TRACER Query arguments: device_name='ska_mid/tm_subarray_node/1', attribute_name='obsstate', attribute_value=2, 
    E   Query start time: 2024-05-15 10:38:13.140957
    E   Query end time: 2024-05-15 10:38:23.141256


As you can see, it contains:

- your custom message with the description of the expected behaviour;
- the list of all the events captured by the tracer (with the device name;
  the attribute name, the attribute value, and the reception time);
- the query arguments used to search for the event in the tracer (the
  custom assertion runs a query to find out existing events, so query arguments
  - i.e., assertion parameters - are printed in the error message);
- the query start and end time (which are the time limits of the search).

Reading this message you can conclude that the event you were expecting
was not found. Inspecting the list of events, you can see that the expected
transition to ``IDLE`` (value 2) didn't happen on the device
``ska_mid/tm_subarray_node/1``, but happened on ``mid-csp/subarray/01``.
Moreover, if there are any previous "suspicious" events, we can also
inspect them to try to understand what happened (e.g., that
``longrunningcommandresult`` event on ``ska_mid/tm_central/central_node``
with a very long error message as a value is expected or not?).

Typed events
~~~~~~~~~~~~

In SKAO projects, we often use *enums* to represent the state of the
devices. For example, in the `ska-tmc-mid-integration` project, we use
the ``ObsState`` integer enum to represent the state of the subarray nodes.
Unfortunately, by default Tango event data are not typed,
so the attribute value
when printed as a string is just a number, 
and it is not very informative.

To address this issue, we provide a mechanism to associate *enums* types
(python ``Enum``)
to events, so that when you print them, you can see the value as a
human-readable label instead of a number. 
This is done by passing the a mapping when
creating the tracer instance, so that the tracer can use it to convert
the attribute values to the corresponding labels.

The typed subscription will look like this:

.. code-block:: python

  import pytest

  from ska_control_model import ObsState
  from ska_tango_testing.integration import TangoEventTracer

  # (where ObsState is an enum like this: )
  # class ObsState(Enum):
  #     EMPTY = 0
  #     RESOURCING = 1
  #     IDLE = 2
  #     ...

  @pytest.fixture
  def event_tracer():
      return TangoEventTracer(
          event_enum_mapping={
              "obsState": ObsState
          }
      )

  # (rest of the test code)

When an assertion will fail, the error message will contain the human-readable
label instead of the number. For example:

.. code-block:: text

  E   AssertionError: [Subarray node device (ska_mid/tm_subarray_node/1) is expected to be in IDLE obsState] Expected to find an event matching the predicate within 10 seconds, but none was found.
  E          
  E   Events captured by TANGO_TRACER:
  E     ...
  E   ReceivedEvent(device_name='mid-csp/subarray/01', attribute_name='obsstate', attribute_value=ObsState.RESOURCING, reception_time=2024-05-15 10:38:11.135468)
  E   ReceivedEvent(device_name='mid-csp/subarray/01', attribute_name='obsstate', attribute_value=ObsState.IDLE, reception_time=2024-05-15 10:38:13.136576)
  E           
  E   TANGO_TRACER Query arguments: device_name='ska_mid/tm_subarray_node/1', attribute_name='obsstate', attribute_value=ObsState.IDLE, 
  E   Query start time: 2024-05-15 10:38:13.140957
  E   Query end time: 2024-05-15 10:38:23.141256

**NOTE**: it's not necessary to add ``tango.DevState`` to
``event_enum_mapping`` because it's already supported by default.
In fact, if you try to add it, you will get an error because
``tango.DevState`` is not even an ``Enum``. 

Logging
~~~~~~~

A further tool which could help you in debugging is the live-logging system.
Other than the tracer, :py:mod:`ska_tango_testing.integration` provides
also a simple event logging utility, based on a
:py:class:`~ska_tango_testing.integration.logger.TangoEventLogger`
class.

The most basic usage of the logger is through the quick utility method
:py:func:`~ska_tango_testing.integration.log_events`, which permits you
to specify with a few lines which events you want to log in the console.

For example, let's take the initial example and add some logging:

.. code-block:: python

    # import assertion library entry point
    # (no need to import all the assertion methods you use) 
    from assertpy import assert_that
    from ska_control_model import ObsState # (NEW: import the enum)

    # tool to trace events from tango devices
    from ska_tango_testing.integration import TangoEventTracer

    # NEW: logging utility
    from ska_tango_testing.integration import log_events

    def test_a_device_changes_state_when_triggered(other_device_proxy):

        # NEW: specify what events you want to log from which devices
        # and attributes
        log_events(
            {
              # map device o a list of attributes you want to subscribe
              "sys/tg_test/1": ["obsState"],
              other_device_proxy: ["otherAttribute", "otherAttribute2"]
            },
            # NOTE: you can optionally specify the mapping for typed events
            # also in the logger
            event_enum_mapping={"obsState": ObsState}
        )
        
        # 1. create a tracer instance
        tracer = TangoEventTracer({"obsState": ObsState})

        # etc.

Whenever an event is received, the logger will print a message in the console
with the following format:

.. code-block:: text

    EVENT_LOGGER:	At 2024-05-15 10:38:10.874175, DEVICE_NAME ATTR_NAME changed to VALUE.


**NOTE**: you can specify the mapping for typed events also in the logger,
so that the events will be printed with the human-readable labels. Otherwise,
the original primitive raw values received from Tango will be printed.