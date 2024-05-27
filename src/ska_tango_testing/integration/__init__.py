"""A set of utility tools for integration testing of SKA Tango devices.

This module provides a set of utility tools for integration testing
of SKA Tango devices. In particular, it provides tools to subscribe to
events, query them (within a timeout), log them in real-time, and build
complex queries and assertions to verify the behaviour of a complex
set of devices.

For a quick start, you can use the :py:class:`TangoEventTracer` class
to subscribe to events from a Tango device and then use it with the
custom assertions provided by
:py:mod:`ska_tango_testing.integration.assertions`
to make assertions on the received events.

.. code-block:: python

    from assertpy import assert_that
    from ska_tango_testing.integration import TangoEventTracer

    def test_a_device_changes_state_when_triggered():

        # create the tracer
        tracer = TangoEventTracer()

        # subscribe to events from a device
        tracer.subscribe_event("sys/tg_test/1", "obsState")

        # do something that triggers the event
        # ...

        # use an assertion to check a state change happened
        assert_that(tracer).described_as(
            "The device should change state"
        ).within_timeout(10).has_change_event_occurred(
            device="sys/tg_test/1",
            attribute="obsState",
            value="ON",
            previous_value="OFF",
        )

If you need to log events in real-time, you can use a quick utility
function :py:func:`log_events` to log events from a set of devices
and attributes. This is useful for debugging purposes and to see which
events are received in real-time while running a test.

.. code-block:: python

    # (other imports)

    from ska_tango_testing.integration import log_events

    def test_a_device_changes_state_when_triggered():

        # log events in real-time
        log_events({
            "sys/tg_test/1": ["obsState"],
            "sys/other_device/100": ["attr1", "attr2"],
        })

        # (rest of the test)

For more advanced usage of the event tracer, we suggest to read
the documentation of the :py:class:`TangoEventTracer` class, and then
give a look at :py:mod:`ska_tango_testing.integration.assertions`,
:py:mod:`ska_tango_testing.integration.event`, and
:py:mod:`ska_tango_testing.integration.predicates`.

For more advanced usage of the event logger, we suggest to read
the documentation of the
:py:class:`ska_tango_testing.integration.logger.TangoEventLogger`
class.
"""

from typing import Callable, Dict, List, Union

import tango
from assertpy import add_extension  # type: ignore

from .assertions import (
    has_change_event_occurred,
    hasnt_change_event_occurred,
    within_timeout,
)
from .logger import TangoEventLogger
from .tracer import TangoEventTracer

# register the tracer custom assertions
add_extension(has_change_event_occurred)
add_extension(hasnt_change_event_occurred)
add_extension(within_timeout)


# provide a quick utility function to log events
# (instead of a full logger)
def log_events(
    device_attribute_map: Dict[Union[str, tango.DeviceProxy], List[str]],
    dev_factory: Callable[[str], tango.DeviceProxy] = tango.DeviceProxy,
) -> TangoEventLogger:
    """Log events from a set of devices and attributes.

    Quick utility function to log events from a set of devices and attributes.
    It uses a
    :py:mod:`ska_tango_testing.integration.logger.TangoEventLogger`
    instance to log the events
    in real-time using the default logger. This is useful for debugging
    purposes and to see the events in real-time while running a test.

    Usage example:

    .. code-block:: python

        # basic usage
        log_events({
            "sys/tg_test/1": ["attr1", "attr2"],
            "sys/tg_test/2": ["State"],
        })

        # usage with proxy instead of device name
        log_events({dev_proxy: ["attr"]})

        # usage providing a custom factory to create the device proxy
        log_events({
            "sys/tg_test/1": ["attr1", "attr2"],
            "sys/tg_test/2": ["State"],
        }, dev_factory=my_custom_dev_factory)

    For more advanced usage, you can see
    :py:mod:`ska_tango_testing.integration.logger.TangoEventLogger`
    class directly, which allows you to customise the logging policy
    (filtering some messages) and the message builder (formatting the
    messages in a custom way).

    :param device_attribute_map: A dictionary mapping devices to a list
        of attribute names you are interested in logging. Each device
        could be specified either as a device name (str) or as a
        :py:class:`tango.DeviceProxy` instance.
    :param dev_factory: An optional factory function that can be used instead
        of the default :py:class:`tango.DeviceProxy` constructor
        (if you need to customise the device proxy creation).

    :return: The `TangoEventLogger` instance that is used to log
        the given events.
    """
    logger = TangoEventLogger()

    for device, attr_list in device_attribute_map.items():
        dev_proxy = dev_factory(device)
        for attr in attr_list:
            logger.log_events_from_device(
                dev_proxy, attr, dev_factory=dev_factory
            )

    return logger


# expose just a minimal set of classes and functions
__all__ = [
    "TangoEventTracer",
    "log_events",
]
