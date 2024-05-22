"""A set of utility tools for integration testing of SKA Tango devices.

This module provides a set of utility tools for integration testing
of SKA Tango devices. In particular, it provides:

- A class :class::`TangoEventTracer` that can be used to subscribe to
    events from a Tango device and then query them for making assertions.
- A class :class::`TangoEventLogger` that can be used to subscribe to
    events from a Tango device and then live log them for debugging purposes.
"""
