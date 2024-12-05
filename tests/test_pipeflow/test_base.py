"""Test base pipe functionality."""
import pandas as pd
import pytest
from pydantic import BaseModel, ConfigDict

from pipeflow import DataFramePipe, DataFramePipeConfig


# Move test classes to conftest.py or create them in fixtures
@pytest.fixture
def test_config():
    class Config(DataFramePipeConfig):
        """Test configuration."""

        model_config = ConfigDict(arbitrary_types_allowed=True)

        column: str

    return Config(column="a", validate_types=True)


@pytest.fixture
def test_pipe(test_config):
    class Pipe(DataFramePipe):
        """Test pipe implementation."""

        def __init__(self, config: DataFramePipeConfig):
            """Initialize test pipe."""
            super().__init__(config)
            self.config = config

        async def process(self, df: pd.DataFrame) -> pd.DataFrame:
            return df[[self.config.column]]

    return Pipe(test_config)


@pytest.mark.asyncio
async def test_dataframe_pipe(test_pipe):
    """Test DataFrame pipe functionality."""
    # Test processing
    input_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    result = await test_pipe(input_data)
    assert list(result.columns) == ["a"]
    assert len(result) == 3


@pytest.mark.asyncio
async def test_dataframe_type_validation(test_pipe):
    """Test DataFrame type validation."""
    # Test type validation
    with pytest.raises(TypeError):
        await test_pipe({"a": [1, 2, 3]})
