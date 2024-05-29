Event logger
------------

In :ref:`Getting Started <getting_started_tracer>` we have seen that
:py:meth:`~ska_tango_testing.integration.log_events` is a quick utility
to live-log events from a set of devices and attributes.

If you wish to make something more sophisticated, you can use directly the
:py:class:`~ska_tango_testing.integration.logger.TangoEventLogger` class.
When subscribing to events with 
:py:meth:`~ska_tango_testing.integration.logger.TangoEventLogger.log_events_from_device`,
method, this class permits you to:

- add a filter (similar to
  :py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events`
  predicate) to select only some events instead of all of them 
  (using ``filtering_rule`` parameter);
- customize the message format providing a custom function that generates a
  string message starting from a
  :py:class:`~ska_tango_testing.integration.event.ReceivedEvent` object
  (using ``message_builder`` parameter);

Usage example:

.. code-block:: python

    from ska_tango_testing import TangoEventLogger

    def test_with_logger():
      logger = TangoEventLogger()

      # log all events from attribute "attr" of device "A"
      logger.log_events_from_device("A", "attr")

      # log only events from attribute "attr2" of device "A"
      # when value > 10
      logger.log_events_from_device(
          "A", "attr2",
          filtering_rule=lambda e: e.attribute_value > 10
      )

      # display a custom message when "B" changes its state
      logger.log_events_from_device(
          "B", "State",
          message_builder=lambda e:
              f"B STATE CHANGED INTO {e.attribute_value}"
      )

**Comments to the code**

- the first call to 
  :py:meth:`~ska_tango_testing.integration.logger.TangoEventLogger.log_events_from_device`
  works exactly as the
  :py:meth:`~ska_tango_testing.integration.log_events` function, but just for
  one device and one attribute;
- the second and the third calls show how to use the ``filtering_rule`` and
  the ``message_builder`` parameters to customize the logging behavior on
  the specified subscription;
- both ``filtering_rule`` and ``message_builder`` are optional parameters,
  the first essentially defaults to "no filter" 
  (see :py:func:`~ska_tango_testing.integration.logger.DEFAULT_LOG_ALL_EVENTS`)
  and the second to a basic
  message format that includes the device name, the attribute name, the attribute
  value and the timestamp of the event
  (see :py:func:`~ska_tango_testing.integration.logger.DEFAULT_LOG_MESSAGE_BUILDER`);
- in this example both ``filtering_rule`` and ``message_builder`` are lambda
  functions, but you can define them as you prefer (e.g. as named functions
  using the ``def`` statement).

For more details, see :ref:`API Documentation <integration_logger_api>`.

