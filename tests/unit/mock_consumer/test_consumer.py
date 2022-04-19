"""This module contains tests of the :py:class:`MockConsumer` class."""
import pytest

from ska_tango_testing.mock_consumer import MockConsumer

from .conftest import TestingProducerProtocol


def test_assert_no_item_when_no_item(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    assert consumer.timeout == 1.0  # for the type-checker

    producer.schedule_put(consumer.timeout + 0.2, "x=1")
    consumer.assert_no_item()


def test_assert_no_item_when_next_item(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that `assert_no_item` fails when an item is produced in time.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    item = "x=1"
    producer.schedule_put(0.2, item)

    with pytest.raises(
        AssertionError,
        match=f"Expected no item to be available. Items available:\n{item}",
    ):
        consumer.assert_no_item()


def test_assert_item_when_no_item(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that `assert_item` fails when the item is produced too late.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    assert consumer.timeout == 1.0  # for the type-checker

    item = "x=1"
    producer.schedule_put(consumer.timeout + 0.2, item)

    with pytest.raises(
        AssertionError,
        match=(
            "Expected matching item within the first 1 items. No items "
            "available."
        ),
    ):
        consumer.assert_item(item)


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
def test_assert_item_when_items_are_equal(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
    position: int,
    lookahead: int,
) -> None:
    """
    Test `assert_item` when an equal item arrives.

    Specifically, we drop items onto the queue in sequence, then we
    select an item that we have dropped onto the queue, and we assert
    that it is available. Whether we expect that assertion to pass or
    fail depends on whether it falls within the lookahead that we are
    using.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    :param position: (one-based) position in the queue at which the item
        will appear
    :param lookahead: lookahead setting for the assertion.
    """
    for i in range(1, 4):
        producer.schedule_put(0.2 * i, f"item{i}={i}")

    if position <= lookahead:
        consumer.assert_item(f"item{position}={position}", lookahead=lookahead)
    else:
        with pytest.raises(
            AssertionError,
            match=f"Expected matching item within the first {lookahead} items",
        ):
            consumer.assert_item(
                f"item{position}={position}", lookahead=lookahead
            )


def test_assert_item_when_items_are_unequal(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that `assert_item` fails when the items are unequal.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    actual_item = "x=1"
    asserted_item = "x=2"

    producer.schedule_put(0.2, actual_item)

    with pytest.raises(
        AssertionError,
        match=(
            "Expected matching item within the first 1 items. Items "
            f"available:\n{actual_item}"
        ),
    ):
        consumer.assert_item(asserted_item)


def test_assert_characteristics_when_no_item(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that `assert_of_next_item` fails when the item is produced too late.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    assert consumer.timeout == 1.0  # for the type-checker

    producer.schedule_put(consumer.timeout + 0.2, "x=1")

    with pytest.raises(
        AssertionError,
        match=(
            "Expected matching item within the first 1 items. No items "
            "available."
        ),
    ):
        consumer.assert_item(name="x", value=1)


def test_assert_characteristics_when_characteristics_are_wrong(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that `assert_item` fails when the characteristics are wrong.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    producer.schedule_put(0.2, "x=1")

    with pytest.raises(
        AssertionError,
        match="Expected matching item within the first 1 items.",
    ):
        consumer.assert_item(name="x", value=2)


def test_assert_characteristics_when_characteristics_are_right(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that `assert_item` passes when the characteristics are right.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    producer.schedule_put(0.2, "x=1")
    consumer.assert_item(name="x", value=1)


def test_assert_both_item_and_characteristics(
    consumer: MockConsumer,
    producer: TestingProducerProtocol,
) -> None:
    """
    Test that `assert_item` accepts both item and characteristics.

    :param consumer: the consumer under test
    :param producer: a producer to test against
    """
    producer.schedule_put(0.2, "x=1")
    consumer.assert_item("x=1", name="x", value=1)
