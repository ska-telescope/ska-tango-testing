.. _custom_queries_and_assertions:

Custom queries and assertions using TangoEventTracer
----------------------------------------------------

Interacting with the tracer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the :ref:`Getting Started <getting_started_tracer>` section, we explored
how to interact with the :py:class:`~ska_tango_testing.integration.TangoEventTracer`
through the *assertpy* :py:mod:`~ska_tango_testing.integration.assertions`
provided by the module. These assertions are very
user-friendly and allow you to write clean and readable test code. They will
likely suffice for most of your needs.

However, there may be situations where you need to interact with the tracer
more directly. This could be for example because you need to implement an
assertion that is not covered by the provided assertions, or because you
want to use the tracer as a more fine-grained event synchronisation tool.
To do this, we propose two methods of interacting with the tracer:

1. Using predicates to filter events.
2. Using queries to define more complex interactions.

Before adventuring into these methods, think well if you really need them
or there may already be some :ref:`Advanced Features <advanced_use_cases>`
that can help you achieve your goal in a simpler way. If you implement
custom assertions, consider that during time the way assertions are implemented
may change and so 1) you may not benefit from future improvements and 2) in
some case you may suffer from backward compatibility issues (although we
strive to keep them to a minimum).


Interaction through the predicate shortcut
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first method of interacting directly with the tracer is via the 
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events`
method.

:py:meth:`~ska_tango_testing.integration.TangoEventTracer.query_events`
allows you to query events collected by the tracer using a predicate as
filter to select only the events that match specific criteria.
Concretely, this methods requires a parameter called ``predicate``,
which accepts lambda functions or named functions. These
functions take an event as input and return a boolean value indicating
whether the event matches the criteria.

.. code-block:: python

    # You can define your predicate as a function and then pass it to the query
    def my_predicate(event: ReceivedEvent) -> bool:
        """Return True if an event is from one of two devices (...),
        is not related to a specific attribute called "notThisAttr",
        has a value less than 5 or greater than 50, and was received
        less than 60 seconds ago."""
        return (
            (
                # The event must be from one of these two devices
                event.has_device("device/name/1") or 
                event.has_device("device/name/2")
            ) and

            # The event must not relate to this attribute
            not event.has_attribute("notThisAttr") and

            # The attribute value must be less than 5 or greater than 50
            (event.current_value < 5 or event.current_value > 50) and

            # The event must have been received less than 60 seconds ago
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

**NOTE**: your predicates can be arbitrarily complex and can include logic
involving the history of events. You can reference ``tracer.events`` to
access all events received so far and use them to evaluate your predicate.

Since not all your events may have been received yet, you can wait for them
to arrive using the ``timeout`` parameter of the query. This parameter
specifies the maximum time (in seconds) to wait for events to arrive.

.. code-block:: python

    # Query the events and wait for 10 seconds
    matching_events = tracer.query_events(my_predicate, timeout=10)

Other than the predicate and timeout, a third (usually hidden) parameter
called ``target_n_events`` is present. This parameter specifies the number
of events you expect to match the predicate. ``target_n_events`` works with
``timeout`` as follows: when both are specified, the query will not be
satisfied until the number of matching events is equal to or greater than
``target_n_events``. If this number is not reached at call time, the process
will wait. While waiting, the tracer continues collecting events. If enough
events are collected to satisfy the query, the process is unblocked. If the
timeout is reached before the target is met, the query will return the events
collected so far, and the process will continue. Without a timeout, the
wait cannot be infinite. If ``target_n_events`` is unspecified, it defaults
to 1, so the query will return when at least one matching event is found.

.. code-block:: python

    # Wait for at least 3 events to match the predicate
    # (or wait for 10 seconds if 3 events are not received)
    matching_events = tracer.query_events(
        my_predicate, timeout=10, target_n_events=3
    )

**NOTE**: assertion code with timeouts can be a good alternative to using
``sleep`` commands or writing custom "wait" functions. Since the timeout is
customisable for each call, you have fine-grained control over how long to
wait for events to arrive and conditions to be satisfied.


Interaction through queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Internally, the tracer represents the interrogations it receives as
:py:class:`~ska_tango_testing.integration.query.EventQuery` objects. You
can do the same by creating your own queries and evaluating them using the
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.evaluate_query`
method.

:py:class:`~ska_tango_testing.integration.query.EventQuery` represents an
interrogation over events received by the tracer or that will be received
in the future. Every time you make an interrogation to the tracer (e.g.,
when you call the
:py:class:`~ska_tango_testing.integration.TangoEventTracer.query_events`
method or a custom assertion), a query
object is created. Queries are capable of self-evaluating through a success
criterion and logic for handling updates to the collected events. They also
embed the timeout concept, enabling them to wait for events if they are not
already present. At the end of the evaluation process, a query may either
**succeed** or **fail**, and this outcome can be checked using the
:py:meth:`~ska_tango_testing.integration.query.EventQuery.succeeded` method.

To evaluate a query, create an instance of the query and pass it as an
argument to the
:py:meth:`~ska_tango_testing.integration.TangoEventTracer.evaluate_query`
method. Note that
:py:class:`~ska_tango_testing.integration.query.EventQuery`
is an abstract class, so you must either
subclass it or use one of the subclasses already provided by the module,
such as :py:class:`~ska_tango_testing.integration.query.NStateChangesQuery`.

Here is an example of creating and evaluating a query:

.. code-block:: python

    from ska_tango_testing.integration.query import NStateChangesQuery
    
    # Create a query object for an event with a specific attribute value
    # from a specific device. Set a timeout of 10 seconds.
    query = NStateChangesQuery(
        device_name="sys/tg_test/1",
        attribute_name="State",
        attribute_value=TARGET_STATE,
        timeout=10,
    )
    tracer.evaluate_query(query)

    # Check if the query succeeded
    assert_that(query.succeeded()).described_as(
        # Use the query description to provide more information about
        # the interrogation and the reason for the failure
        f"The following query is expected to succeed:\n{query.describe()}"

        # Provide a list of events in the tracer at the time of evaluation
        # to understand why the query failed
        f"\nEvents in the tracer:\n{''.join([str(e) for e in tracer.events])}"
    ).is_true()

If you want to learn more about how queries work and how to create them,
refer to the :py:meth:`ska_tango_testing.integration.query` API
documentation.

**Should I use queries or predicates?** The choice between using queries or
predicates depends on the complexity of the logic you need to implement and
the context where you are doing it. If you need a simple shortcut to get
events that match a specific criterion, predicates are the way to go. If you
need more complex logic that go beyond simple filtering, or you are
implementing some sort of structured test harness (e.g., that deals with
synchronisation) probably queries are the best choice, as they provide a
more structured and customisable way to interact with the tracer
(see for example the
:py:class:`~ska_tango_testing.integration.query.QueryWithFailCondition`
class for an example of advanced usage).

Custom assertions
~~~~~~~~~~~~~~~~~

To keep test code clean, readable, and reusable, consider defining a custom
`assertpy` assertion for complex queries, especially if they are used across
multiple tests. `assertpy` allows you to extend its set of assertion methods
by creating new functions, like those available in
:py:mod:`ska_tango_testing.integration.assertions`. These can then be
exported using the `assertpy` API method ``add_extension(function)``. Given
your query (potentially with one or more complex predicates defined
separately), you can define a custom assertion that invokes the query (using
the tracer and timeout within the test context), asserts on the result, and
customises the error message with meaningful information if the assertion
fails.

**NOTE**: Custom assertions in this module are already exported to the
`assertpy` context within :py:mod:`ska_tango_testing.integration`. If you
are an end-user, importing the module in your tests automatically provides
access to these assertions. Your IDE may not always recognise the custom
assertions, but they are present.

If you wish to define a custom assertion, we recommend reviewing the
`assertpy documentation <https://assertpy.github.io/docs.html>`_ to
understand the expected structure for your code. Additionally, examine the
existing assertions in :py:mod:`ska_tango_testing.integration.assertions`
to learn how to leverage the tracer for queries.

If your custom assertion appears generic enough to be useful in other
contexts, please consider contributing it to the library by submitting a
merge request.

**NOTE**: consider that the assertions we provide evolve over time, and
so some your custom assertions may become redundant or may need to be
updated to reflect changes in the library. We strive to keep backward
compatibility issues to a minimum, but they may still occur.









