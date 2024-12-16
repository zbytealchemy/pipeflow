"""Redis plugin registration."""
from pipeflow.plugins import register_sink, register_source

from .sink import RedisSinkPipe
from .source import RedisSourcePipe

# Register the plugins
register_source("redis")(RedisSourcePipe)
register_sink("redis")(RedisSinkPipe)
