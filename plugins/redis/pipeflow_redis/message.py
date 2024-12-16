"""Redis message types."""
from typing import Any, Dict, Optional

from pipeflow.core import Message


class RedisMessage(Message):
    """Message from Redis."""

    key: str
    value: Any
    source: str  # One of: "pubsub", "stream", "list", "key-value"
    metadata: Optional[Dict[str, Any]] = None
