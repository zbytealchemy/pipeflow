"""Example of processing pandas DataFrames using Pipeflow."""
import asyncio
from typing import Any, List

import pandas as pd
from pydantic import ConfigDict

from pipeflow.core.dataframe import DataFramePipe, DataFramePipeConfig


class FilterConfig(DataFramePipeConfig):
    """Configuration for filter pipe."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    column: str
    value: Any


class FilterPipe(DataFramePipe):
    """Filter DataFrame rows based on a minimum value."""

    def __init__(self, config: FilterConfig):
        super().__init__(config)

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter rows where column value is >= min_value."""
        return df[df[self.config.column] >= self.config.value]


class AggregateConfig(DataFramePipeConfig):
    """Configuration for aggregation pipe."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    group_by: List[str]
    agg_column: str
    agg_func: str


class AggregatePipe(DataFramePipe):
    """Aggregate DataFrame by group and calculate mean."""

    def __init__(self, config: AggregateConfig):
        super().__init__(config)

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group by specified columns and calculate mean of agg_column."""
        return (
            df.groupby(self.config.group_by)[self.config.agg_column]
            .agg(self.config.agg_func)
            .reset_index()
        )


async def main():
    # Sample data
    data = pd.DataFrame(
        {
            "category": ["A", "A", "B", "B", "C"],
            "region": ["East", "West", "East", "West", "East"],
            "sales": [100, 150, 200, 300, 250],
            "units": [10, 15, 20, 30, 25],
        }
    )

    # Create pipeline
    filter_pipe = FilterPipe(
        FilterConfig(column="sales", value=150, validate_types=True)
    )

    aggregate_pipe = AggregatePipe(
        AggregateConfig(
            group_by=["category"],
            agg_column="units",
            agg_func="mean",
            validate_types=True,
        )
    )

    # Process data through pipes
    filtered_data = await filter_pipe(data)
    final_data = await aggregate_pipe(filtered_data)

    print("Original data:")
    print(data)
    print("\nFiltered data (sales >= 150):")
    print(filtered_data)
    print("\nAggregated data (mean units by category):")
    print(final_data)


if __name__ == "__main__":
    asyncio.run(main())
