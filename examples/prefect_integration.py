"""Example of advanced Prefect integration with pipeflow."""
import asyncio
from typing import Any, Dict, List

import pandas as pd
from prefect import flow, task
from prefect.context import get_run_context
from pydantic import BaseModel, ConfigDict

from pipeflow import ConfigurablePipe, DataFramePipe, DataFramePipeConfig, PipeConfig


class LoadConfig(PipeConfig):
    """Configuration for loading data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    filename: str


class LoadPipe(ConfigurablePipe[None, pd.DataFrame]):
    """Load data from a CSV file."""

    def __init__(self, config: LoadConfig):
        super().__init__(config)

    async def process(self, _: None) -> pd.DataFrame:
        """Load the CSV file."""
        return pd.read_csv(self.config.filename)


class TransformConfig(DataFramePipeConfig):
    """Configuration for data transformation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    columns: List[str]
    operation: str


class TransformPipe(DataFramePipe):
    """Transform data using specified operation."""

    def __init__(self, config: TransformConfig):
        super().__init__(config)

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the specified operation to columns."""
        result = df.copy()
        if self.config.operation == "fillna":
            result[self.config.columns] = result[self.config.columns].fillna(0)
        elif self.config.operation == "normalize":
            for col in self.config.columns:
                result[col] = (result[col] - result[col].mean()) / result[col].std()
        return result


class SaveConfig(PipeConfig):
    """Configuration for saving data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    filename: str


class SavePipe(ConfigurablePipe[pd.DataFrame, str]):
    """Save data to a CSV file."""

    def __init__(self, config: SaveConfig):
        super().__init__(config)

    async def process(self, df: pd.DataFrame) -> str:
        """Save the DataFrame to CSV."""
        df.to_csv(self.config.filename, index=False)
        return self.config.filename


@task(retries=3, retry_delay_seconds=5)
async def load_data(config: Dict[str, Any]) -> pd.DataFrame:
    """Load data with retries."""
    pipe = LoadPipe(LoadConfig(**config))
    return await pipe(None)


@task
async def transform_data(
    df: pd.DataFrame, configs: List[Dict[str, Any]]
) -> pd.DataFrame:
    """Apply multiple transformations."""
    result = df
    for config in configs:
        pipe = TransformPipe(TransformConfig(**config))
        result = await pipe(result)
    return result


@task
async def save_data(df: pd.DataFrame, config: Dict[str, Any]) -> str:
    """Save the processed data."""
    pipe = SavePipe(SaveConfig(**config))
    return await pipe(df)


@flow(name="process_data")
async def process_data(
    input_file: str, output_file: str, transform_configs: List[Dict[str, Any]]
) -> str:
    """Process data using a flow of pipes.

    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
        transform_configs: List of transformation configurations

    Returns:
        Path to the output file
    """
    # Load data
    df = await load_data({"filename": input_file})

    # Transform data
    df = await transform_data(df, transform_configs)

    # Save data
    result = await save_data(df, {"filename": output_file})

    return result


async def main():
    # Create sample data
    df = pd.DataFrame(
        {"A": [1, 2, None, 4, 5], "B": [10, 20, 30, 40, 50], "C": [None, 2, 3, None, 5]}
    )
    df.to_csv("input.csv", index=False)

    # Define transformations
    transforms = [
        {"columns": ["A", "C"], "operation": "fillna"},
        {"columns": ["B"], "operation": "normalize"},
    ]

    # Run the flow
    result = await process_data(
        input_file="input.csv", output_file="output.csv", transform_configs=transforms
    )

    print(f"Data processed and saved to: {result}")

    # Show the results
    print("\nInput data:")
    print(pd.read_csv("input.csv"))
    print("\nOutput data:")
    print(pd.read_csv("output.csv"))


if __name__ == "__main__":
    asyncio.run(main())
