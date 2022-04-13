"""This module contains tests of the `MockCallback` class."""
import queue

import pytest

from ska_tango_testing.mock_callback import QueueGroup


def test_empty_get(queue_group: QueueGroup) -> None:
    """
    Test that a get on an empty queue group causes Empty to be raised.

    :param queue_group: the queue group under test.
    """
    with pytest.raises(queue.Empty):
        queue_group.get(timeout=1)


def test_empty_get_from(queue_group: QueueGroup) -> None:
    """
    Test that a get_from on an empty queue group causes Empty to be raised.

    :param queue_group: the queue group under test.
    """
    with pytest.raises(queue.Empty):
        queue_group.get_from("foo", timeout=1)


def test_get(queue_group: QueueGroup) -> None:
    """
    Test that we can get an item from a non-empty queue group.

    :param queue_group: the queue group under test.
    """
    queue_group.put("name1", "value1")
    assert queue_group.get(timeout=1) == ("name1", "value1")

    with pytest.raises(queue.Empty):
        queue_group.get(timeout=1)


def test_get_from(queue_group: QueueGroup) -> None:
    """
    Test that we can get an item from a specified non-empty queue in a group.

    :param queue_group: the queue group under test.
    """
    queue_group.put("name1", "value1")

    with pytest.raises(queue.Empty):
        queue_group.get_from("name2", timeout=1)

    assert queue_group.get_from("name1", timeout=1) == "value1"

    with pytest.raises(queue.Empty):
        queue_group.get_from("name1", timeout=1)


def test_get_after_get_from(queue_group: QueueGroup) -> None:
    """
    Test that get and get_from work correctly together.

    :param queue_group: the queue group under test.
    """
    queue_group.put("name1", "value1")
    queue_group.put("name1", "value2")
    queue_group.put("name1", "value3")
    queue_group.put("name1", "value4")

    assert queue_group.get_from("name1", timeout=1) == "value1"
    assert queue_group.get(timeout=1) == ("name1", "value2")
    assert queue_group.get_from("name1", timeout=1) == "value3"
    assert queue_group.get(timeout=1) == ("name1", "value4")

    with pytest.raises(queue.Empty):
        queue_group.get(timeout=1)
