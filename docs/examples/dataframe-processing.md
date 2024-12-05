# DataFrame Processing Example

This example shows how to process Pandas DataFrames using Pipeflow.

## Setup

```python
from pipeflow import ConfigurablePipe, PipeConfig
import pandas as pd
from typing import List

# Install pandas if not already installed
# pip install pandas
```

## Configuration

```python
class DataFrameConfig(PipeConfig):
    columns: List[str]
    operation: str = "mean"  # or "sum", "min", "max"
    group_by: str = None
```

## DataFrame Processing Pipe

```python
class DataFramePipe(ConfigurablePipe[pd.DataFrame, pd.DataFrame]):
    def __init__(self, config: DataFrameConfig):
        super().__init__(config)
    
    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        # Select columns
        df = df[self.config.columns]
        
        # Apply grouping if specified
        if self.config.group_by:
            grouped = df.groupby(self.config.group_by)
            
            # Apply operation
            if self.config.operation == "mean":
                return grouped.mean().reset_index()
            elif self.config.operation == "sum":
                return grouped.sum().reset_index()
            elif self.config.operation == "min":
                return grouped.min().reset_index()
            elif self.config.operation == "max":
                return grouped.max().reset_index()
        
        return df
```

## Usage Example

```python
async def main():
    # Create sample data
    data = {
        "category": ["A", "A", "B", "B", "C"],
        "value1": [1, 2, 3, 4, 5],
        "value2": [10, 20, 30, 40, 50]
    }
    df = pd.DataFrame(data)
    
    # Configure pipe
    config = DataFrameConfig(
        columns=["category", "value1", "value2"],
        operation="mean",
        group_by="category"
    )
    
    # Create and use pipe
    pipe = DataFramePipe(config)
    result = await pipe.process(df)
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Output

```
  category  value1  value2
0        A     1.5    15.0
1        B     3.5    35.0
2        C     5.0    50.0
```

## Advanced Usage

### Pipeline with Multiple Operations

```python
from pipeflow import Pipeline

# Create pipes
mean_pipe = DataFramePipe(DataFrameConfig(
    columns=["category", "value1"],
    operation="mean",
    group_by="category"
))

sum_pipe = DataFramePipe(DataFrameConfig(
    columns=["category", "value2"],
    operation="sum",
    group_by="category"
))

# Create pipeline
pipeline = Pipeline()
pipeline.add_pipe(mean_pipe)
pipeline.add_pipe(sum_pipe)

# Process data
result = await pipeline.process(df)
```

## Best Practices

1. Handle large DataFrames efficiently
2. Use appropriate data types
3. Consider memory usage
4. Add data validation
5. Implement error handling
6. Monitor performance
