Test harnesses
==============

The :py:mod:`ska_tango_testing` package provides two levels of support
for setting up test harnesses.

* The :py:mod:`ska_tango_testing.context` subpackage
  is focussed on testing of Tango devices.
  It provides a consistent interface to different Tango contexts,
  allowing you to write your tests against that one interface,
  and know that it will work the same,
  regardless of whether you are testing in a lightweight context
  or against a fully deployed Tango system.
  See :doc:`tango_contexts` for details.
* The :py:mod:`ska_tango_testing.harness` subpackage supports the
  establishment of broader test harnesses for Tango devices.
  Typically, testing of Tango devices requires other, non-Tango,
  test harness elements to be in place.
  For example, to test a Tango device that uses TCP
  to control a laboratory instrument,
  we might want to launch an instrument simulator as a TCP server,
  so that the Tango device has something to control.
  The ``ska_tango_testing.harness`` subpackage provides a simple
  approach to managing these test harness elements.
  See :doc:`tango_test_harnesses` for details.

.. toctree::
   :maxdepth: 2
   :caption: Test harnesses

   tango_contexts
   tango_test_harnesses
