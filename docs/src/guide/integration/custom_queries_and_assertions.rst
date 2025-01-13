.. _custom_queries_and_assertions:

Custom queries and assertions using TangoEventTracer
----------------------------------------------------

Interacting with the tracer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the :ref:`Getting Started <getting_started_tracer>` section we saw how to
interact with the
:py:class:`~ska_tango_testing.integration.TangoEventTracer`
through the *assertpy*
:py:mod:`~ska_tango_testing.integration.assertions` that are already
provided by the module. These assertions are very user friendly
and permit you to write clean and readable test code. Probably, they will
be enough for most of your needs.

However, sometimes you may need to interact with the tracer in a more
"technical" way, for example to create custom assertions that are not already
present in the module, to make quick interrogations and retrieve events, 
or to implement more custom synchronization logic in a your test harness.
Here we will see how to do that.

Interaction through the predicate shortcut
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first method to interact with the tracer is through
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events`.

:py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events` is a
method that permits you to query the events that have been collected by the
tracer using a predicate, which is essentially a filter that is
applied to each event to check if it matches the criteria you are looking for.
You define this criteria through the ``predicate`` parameter of the method,
which accepts lambda functions or a named functions that take as an input
an event and return a boolean value to indicate if the event matches the
criteria or not.



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


**NOTE**: your predicates can be arbitrarily complex, and can include
also some logic that involves the history of the events. In practice, you
can reference ``tracer.events`` to access all the events that have been
received so far and use them to evaluate your predicate.

Since not all your events may have been received yet, you can wait for them
to arrive using the ``timeout`` parameter of the query, which is the
maximum time to wait for the
events (in seconds) to arrive, if they are not already present.

.. code-block:: python

    # Query the events and wait for 10 seconds
    matching_events = tracer.query_events(my_predicate, timeout=10)

Other than the predicate and the timeout, a third (usually hidden)
parameter called ``target_n_events`` is present. This parameter is used to
specify the number of events that you expect to match the predicate. 
``target_n_events`` works together with ``timeout`` in the following way:
when you specify both of them, the query will not be satisfied
until the number of events that match the predicate is
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


Interaction through queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Internally the tracer represents the integrations as
:py:class:`~ska_tango_testing.integration.query.EventQuery` objects and you
can do that as well by creating your own queries and evaluating them using
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.evaluate_query`
method.

:py:class:`~ska_tango_testing.integration.query.EventQuery` is a
class that represents an interrogation over the events that have been received
by the tracer or that will be received in the future. It is created every time
an interrogation is made to the tracer (e.g., when you call the
``query_events`` method of the tracer or any of the given custom assertions),
and is capable of auto-evaluating by itself through a success criteria and a
logic to handle the update of the events that are collected. It also embeds
the timeout concept so it is capable of waiting for the events to arrive if
they are not already present. At the end of the evaluation process, the query
may have **succeed** or **failed** and you can know that by calling its
:py:meth:`~ska_tango_testing.integration.query.EventQuery.succeeded` method.

To evaluate a query you have to create the instance of the query and then
call the
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.evaluate_query`
method of the tracer, passing the query as an argument. You may have noticed
that by itself :py:class:`~ska_tango_testing.integration.query.EventQuery`
is an abstract class, so you have to create a subclass of it to use it or
use one of the subclasses that are already provided by the module
:py:mod:`ska_tango_testing.integration.query`
(like :py:class:`~ska_tango_testing.integration.query.NStateChangesQuery`).

Here there follow an example on how to create a query and evaluate it:

.. code-block:: python

    # ...

    from ska_tango_testing.integration.query import NStateChangesQuery
    query = NSateChangesQuery(
        device_name="sys/tg_test/1",
        attribute_name="State",
        attribute_value=TARGET_STATE,
        timeout=10,
    )
    tracer.evaluate_query(query)

    # check if the query succeeded
    assert_that(query.succeeded()).described_as(
        # use the query description to provide more information
        # about the done interrogation and the reason of the failure
        f"The following query is expected to succeed:\n{query.describe()}"

        # provide also the list of events in the tracer at the moment of the
        # evaluation, so you can understand why the query failed
        f"\nEvents in the tracer:\n{''.join([str(e) for e in tracer.events])}"               
    ).is_true() 

If you want to know more about how queries work and how to create them, you can
read :py:meth:`ska_tango_testing.integration.query` API documentation.

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









