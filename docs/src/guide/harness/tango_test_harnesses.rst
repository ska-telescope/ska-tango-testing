Tango test harnesses
--------------------

The :py:mod:`ska_tango_testing.harness` subpackage provides high-level
tooling for implementing test harnesses for Tango devices,
including situations where testing of Tango devices requires other,
non-Tango, test harness elements.

Motivation
^^^^^^^^^^
To provide a motivation for this subpackage, consider this example:

We want to test a Tango device that uses TCP
to monitor and control a laboratory instrument.
A real instrument won't always be available to test against,
so we will test against an instrument simulator.
Since we access the real instrument over TCP,
the simulator will also be accessed over TCP,
which means our test harness needs to manage a simulator TCP server.

In order to test against the instrument simulator,
the simulator TCP server must be launched prior to testing,
and must be running during testing,
and must be torn down after testing is complete.
In the case of unit tests, where test isolation is desirable,
we will want to launch a fresh TCP server for each unit test.
To avoid port congestion, we do not fix the TCP server port.
Rather, we configure the server to run on any available port,
and we dynamically configure our Tango device properties
to use whatever port the server ends up on.

The problem with pytest fixtures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Requirements like these can be met through the use of pytest fixtures.
In this case, we simply need

* a fixture that launches the simulator TCP server,
  yields the server port, and shuts the server down afterwards.

* a fixture that configures and launches the Tango device under test.
  This feature obtains the server port
  from the aforementioned simulator TCP server fixture.

The problem with this approach is it doesn't scale well.
Pytest fixtures are excellent for setting up small, rigid test harnesses,
but if you try to build a large, flexible test harness out of Pytest
fixtures, you tend to end up with a big bowl of fixture spaghetti.
For example,
just adding support for testing against a real instrument when available
would significantly complicate this Pytest fixture-based harness.
Moreover, this complexity cannot be encapsulated in a class
and hidden away.

Enter ``TangoTestHarness``
^^^^^^^^^^^^^^^^^^^^^^^^^^
The :py:class:`ska_tango_testing.harness.TangoTestHarness` class
makes it easy to implement a pure python test harness.

Several methods are provided to configure the harness:

* The :py:meth:`~ska_tango_testing.harness.TangoTestHarness.add_device`
  method is used to specify a Tango device to be included in the harness.
  The specification includes the device name, the device class,
  and the device's properties.
* The :py:meth:`~ska_tango_testing.harness.TangoTestHarness.add_mock_device`
  method is used to associate a mock with a device name.
  Once a mock has been associated with a device name,
  any attempt to create a proxy to that device name
  results in the specified mock rather than a real proxy.
* The :py:meth:`~ska_tango_testing.harness.TangoTestHarness.add_context_manager`
  method specifies any additional contexts that are to be entered
  when we enter the test harness context.
  This is how we provide for non-Tango test harness elements.
  In our example above, we would provide for a simulator TCP server
  by implementing it as a context manager,
  and then using ``add_context_manager`` to add it to the test harness:

  .. code-block:: python

    @contextmanager
    def server_factory(backend):
        server = TcpServer("localhost", 0, backend)
        with server:
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()
            (hostname, port) = server.server_address
            yield port
            server.shutdown()

    tango_test_harness.add_context_manager(
        "instrument_simulator",
        server_factory(instrument_simulator),
    )

    ...

    with tango_test_harness as test_context:
        # when we enter the test harness context,
        # we also enter any context managers that we added to the harness.

As just noted, ``TangoTestHarness`` is a context manager.
Having configured the harness, we enter its context
(i.e. the context in which the Tango subsystem
and any other required test harness elements
are all running and available)
using the usual ``with`` syntax.

Deferred property resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In our example, we need to know what port
the simulator TCP server is running on,
in order to configure the device properties of our Tango device.
``TangoTestHarness`` supports this by allowing the user
to provide *unresolved* properties to the ``add_device`` method.
These properties are resolved upon entry into the test harness context,
against the contexts that were registered with ``add_context_manager``.

To provide an unresolved property to ``TangoTestHarness``,
provide a property value that is *callable*.
Whenever a property value is callable,
``TangoTestHarness`` treats it as unresolved,
and resolves it by calling that callable
with a dictionary of its contexts.

For example, recall that our simulator server context manager
yields the server port.
Since that context manager was registered with ``add_context_manager``
under the name "instrument_simulator",
that means that when we add our tango device using ``add_device``,
we can specify the port as a callable
that extracts the required port from the collected contexts:

.. code-block:: python

    tango_test_harness.add_context_manager(
        "instrument_simulator",
        simulator_server(instrument_simulator),
    )
    tango_test_harness.add_device(
        "test/instrument/1",
        InstrumentDevice,
        Host="localhost",
        Port=lambda contexts: contexts["instrument_simulator"],
    )

Encapsulation
^^^^^^^^^^^^^
One advantage of this approach is that the test harness for a test suite
can be encapsulated in its own test harness class:

.. code-block:: python

    class InstrumentTestHarness:
        def __init__(self):
            self._tango_test_harness = TangoTestHarness()

        def add_instrument(self, instrument_id, simulator):
            simulator_context_name = f"simulator_{instrument_id}"
            self._tango_test_harness.add_context_manager(
                simulator_context_name,
                server_context_manager_factory(simulator),
            )
            self._tango_test_harness.add_device(
                f"test/instrument/{instrument_id}",
                InstrumentDevice",
                Host="localhost",
                Port=lambda context: context[simulator_context_name],
            )

        def __enter__(self):
            return self._tango_test_harness.__enter__()

        def __exit__(self, exc_type, exception, trace):
            return self._tango_test_harness.__exit__(exc_type, exception, trace)

And then using the class in a test or pytest fixture might be as simple as:

.. code-block:: python

    test_harness = InstrumentTestHarness()
    test_harness.add_instrument(instrument_id, InstrumentSimulator())
    with test_harness as test_context:
        ...
