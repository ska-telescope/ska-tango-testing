.. _advanced_use_cases:

Advanced Use Cases for the Assertions
-------------------------------------


Minimum number of Events (``min_n_events``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A parameter called ``min_n_events`` permits you
to specify a minimum number of events that must be present in the tracer
to make the assertion pass. This is useful when you want to check repeated
events. Example:

.. code-block:: python

  assert_that(tracer).described_as(
    "Tree ON/OFF events must be detected for a certain device"
  ).has_change_event_occurred(
      device_name="sys/tg_test/1",
      attribute_name="State",
      current_value="ON",
      previous_value="OFF",
      min_n_events=3
  )


Custom predicate (``custom_matcher``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We are aware that sometimes event matching and comparisons
are not trivial and that in some cases
a simple `==` check between an expected value and an event value is not
enough. For example, maybe you are dealing
with a complex attribute internal structure
(e.g., a composed tuple of things) and you
want to check only a part of it. Or maybe, you want to make some type
checking and casting before performing the comparison (e.g., you want to
check an attribute value is valid JSON and then parse it and compare it
with a ground truth value). Or also maybe, you just have a numeric value
and you want to check it fits in a certain range.

To address easily these cases, you can use the ``custom_matcher`` parameter
to define a further condition that must be satisfied by the event to make
the assertion pass. This parameter is a function that takes a
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` object as input
and returns a boolean value. If the function returns ``True``, the event
is considered valid and the assertion passes. If the function returns
``False``, the event is considered invalid and the assertion fails. The
``custom_matcher`` function is called for each event in the tracer and
is put in ``and`` with the other checks you defined. Example:

.. code-block:: python

  from ska_tango_testing.integration.event import ReceivedEvent

  # ...

  assert_that(tracer).described_as(
    "A certain numeric value must be in a given range"
  ).has_change_event_occurred(
      # custom matched can be combined with other more simple checks
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

Before using this advanced feature, we suggest to read the 
:py:mod:`~ska_tango_testing.integration.event` module documentation
(in particular, the
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` class API).



Early Stop Sentinel (``with_early_stop``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As we already seen in the rest of this guide, the main purpose of the
assertions and the event tracer is to check that a certain set of events
occur. In distributed systems, it is common that some events may
take a long time to happen because of external factors (e.g., network
delays, slow devices, etc.) or also because of the slowness of the system
itself. The naive approach to deal with those slow events is to define
a long timeout and wait for the events to happen or fail if the timeout
is reached. However, if the timeout is too long, your tests may fail very
slowly and this may be a problem in your CI/CD pipelines. Shortening
the timeout is not always a good idea because it may lead to
false negatives (i.e., the system is working correctly but the timeout is
reached before the events happen).

To face this problem, we introduce the concept of an "early stop sentinel".
An early stop sentinel is a function that monitors your events and, if it
detects a certain condition, it stops the evaluation early, it makes
the assertion fail and it permits you to avoid to wait for the timeout to
be reached. Think about all the exception events you may already rise in
your system: with an early stop sentinel you can catch them and stop the
evaluation immediately, making your tests fail faster.

The :py:func:`~ska_tango_testing.integration.assertions.with_early_stop`
method permits you to define in a tracer assertions a stop condition
through a lambda function that takes a
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` object as input
and returns a boolean value. If the function returns ``True``, the evaluation
stops immediately and the assertion fails. If the function returns ``False``,
the evaluation continues as usual. We can say that the early sentinel
is very similar to a custom matcher, but it has the opposite effect. Example:

.. code-block:: python

  LONG_TIMEOUT = 250  # seconds
  assert_that(event_tracer).described_as(
      "A set of events must occur within a long timeout "
      "AND no error code is detected in the meantime."
  ).within_timeout(LONG_TIMEOUT).with_early_stop(
      lambda event: event.has_attribute("longRunningCommandResult") and
          "error code 3: exception" in str(event.attribute_value)
  ).has_change_event_occurred(
      # (...) your assertions here
  ).has_change_event_occurred(
      # (...)
  ).has_change_event_occurred(
      # (...)
  )

In this example, the assertion chain will stop immediately if an event
with the attribute "longRunningCommandResult" containing the string
"error code 3: exception" is detected. This is a very simple example, but
you can define more complex early stop sentinels as you need.

**NOTE**: the early stop sentinel is evaluated for each event in the tracer
every time a new event is received and has always the priority over
the regular evaluation. Concretely this means that if in any moment
the early stop sentinel returns ``True``, the evaluation stops
immediately and fails, even if your query succeeds. This also means
that if at the beginning of the evaluation the early stop sentinel
detects something in the current events, the evaluation will fail. If you
use this without a timeout the behaviour is very similar to a
:py:func:`~ska_tango_testing.integration.assertions.hasnt_change_event_occurred`
assertion (but they are separate things, and they can actually be
combined together).

**NOTE**: currently if you concatenate more early stop sentinels, only
the last one is considered. This may change in the future.