"""Channel gateway — adapter pattern (§2, §5, §6).

Core engine TIDAK BOLEH tahu detail platform. Semua channel knowledge
ter isolasi di masing-masing adapter.
"""
from .base import ChannelAdapter, MessageContext  # noqa: F401
