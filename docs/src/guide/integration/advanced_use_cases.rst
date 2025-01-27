.. _advanced_use_cases:

Advanced Use Cases for the Assertions
-------------------------------------


Minimum number of Events (``min_n_events``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A parameter called ``min_n_events`` allows you to specify a minimum number of
events that must be present in the tracer to make the assertion pass. This is
useful when you want to check repeated events. Example:

.. code-block:: python

  assert_that(tracer).described_as(
    "Three ON/OFF events must be detected for a certain device"
  ).has_change_event_occurred(
      device_name="sys/tg_test/1",
      attribute_name="State",
      current_value="ON",
      previous_value="OFF",
      min_n_events=3
  )


Custom predicate (``custom_matcher``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We are aware that sometimes event matching and comparisons are not trivial and
that in some cases a simple `==` check between an expected value and an event
value is not enough. For example, you may be dealing with a complex attribute
internal structure (e.g., a composed tuple of things) and you want to check
only a part of it. Or perhaps you want to make some type checking and casting
before performing the comparison (e.g., you want to check an attribute value
is valid JSON and then parse it and compare it with a ground truth value). Or
maybe you just have a numeric value and you want to check it fits in a certain
range.

To address these cases easily, you can use the ``custom_matcher`` parameter
to define a further condition that must be satisfied by the event to make
the assertion pass. This parameter is a function that takes a
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` object as input
and returns a boolean value. If the function returns ``True``, the event
is considered valid and the assertion passes. If the function returns
``False``, the event is considered invalid and the assertion fails. The
``custom_matcher`` function is called for each event in the tracer and
is combined with the other checks you defined. Example:

.. code-block:: python

  from ska_tango_testing.integration.event import ReceivedEvent

  # ...

  assert_that(tracer).described_as(
    "A certain numeric value must be in a given range"
  ).has_change_event_occurred(
      # custom matcher can be combined with other more simple checks
      device_name="sys/tg_test/1",
      attribute_name="NumericValue",
      # a python lambda function is a very handy way to define a custom matcher
      custom_matcher=lambda e: 10 <= e.attribute_value < 20
  )

  # alternatively, you can define a named function and pass it
  def is_device_configured_as_expected(event: ReceivedEvent) -> bool:
    """Check if the device is configured as expected.
    
    :param event: an event from the configuration attribute
    :return: True if the device is configured as expected, False otherwise
    """
    try:
      # in your custom matcher you can access the received event
      json_value = json.loads(event.attribute_value)
      return json_value == expected_json_value
    except json.JSONDecodeError:
      return False

  assert_that(tracer).described_as(
    "A certain attribute value must be a valid JSON and be "
    "equal to a given expected JSON"
  ).has_change_event_occurred(
      device_name="sys/tg_test/1",
      attribute_name="JSONConfiguration",
      custom_matcher=is_device_configured_as_expected
  )

Potentially, your custom matcher can be as complex as you need. For example,
you can cross-reference other tracer events:

.. code-block:: python

  def is_temperature_increasing(device_name, attribute_name) -> bool:
    """Check if in the tracer events the temperature is always increasing.
    
    :param device_name: the device where the temperature is measured
    :param attribute_name: the attribute name where the temperature is stored
    :return: True if the temperature is increasing, False otherwise
    """

    previous_temperature = None
    # (NOTE: to be sure here I would sort by reception date, but whatever.
    # This is just an example, not production code)
    for event in tracer.events:
      if event.has_device(device_name) and event.has_attribute(attribute_name):
        current_temperature = event.attribute_value
        if previous_temperature is not None:
          if current_temperature <= previous_temperature:
            return False
        previous_temperature = current_temperature

    return True
        

  assert_that(tracer).described_as(
    "3 or more temperature changes are detected, they are all increasing "
    "and the last one is less than 100 degrees"
  ).has_change_event_occurred(
      device_name="sys/tg_test/1",
      attribute_name="Temperature",
      custom_matcher=lambda e:
          len(tracer.events) >= 3 and
          is_temperature_increasing("sys/tg_test/1", "Temperature") and
          e.attribute_value < 100
  )

Before using this advanced feature, we suggest reading the 
:py:mod:`~ska_tango_testing.integration.event` module documentation
(in particular, the
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` class API).



Early Stop Sentinel (``with_early_stop``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In distributed systems, events can take time to occur due to external factors
like network delays, slow devices, or system slowness. A common strategy to
handle such delays is setting long timeouts. However, lengthy timeouts can
slow your CI/CD pipelines, while shorter timeouts risk false negatives
(failing when the system is actually working).

To address this, we introduce the "early stop sentinel." This is a function
that monitors events and stops evaluation early if a specific condition is
met, causing the assertion to fail immediately. This avoids unnecessary
waiting and helps tests fail faster when an issue is detected.

The :py:func:`~ska_tango_testing.integration.assertions.with_early_stop`
function allows you to define a stop condition in a tracer assertion using
a lambda function. This function takes a
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` object as
input and returns a boolean value. If ``True``, the evaluation halts, and
the assertion fails. If ``False``, the evaluation continues as usual.
Essentially, the sentinel acts like a reverse matcher. Example:

.. code-block:: python

  LONG_TIMEOUT = 250  # seconds
  assert_that(event_tracer).described_as(
      "Events must occur within a long timeout, "
      "AND no error code is detected in the meantime."
  ).within_timeout(LONG_TIMEOUT).with_early_stop(
      lambda event: event.has_attribute("longRunningCommandResult") and
          "error code 3: exception" in str(event.attribute_value)
  ).has_change_event_occurred(
      # Assertions here
  ).has_change_event_occurred(
      # More assertions
  ).has_change_event_occurred(
      # Additional assertions
  )

In this example, the assertion chain stops immediately if an event contains
the attribute ``"longRunningCommandResult"`` with the string
``"error code 3: exception"``. You can define more complex sentinels as
needed. Potential use cases may be:

- long running command results that indicate an error,
- observation state faults,
- common "wrong" state transitions or values,
- whatever in your specific case may indicate a problem.

**Key Points:**

- The sentinel evaluates each event as it is received, taking priority
  over regular evaluation.
- If the sentinel returns ``True`` at any point (even at the start), the
  evaluation stops and fails.
- Using the sentinel without a timeout behaves similarly to
  :py:func:`~ska_tango_testing.integration.assertions.hasnt_change_event_occurred`,
  but they are two distinct features (in fact, you can actually combine them).

**NOTE:** Currently, if multiple sentinels are defined, only the last one
is used. This behaviour may change in future updates.

Timeout as an object (``ChainedAssertionsTimeout`` class)  
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As we already mentioned in :ref:`Getting Started <getting_started_tracer>`,
the timeout parameter specified through
:py:func:`~ska_tango_testing.integration.assertions.within_timeout` is a
simple way to make the following assertion chain not just evaluate current
events but also wait for new events to arrive for a certain amount of time.
What you yet may not know is that you can specify a timeout as an object
and then share it among multiple assertion chains (as it's already shared
among multiple assertions in the same chain).

The class
:py:class:`~ska_tango_testing.integration.assertions.ChainedAssertionsTimeout`
represents a timeout as an object, which:

- is initialised once with a timeout value (during the object creation),
- can be passed among multiple assertion chains,
- when it's used the first time, it starts counting down from the moment
  it's used,
- for the following assertions, it provides the remaining time to wait
  for new events to arrive (which is the initial timeout minus the time
  passed since the first use).

This is useful when you want to share the same timeout among multiple
assertion chains. Example:

.. code-block:: python

  timeout = ChainedAssertionsTimeout(10)  # 10 seconds timeout

  assert_that(tracer).described_as(
    "A certain event must occur within a timeout"
  ).within_timeout(timeout).has_change_event_occurred(
      # Assertions here
  ).has_change_event_occurred(
      # More assertions
  ).has_change_event_occurred(
      # Additional assertions
  )

  # Let's say the first assertion chain took 6 seconds to complete
  # --> the remaining time for the following chain is 4 seconds

  # the timeout is shared among multiple assertion chains
  assert_that(other_tracer).described_as(
    "Another event must occur within the same timeout"
  ).within_timeout(timeout).has_change_event_occurred(
      # Assertions here
  ).has_change_event_occurred(
      # More assertions
  ).has_change_event_occurred(
      # Additional assertions
  )

Also, the object can be also used when you want a more fine-grained control
over when to start the timeout. Example:

.. code-block:: python

  timeout = ChainedAssertionsTimeout(10)  # 10 seconds timeout
  timeout.start()  # start the timeout

  # (let's assume here we make our actions, which block the SUT for a while)
  # (e.g., 6 seconds)
  # ...

  # --> This assertion will have only 4 seconds to wait for new events
  assert_that(other_tracer).described_as(
    "Another event must occur within the same timeout"
  ).within_timeout(timeout).has_change_event_occurred(
      # Assertions here
  )

