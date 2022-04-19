"""This subpackage provides mock consumers for testing asynchronous code."""

__all__ = ["MockConsumer", "ProducerProtocol"]


from .consumer import MockConsumer
from .producer_protocol import ProducerProtocol
