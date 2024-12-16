"""Example of basic data transformation using Pipeflow."""
import asyncio
from typing import Dict, List

from pydantic import ConfigDict

from pipeflow.core import ConfigurablePipe, PipeConfig


class FilterConfig(PipeConfig):
    """Configuration for filtering records."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    field: str
    value: str


class FilterPipe(ConfigurablePipe[List[Dict], List[Dict]]):
    """Filter records based on a field value."""

    def __init__(self, config: FilterConfig):
        super().__init__(config)

    async def process(self, data: List[Dict]) -> List[Dict]:
        """Filter records where field matches value."""
        return [
            record
            for record in data
            if record.get(self.config.field) == self.config.value
        ]


class TransformConfig(PipeConfig):
    """Configuration for data transformation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    columns: List[str]
    operation: str


class TransformPipe(ConfigurablePipe[List[Dict], List[Dict]]):
    """Transform records by converting specified fields to uppercase."""

    def __init__(self, config: TransformConfig):
        super().__init__(config)

    async def process(self, data: List[Dict]) -> List[Dict]:
        """Convert specified fields to uppercase."""
        result = []
        for record in data:
            transformed = record.copy()
            for field in self.config.columns:
                if field in transformed:
                    transformed[field] = str(transformed[field]).upper()
            result.append(transformed)
        return result


async def main():
    # Sample data
    data = [
        {"name": "Alice", "status": "active", "role": "admin"},
        {"name": "Bob", "status": "inactive", "role": "user"},
        {"name": "Charlie", "status": "active", "role": "user"},
    ]

    # Create pipeline
    filter_pipe = FilterPipe(FilterConfig(field="status", value="active"))
    transform_pipe = TransformPipe(
        TransformConfig(columns=["role"], operation="uppercase")
    )

    # Process data through pipes
    filtered_data = await filter_pipe(data)
    final_data = await transform_pipe(filtered_data)

    print("Original data:")
    print(data)
    print("\nFiltered and transformed data:")
    print(final_data)


if __name__ == "__main__":
    asyncio.run(main())
