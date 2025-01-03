"""Utility function to add an event to the storage after a delay."""

import threading
import time

from ska_tango_testing.integration.event import ReceivedEvent
from ska_tango_testing.integration.event_storage import EventStorage


def delayed_store_event(
    storage: EventStorage, event: ReceivedEvent, delay: float
) -> None:
    """Add an event to the storage after a delay.

    :param storage: The storage to add the event to
    :param event: The event to add
    :param delay: The delay in seconds
    """

    def add_event_after_delay() -> None:
        """Add the event to the storage after the delay."""
        time.sleep(delay)
        storage.store(event)

    threading.Thread(target=add_event_after_delay).start()
