.. _custom_queries_and_assertions:


Custom queries and assertions using TangoEventTracer
----------------------------------------------------

In :ref:`Getting Started <getting_started_tracer>` we saw how to use the
:py:class:`~ska_tango_testing.integration.TangoEventTracer` to capture events
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
that takes as input an event and returns a boolean. The predicate 
is essentially a filter that iterates over all the events
and selects the ones that match your criteria.
In the simplest case, those criteria
are expressed as a logic expression on
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` properties.
For example:

.. code-block:: python

    # you can define your predicate as a function and then pass it to the query
    def my_predicate(event: ReceivedEvent) -> bool:
        """Return true if a event is from one of two devices (...),
        is not related to a specific attribute called "notThisAttr",
        has a value less than 5 or greater than 50, and has been received
        less than 60 seconds ago."""
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
    matching_events = tracer.query_events(my_predicate)

    # Alternatively, this can be done in one line using a lambda expression
    matching_events = tracer.query_events(
        lambda event: (
            event.has_device("device/name/1") or 
            event.has_device("device/name/2")
        ) and
        not event.has_attribute("notThisAttr") and
        (event.current_value < 5 or event.current_value > 50) and
        event.reception_age() < 60
    )

**NOTE**: in the predicate we often prefer to use the
``has_X`` methods of the 
:py:class:`~ska_tango_testing.integration.event.ReceivedEvent` class
instead of directly accessing and comparing properties values. 
This is because the ``has_X`` methods
are more robust and can handle some tricky cases (like the case insensitive
comparison of the attribute name; see
:py:class:`ska_tango_testing.integration.event.ReceivedEvent`
for more information).

In more complex cases, predicates can also include complex verification logic
which include the history of the events. In practice, you do that using the
``tracer`` object and
:py:attr:`~ska_tango_testing.integration.TangoEventTracer.events` property,
which is a thread-safe copy of the events that have been received so far. 
For example: 

.. code-block:: python

    def event_is_first(event: ReceivedEvent) -> bool:
        """Check if the event is the first one from its device and attribute. 
        """
        # to evaluate the predicate you can use not only the event data
        # but also all the other events that have been received so far
        for evt in tracer.events:
            if (
                evt.has_device(event.device_name) and
                evt.has_attribute(event.attribute_name) and
                evt.reception_time < event.reception_time
            ):
                # stop when any precedent event is found
                # (event has at least a previous one => not the first
                # from the this device and attribute)
                return False 

        # no event from the same device and attribute found
        # before the current event => event is the first
        return True  

    # Get all events that are the first from each device and attribute
    matching_events = tracer.query_events(event_is_first)

**NOTE**: if your query has a timeout, don't worry accessing ``tracer.events``.
That property is thread-safe and, since the tracer will continue to collect
events, it will be updated with the new events that arrive while the query
is waiting, so every time your predicate will be evaluated it will use
updated data.

Timeout in queries
~~~~~~~~~~~~~~~~~~

The second most important element of
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events`
is the ``timeout`` parameter, which is the maximum time to wait for the
events (in seconds) to arrive, if they are not already present.

.. code-block:: python

    # Query the events and wait for 10 seconds
    matching_events = tracer.query_events(my_predicate, timeout=10)

Other than the predicate and the timeout, a third (usually hidden)
parameter used to specify the criteria is the ``target_n_events``, 
which is the number of
events that you expect to match the predicate. ``target_n_events`` works
together with ``timeout`` in the following way: when you specify both of them,
the query will not be satisfied until the number of events that match the predicate is
equal or greater to ``target_n_events``. If you don't reach that number at
call time, the process that called the query will wait. While that process is
waiting, the tracer will continue to collect events, and eventually if it
collects enough events to satisfy the query, the process will be unblocked.
Alternatively, if the timeout is reached before the target is reached,
the query will return the events that have been collected so far and the
process will continue. Since you can wait for events only when specifying
a timeout, the wait cannot be infinite. When you don't specify 
``target_n_events`` it defaults to 1, so the query will
return when there is at least one event that matches the predicate.

Essentially, ``target_n_events`` is meaningful only when there
is a timeout, because if there isn't the call will always return immediately
regardless of the number of events that match the predicate.

**NOTE**: using assertion code that use a timeout can be a good alternative
to using a ``sleep`` command in your test code, or writing explicit custom 
"wait" functions for things. Since the timeout is customizable for each call,
you can have a fine-grained control on how long you want to wait for the
events to arrive, and so for a certain condition to be satisfied.

Custom assertions
~~~~~~~~~~~~~~~~~

To keep test code clean, readable and in a certain measure reusable, if
you have a complex assertion based on a query (even better if you need to
reuse it in multiple tests), you can define a custom `assertpy` assertion.

`assertpy` permits you to extend their set of assertion methods by creating
new functions like the ones that are made available on
:py:mod:`ska_tango_testing.integration.assertions` and then export them
using the `assertpy` API method call ``add_extension(function)``. So given
your query (maybe with one or more complex predicates already
defined separately), you can define a custom assertion which calls the query
(using the tracer and the timeout present in the test context), assert on the
result and if the assertion fails, personalize the error message
adding meaningful information.

**NOTE**: Custom assertions of this module are already exported
to the `assertpy` context in :py:mod:`ska_tango_testing.integration`, so
if you are an end-user, when you import the module somewhere in your tests
you already have access to the assertions. Sometimes your IDE may not
recognize the custom assertions, but they are there.

If you want to define a custom assertion, we recommend you read
`assertpy documentation <https://assertpy.github.io/docs.html>`_ 
to understand the structure which is expected for your code and also to
look at the already defined assertions in
:py:mod:`ska_tango_testing.integration.assertions` (and to the predicates used
in the same module) to understand how to use the tracer for queries.

If your custom assertion seems to be generic enough to be useful in other
contexts, please consider contributing it to the library by opening a
merge request.










