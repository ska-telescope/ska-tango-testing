Integration tests with TangoEventTracer
=======================================

:py:mod:`ska_tango_testing.integration` provides a set of tools to write
integration tests for Tango devices using an event-driven approach.
Essentially this module gives you a relatively
simple tested code to capture events from Tango devices and then make
assertions on them, without the need to re-write the ``subscribe_event`` logic
or to rely to ``while ... sleep`` loops to wait for events.

The central tool provided by the module is
:py:class:`~ska_tango_testing.integration.TangoEventTracer`, 
which is a class that can be used to subscribe to device
attributes change events, store them locally and then make assertions over
them using the library
`assertpy <https://assertpy.github.io/index.html>`_ and some additional
custom assertions provided by the module itself (see 
:py:mod:`~ska_tango_testing.integration.assertions`).

This module provides also some additional event live-logging utilities, to help
you debugging your tests.

To begin using :py:mod:`ska_tango_testing.integration` we recommend to
start with the :ref:`getting_started_tracer` guide, to learn about
:py:class:`~ska_tango_testing.integration.TangoEventTracer` and the already
available assertions and then, only if needed, to move to the more advanced
features described in :ref:`custom_queries_and_assertions` and
in the :ref:`API reference <integration_tracer_api>`.

.. toctree::
   :maxdepth: 2
   :caption: Integration tests with TangoEventTracer

   getting_started
   custom_queries_and_assertions
   event_logger

