"""Patch the DeviceProxy class with the mock class.

NOTE: currently, because of
https://gitlab.com/tango-controls/pytango/-/issues/459
``tango.DeviceProxy`` internally is not used directly but instead
it is used ``ska_tango_testing.context.DeviceProxy``. That's why we
have also this patch instead of just patching ``tango.DeviceProxy``
in unit tests that delegate to the tracer the creation of the
instance of the device proxy.
"""

from typing import Any
from unittest.mock import patch

from tests.unit.event_tracer.testing_utils.dev_proxy_mock import (
    DeviceProxyMock,
)


def patch_context_device_proxy() -> Any:
    """Patch the DeviceProxy class with the mock class.

    NOTE: currently, because of
    https://gitlab.com/tango-controls/pytango/-/issues/459
    ``tango.DeviceProxy`` internally is not used directly but instead
    it is used ``ska_tango_testing.context.DeviceProxy``. That's why we
    have also this patch instead of just patching ``tango.DeviceProxy``
    in unit tests that delegate to the tracer the creation of the
    instance of the device proxy.

    :return: The patcher (the result of ``unittest.mock.patch`` call)
    """
    return patch(
        "ska_tango_testing.context.DeviceProxy", new_callable=DeviceProxyMock
    )
