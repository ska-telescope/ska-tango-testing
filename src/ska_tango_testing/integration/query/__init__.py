"""Query the tracer for events.

This module provides classes to represent the various queries that can
be made to the tracer to verify conditions on the events that have been
recorded and/or to retrieve events.

The main base class for the query hierarchy is
:py:class:`~ska_tango_testing.integration.query.EventQuery`, which provides
the basic interface for a query.

Some useful queries are provided in this module, such as:

- :py:class:`~ska_tango_testing.integration.query.NEventsMatchQuery`:
  A query to check if a certain number of events match a given predicate.
- :py:class:`~ska_tango_testing.integration.query.NStateChangesQuery`:
  A query to check if a certain number of changes in an attribute value
  are recorded.
- :py:class:`~ska_tango_testing.integration.query.QueryWithFailCondition`:
  A sort of decorator query that adds a fail condition to another query
  to make it fail early if some kind of event is detected.

"""

from .base import EventQuery, EventQueryStatus
from .n_events_match import NEventsMatchQuery
from .n_state_changes import NStateChangesQuery
from .with_fail_condition import QueryWithFailCondition

__all__ = [
    "EventQuery",
    "EventQueryStatus",
    "NEventsMatchQuery",
    "NStateChangesQuery",
    "QueryWithFailCondition",
]
