"""Redis configuration."""
from typing import Optional

from pydantic import ConfigDict

from pipeflow.core import PipeConfig


class RedisConfig(PipeConfig):
    """Redis configuration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Connection settings
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None

    # SSL settings
    ssl: bool = False
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_password: Optional[str] = None

    # Operation mode
    key: Optional[str] = None
    channel: Optional[str] = None
    stream_name: Optional[str] = None
    list_name: Optional[str] = None
    max_entries: Optional[int] = None
