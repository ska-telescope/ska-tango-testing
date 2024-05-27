Event logger
------------

In :ref:`Getting Started <getting_started_tracer>` we have seen that
:py:meth:`~ska_tango_testing.integration.log_events` is a quick utility
to live-log events from a set of devices and attributes.

If you wish to make something more sophisticated, you can use direcltly the
:py:class:`~ska_tango_testing.integration.logger.TangoEventLogger` class.
When subscribing to events that class permits you to:

- add a filter (similar to
  :py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events`
  predicate) to select only some events instead of all of them;
- customize the message format providing a custom function that generates a
  string message starting from a
  :py:class:`~ska_tango_testing.integration.event.ReceivedEvent` object.
