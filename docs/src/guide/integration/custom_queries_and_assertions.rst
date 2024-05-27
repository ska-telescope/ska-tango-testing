.. _custom_queries_and_assertions:


Custom queries and assertions using TangoEventTracer
----------------------------------------------------

In :ref:`Getting Started <getting_started_tracer>` we have seen how to use the
:py:class:`~ska_tango_testing.integration.TangoEventTracer` to trace events
and then use `assertpy <https://assertpy.github.io/index.html>`_ (custom)
assertions to verify the events. But how are they implemented?

Queries and predicates
~~~~~~~~~~~~~~~~~~~~~~

:py:class:`~ska_tango_testing.integration.TangoEventTracer` is an event
collector. The main way to access the events is through the
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events` method,
which is essentially a way to filter events based on some criteria and also
to "await" them if they are not yet available.

The main way to specify the criteria is the method parameter
(always required) called ``predicate``, which is a callable
that takes in input an event and returns a boolean. The predicate 
is essentially a filter that is iterates over all the events
(present and future) and selects the ones that match your rules
(i.e. the ones that return ``True`` when passed to the predicate), so that's
the right place to encode your criteria. In the simplest case, those criteria
are expressed as a logic expression on
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` attributes.
For example:

.. code-block:: python

    def predicate(event: ReceivedEvent) -> bool:
        return (
            (
                # The event can be from one of those two devices
                event.has_device("device/name/1") or 
                event.has_device("device/name/2")
            ) and

            # the event can have any attribute other that this one
            not event.has_attribute("notThisAttr") and

            # The attribute value is less than 5 or greater than 50
            (event.current_value < 5 or event.current_value > 50) and

            # event has been received less than 60 seconds ago
            event.reception_age() < 60
        )
    
    # Query the events
    events = tracer.query_events(predicate)

    # Alternatively, this can be done in one line
    events = tracer.query_events(
        lambda event: (
            event.has_device("device/name/1") or 
            event.has_device("device/name/2")
        ) and
        not event.has_attribute("notThisAttr") and
        (event.current_value < 5 or event.current_value > 50) and
        event.reception_age() < 60
    )

In more complex cases, predicates can also include complex verification logic
which include the history of the events. In practice, you do that using the
``tracer`` object and
:py:attr:`~ska_tango_testing.integration.TangoEventTracer.events` property,
which is a thread-safe copy of the events that have been received so far. 
For example: 

.. code-block:: python

    def event_has_previous(event: ReceivedEvent) -> bool:
        """Check if the event is not the first one from its device
        and attribute. 
        """

        for evt in tracer.events:
            if (
                evt.device == event.device and
                evt.attribute == event.attribute and
                evt.reception_time < event.reception_time
            ):
                return True
        
        return False        

    # Query the events
    events = tracer.query_events(predicate)

Some meaningful examples of predicates are available in the
:py:mod:`ska_tango_testing.integration.predicates` module, where are
defined the predicates that are used to implement
:py:meth:`~ska_tango_testing.integration.assertions.has_change_event_occurred`.

Timeout in queries
~~~~~~~~~~~~~~~~~~

The second most important element of
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events`
is the ``timeout`` parameter, which is the maximum time to wait for the
events (in seconds) to arrive, if they are not already present. 

.. code-block:: python

    # Query the events and wait for 10 seconds
    events = tracer.query_events(predicate, timeout=10)

Other than the predicate, a second (usually hidden) parameter to specify
the criteria is the ``target_n_events`` parameter, which is the number of
events that you expect to match the predicate. If you pass a timeout, the query
will not be satisfied until the number of events that match the predicate is
equal or greater to ``target_n_events``. If you don't reach that number at
call time, the process that called the query will wait. While that process is
waiting, the tracer will continue to collect events, and eventually if it
collects enough events to satisfy the query, the process will be unblocked.
Alternatively, if the timeout is reached, the query will return the events
that have been collected so far and the process will continue. 
``target_n_events`` defaults to 1, so if you don't specify it, the query will
return when there is at least one event that matches the predicate.

An important note is that ``target_n_events`` is meaningful only when there
is a timeout, because if there isn't the call will return immediately
(regardless of the number of events that match the predicate), and
so that criterion is not relevant.

**NOTE**: using assertion code that use a timeout can be a good alternative
to using a sleep in your test code, or writing explicit "wait" functions.

Custom assertions
~~~~~~~~~~~~~~~~~

To mantain test code clean, readable and in a certain measure reusable, if
you have a complex assertion based on a query (even better if you need to
reuse it in multiple tests), you can define a custom `assertpy` assertion.

`assertpy` permits you to extend their set of assertion methods by creating
new functions like the ones that are made available on
:py:mod:`ska_tango_testing.integration.assertions` and then export them
using the `assertpy` API method call ``add_extension(function)``. So given
a your query (maybe with one or more complex predicates already
defined separately), you can define a custom assertion which calles the query
(using the tracer and the timeout present in the test context), assert on the
result and if the assertion fails, personalize the error message
adding meaningful information.

If you want to define a custom assertion, we suggest you read
`assertpy documentation <https://assertpy.github.io/docs.html>`_ 
to understand the structure which is expected for your code and also to
look at the already defined assertions in
:py:mod:`ska_tango_testing.integration.assertions` (and to the predicates used
in the same module) to understand how to use the tracer for queries.

If your custom assertion seem to be generic enough to be useful in other
contexts, please consider to contribute it to the library by opening a MR.










