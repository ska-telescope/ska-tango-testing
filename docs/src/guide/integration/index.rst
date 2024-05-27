Integration tests with TangoEventTracer
=======================================

:py:mod:`ska_tango_testing.integration` provides a set of tools to write
integration tests for Tango devices using an event-driven approach. The
module provides a set of tools to capture events from Tango devices and
then make assertions on them.

The central tool of the module is
:py:class:`~ska_tango_testing.integration.TangoEventTracer`
which is a class that can be used to subscribe to device
attributes change events, store them locally and then make assertions on
them using the assertion library
`assertpy <https://assertpy.github.io/index.html>`_ and some additional
assertions provided by the module itself (see 
:py:mod:`~ska_tango_testing.integration.assertions`).

This module provides also some additional event logging utilities.

To begin using :py:mod:`ska_tango_testing.integration` we recommend to
start with the :ref:`getting_started_tracer` guide, to learn about
:py:class:`~ska_tango_testing.integration.TangoEventTracer` and the already
available assertions and then, only if needed, to move to the more advanced
features described in the :ref:`custom_queries_and_assertions` section and
in the :ref:`API reference <integration_tracer_api>`.

.. toctree::
   :maxdepth: 2
   :caption: Integration tests with TangoEventTracer

   getting_started
   custom_queries_and_assertions
   event_logger

