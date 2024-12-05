"""Message classes for pipeflow."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    """Base class for all messages in pipeflow."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    value: Any
    metadata: Optional[Dict[str, Any]] = None
