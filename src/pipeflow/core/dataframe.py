"""Base implementations for Pipeflow pipes."""
import logging
from typing import Any, Dict, Optional, Type, TypeVar, Union, cast

import pandas as pd
from prefect import task
from pydantic import ConfigDict

from pipeflow.core.pipe import BasePipe, ConfigurablePipe, PipeConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = TypeVar("P", bound=BasePipe[Any, Any])
CP = TypeVar("CP", bound=ConfigurablePipe[Any, Any, Any])


class DataFramePipeConfig(PipeConfig):
    """Configuration for DataFrame pipes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    validate_types: bool = True


class DataFramePipe(ConfigurablePipe[pd.DataFrame, pd.DataFrame, DataFramePipeConfig]):
    """Base class for pipes that process pandas DataFrames.

    Example:
        >>> class FilterPipeConfig(DataFramePipeConfig):
        ...     column: str
        ...     value: Any
        ...
        >>> class FilterPipe(DataFramePipe):
        ...     def __init__(self, config: FilterPipeConfig):
        ...         super().__init__(config)
        ...
        ...     async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        ...         return df[df[self.config.column] == self.config.value]
    """

    def __init__(self, config: DataFramePipeConfig):
        """Initialize the DataFrame pipe.

        Args:
            config: Pipe configuration
        """
        super().__init__(config)
        self.context: Optional[Dict[str, Any]] = None

    async def process(self, data: Any) -> pd.DataFrame:
        """Process the input data, ensuring it's a DataFrame.

        Args:
            data: Input data

        Returns:
            Processed DataFrame

        Raises:
            TypeError: If input data is not a DataFrame and validate_types is True
        """
        if isinstance(self.config, DataFramePipeConfig) and self.config.validate_types:
            if not isinstance(data, pd.DataFrame):
                raise TypeError(f"Expected DataFrame, got {type(data)}")
        return pd.DataFrame(data)  # Ensure we return a DataFrame


@task(name="run_pipe")  # type: ignore[arg-type]
async def run_pipe(
    pipe_class: Union[Type[CP], Type[P]],
    config: Optional[Dict[str, Any]] = None,
    data: Optional[Any] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Any:
    """Run a pipe as a Prefect task.

    Args:
        pipe_class: Class of the pipe to run
        config: Optional pipe configuration (required for ConfigurablePipe)
        data: Optional input data
        context: Optional execution context

    Returns:
        Processed data

    Raises:
        ValueError: If config is not provided for ConfigurablePipe
    """
    if issubclass(pipe_class, ConfigurablePipe):
        if config is None:
            raise ValueError("Config is required for ConfigurablePipe")
        pipe = cast(
            BasePipe[Any, Any], pipe_class(config)
        )  # ConfigurablePipe requires config
    else:
        pipe = cast(BasePipe[Any, Any], pipe_class())  # BasePipe has no config

    if hasattr(pipe, "context"):
        pipe.context = context

    if data is None:
        return pipe
    return await pipe(data)
