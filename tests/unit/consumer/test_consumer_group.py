"""This module contains tests of the :py:class:`MockConsumer` class."""
from typing import Any, Dict, List, Optional

import pytest

from ska_tango_testing.mock import CharacterizerType, MockConsumerGroup
from ska_tango_testing.mock.placeholders import Anything

from .conftest import FakeItem, TestingProducerProtocol


def test_assert_no_item_when_no_item(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    voltage: Any,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param voltage: a "voltage" item to use in testing
    """
    producer.schedule_put(1.2, voltage)
    consumer_group.assert_no_item()


def test_assert_no_item_when_item_is_available(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    voltage: Any,
) -> None:
    """
    Test that `assert_no_item` fails when an item is produced in time.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param voltage: a "voltage" item to use in testing
    """
    producer.schedule_put(0.2, voltage)

    with pytest.raises(
        AssertionError,
        match="Expected no item, but an item is available.",
    ):
        consumer_group.assert_no_item()


@pytest.mark.parametrize("characteristic_check", [False, True])
@pytest.mark.parametrize("equality_check", [False, True])
@pytest.mark.parametrize("category_check", [False, True])
def test_assert_item_when_no_item(  # pylint: disable=too-many-arguments
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    voltage: Any,
    characterizer: CharacterizerType,
    category_check: bool,
    equality_check: bool,
    characteristic_check: bool,
) -> None:
    """
    Test that `assert_item` fails when the item is produced too late.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param voltage: a "voltage" item to use in testing
    :param characterizer: a callable that extracts item characteristics.
    :param category_check: whether to check the item category
    :param equality_check: whether to check item equality
    :param characteristic_check: whether to check item characteristics
    """
    producer.schedule_put(1.2, voltage)

    args = [voltage] if equality_check else []
    kwargs = characterizer({"item": voltage}) if characteristic_check else {}
    if category_check:
        kwargs["category"] = "voltage"

    with pytest.raises(
        AssertionError,
        match="Expected matching item within the first 1 items.",
    ):
        consumer_group.assert_item(*args, **kwargs)


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
@pytest.mark.parametrize("characteristic_check", [None, False, True])
@pytest.mark.parametrize("equality_check", [None, False, True])
@pytest.mark.parametrize("category_check", [None, False, True])
# pylint: disable-next=too-many-arguments
def test_assert_item_when_items_are_available(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    item_library: Dict[str, FakeItem],
    characterizer: CharacterizerType,
    category_check: Optional[bool],
    equality_check: Optional[bool],
    characteristic_check: Optional[bool],
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

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param item_library: a library of items for use in testing
    :param characterizer: a callable that extracts item characteristics.
    :param category_check: whether to check the category, and if so
        whether to check the right one
    :param equality_check: whether to check item equality, and if so
        whether to check the right item
    :param characteristic_check: whether to check item characteristics,
        and if so whether to check the right ones
    :param position: (one-based) position in the queue at which the item
        will appear
    :param lookahead: lookahead setting for the assertion.
    """
    producer.schedule_put(0.2, item_library["voltage_1"])
    producer.schedule_put(0.4, item_library["voltage_2"])
    producer.schedule_put(0.5, item_library["voltage_3"])

    if equality_check is None and characteristic_check is None:
        # At most we are checking the category, so the first item will match,
        # regardless of the position in which we have placed the nominally
        # matching item.
        good_voltage = item_library["voltage_1"]
    else:
        good_voltage = item_library[f"voltage_{position}"]
    bad_voltage = item_library["bad_voltage"]

    args_dict: Dict[Optional[bool], List[Any]] = {
        None: [],
        False: [bad_voltage],
        True: [good_voltage],
    }

    kwargs: Dict[str, Any] = {}
    if characteristic_check is False:
        kwargs.update(characterizer({"item": bad_voltage}))
    elif characteristic_check is True:
        kwargs.update(characterizer({"item": good_voltage}))

    if category_check is False:
        kwargs["category"] = "wrong category"
    elif category_check:
        kwargs["category"] = "voltage"

    expect_to_pass = True
    if (
        category_check is False
        or equality_check is False
        or characteristic_check is False
    ):
        expect_to_pass = False
    elif position > lookahead and (equality_check or characteristic_check):
        expect_to_pass = False

    if expect_to_pass:
        item = consumer_group.assert_item(
            *args_dict[equality_check], lookahead=lookahead, **kwargs
        )
        assert item == {
            "category": "voltage",
            "item": good_voltage,
            "name": good_voltage.name,
            "quality": good_voltage.quality,
            "value": good_voltage.value,
        }
    else:
        with pytest.raises(
            AssertionError,
            match=f"Expected matching item within the first {lookahead} items",
        ):
            consumer_group.assert_item(
                *args_dict[equality_check], lookahead=lookahead, **kwargs
            )


def test_assert_no_specific_item_when_no_item(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    voltage: Any,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param voltage: a "voltage" item to use in testing
    """
    producer.schedule_put(1.2, voltage)
    consumer_group["voltage"].assert_no_item()


def test_assert_no_specific_item_when_item_in_different_queue(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    voltage: FakeItem,
) -> None:
    """
    Test that assert_no_item succeeds when the item is produced too late.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param voltage: a "voltage" item to use in testing
    """
    producer.schedule_put(0.2, voltage)
    consumer_group["current"].assert_no_item()


def test_assert_no_specific_item_when_item_is_available(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    voltage: FakeItem,
) -> None:
    """
    Test that `assert_no_item` fails when an item is produced in time.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param voltage: a "voltage" item to use in testing
    """
    producer.schedule_put(0.2, voltage)

    with pytest.raises(
        AssertionError,
        match="Expected no item, but an item is available.",
    ):
        consumer_group["voltage"].assert_no_item()


@pytest.mark.parametrize("characteristic_check", [False, True])
@pytest.mark.parametrize("equality_check", [False, True])
# pylint: disable-next=too-many-arguments
def test_assert_specific_item_when_no_item(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    item_library: Dict[str, FakeItem],
    characterizer: CharacterizerType,
    equality_check: bool,
    characteristic_check: bool,
) -> None:
    """
    Test that `assert_item` fails when the item is produced too late.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param item_library: a library of items for use in testing
    :param characterizer: a callable that extracts item
        characteristics.
    :param equality_check: whether to check item equality
    :param characteristic_check: whether to check item characteristics
    """
    voltage = item_library["voltage_1"]

    producer.schedule_put(0.2, item_library["current_1"])
    producer.schedule_put(1.5, voltage)

    args = [voltage] if equality_check else []
    kwargs = characterizer({"item": voltage}) if characteristic_check else {}

    with pytest.raises(
        AssertionError,
        match="Expected matching item within the first 1 items.",
    ):
        consumer_group["voltage"].assert_item(*args, **kwargs)


@pytest.mark.parametrize("lookahead", [1, 2])
@pytest.mark.parametrize("position", [1, 2, 3])
@pytest.mark.parametrize("characteristic_check", [None, False, True])
@pytest.mark.parametrize("equality_check", [None, False, True])
# pylint: disable-next=too-many-arguments
def test_assert_specific_item_when_items_are_available(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    item_library: Dict[str, FakeItem],
    characterizer: CharacterizerType,
    equality_check: Optional[bool],
    characteristic_check: Optional[bool],
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

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param item_library: a library of items for use in testing
    :param characterizer: a callable that extracts item
        characteristics.
    :param equality_check: whether to check item equality
    :param characteristic_check: whether to check item characteristics
    :param position: (one-based) position in the queue at which the item
        will appear
    :param lookahead: lookahead setting for the assertion.
    """
    producer.schedule_put(0.1, item_library["current_1"])
    for i in range(1, 4):
        producer.schedule_put(0.2 * i, item_library[f"voltage_{i}"])

    if equality_check is None and characteristic_check is None:
        # At most we are checking the category, so the first item will match,
        # regardless of the position in which we have placed the nominally
        # matching item.
        good_voltage = item_library["voltage_1"]
    else:
        good_voltage = item_library[f"voltage_{position}"]
    bad_voltage = item_library["bad_voltage"]

    args_dict: Dict[Optional[bool], List[Any]] = {
        None: [],
        False: [bad_voltage],
        True: [good_voltage],
    }

    kwargs: Dict[str, Any] = {}
    if characteristic_check is False:
        kwargs.update(characterizer({"item": bad_voltage}))
    elif characteristic_check is True:
        kwargs.update(characterizer({"item": good_voltage}))

    expect_to_pass = True
    if equality_check is False:
        expect_to_pass = False
    if characteristic_check is False:
        expect_to_pass = False
    if position > lookahead and (equality_check or characteristic_check):
        expect_to_pass = False

    if expect_to_pass:
        item = consumer_group["voltage"].assert_item(
            *args_dict[equality_check], lookahead=lookahead, **kwargs
        )
        assert item == {
            "category": "voltage",
            "item": good_voltage,
            "name": good_voltage.name,
            "quality": good_voltage.quality,
            "value": good_voltage.value,
        }
    else:
        with pytest.raises(
            AssertionError,
            match=f"Expected matching item within the first {lookahead} items",
        ):
            consumer_group["voltage"].assert_item(
                *args_dict[equality_check], lookahead=lookahead, **kwargs
            )


def test_assert_consumes_items(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    item_library: Dict[str, FakeItem],
) -> None:
    """
    Test that our assertions consume items as appropriate.

    We drop a bunch of items onto the queue, and then assert their
    presence one by one. At the end, we assert that there are no items
    left.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param item_library: a library of items for use in testing
    """
    producer.schedule_put(0.2, item_library["status_connected"])

    producer.schedule_put(0.5, item_library["current_1"])
    producer.schedule_put(0.5, item_library["current_2"])
    producer.schedule_put(0.5, item_library["current_3"])

    producer.schedule_put(0.4, item_library["voltage_1"])
    producer.schedule_put(0.6, item_library["voltage_2"])
    producer.schedule_put(0.8, item_library["voltage_3"])

    producer.schedule_put(1.0, item_library["status_disconnected"])

    consumer_group.assert_item(
        item_library["status_connected"], category="status"
    )

    consumer_group["voltage"].assert_item(item_library["voltage_1"])
    consumer_group["voltage"].assert_item(item_library["voltage_2"])
    consumer_group["voltage"].assert_item(item_library["voltage_3"])
    consumer_group["voltage"].assert_no_item()

    consumer_group["current"].assert_item(
        item_library["current_1"], lookahead=3
    )
    consumer_group["current"].assert_item(
        item_library["current_2"], lookahead=2
    )
    consumer_group["current"].assert_item(item_library["current_3"])
    consumer_group["current"].assert_no_item()

    consumer_group.assert_item(
        item_library["status_disconnected"], category="status"
    )

    consumer_group.assert_no_item()


def test_assert_any_item_when_item_is_available(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    item_library: Dict[str, FakeItem],
) -> None:
    """
    Test that Anythingh can be used to assert an item against the group.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param item_library: a library of items for use in testing
    """
    producer.schedule_put(0.2, item_library["voltage_1"])
    consumer_group.assert_item(Anything)


def test_assert_any_specific_item_when_item_is_available(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    item_library: Dict[str, FakeItem],
) -> None:
    """
    Test that Anything can be used to assert a specific item.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param item_library: a library of items for use in testing
    """
    producer.schedule_put(0.2, item_library["voltage_1"])
    consumer_group["voltage"].assert_item(Anything)


def test_assert_any_characteristic_when_item_has_characteristic(
    consumer_group: MockConsumerGroup,
    producer: TestingProducerProtocol,
    item_library: Dict[str, FakeItem],
) -> None:
    """
    Test that Anything can be used to assert against a characteristic.

    :param consumer_group: the consumer under test
    :param producer: a producer to test against
    :param item_library: a library of items for use in testing
    """
    producer.schedule_put(0.2, item_library["voltage_1"])

    consumer_group.assert_item(
        name=item_library["voltage_1"].name,
        value=item_library["voltage_1"].value,
        quality=Anything,
    )
