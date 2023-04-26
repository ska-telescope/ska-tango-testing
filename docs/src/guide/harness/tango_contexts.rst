Tango contexts
--------------
.. note::
  The :py:mod:`ska_tango_testing.context` subpackage
  provides relatively low-level management of Tango test contexts.
  For implementing test harnesses,
  it is highly recommended to use the higher-level and more general
  :py:mod:`ska_tango_testing.harness` subpackage.
  See :doc:`tango_test_harnesses` for guidance.

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
  