# Basic Transformation Example

This example demonstrates how to perform basic data transformations using Pipeflow.

## Setup

```python
from pipeflow import ConfigurablePipe, PipeConfig
from typing import Dict, List
from pydantic import BaseModel

# Define data model
class Record(BaseModel):
    id: int
    value: float
    category: str
```

## Create Configuration

```python
class TransformConfig(PipeConfig):
    multiply_by: float = 1.0
    categories: List[str] = ["A", "B", "C"]
```

## Implement Transformation

```python
class TransformPipe(ConfigurablePipe[Dict, Dict]):
    def __init__(self, config: TransformConfig):
        super().__init__(config)
    
    async def process(self, data: Dict) -> Dict:
        if data["category"] in self.config.categories:
            data["value"] *= self.config.multiply_by
        return data
```

## Use the Pipe

```python
async def main():
    # Create configuration
    config = TransformConfig(
        multiply_by=2.0,
        categories=["A", "B"]
    )
    
    # Create pipe
    pipe = TransformPipe(config)
    
    # Process data
    data = {
        "id": 1,
        "value": 10.0,
        "category": "A"
    }
    
    result = await pipe.process(data)
    print(result)  # {"id": 1, "value": 20.0, "category": "A"}

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Explanation

1. We define a simple data model using Pydantic
2. We create a configuration class for our transformation
3. We implement a pipe that multiplies values by a configurable factor
4. We process data through the pipe asynchronously

## Next Steps

- Try adding more transformations
- Combine multiple pipes into a pipeline
- Add error handling and validation
- Explore streaming capabilities
