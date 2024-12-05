# Basic Pipeline Example

This example demonstrates how to create a basic data processing pipeline using Pipeflow.

## Setup

First, install Pipeflow:

```bash
pip install pipeflow
```

## Creating the Pipeline

Here's a simple pipeline that processes user data:

```python
from pipeflow import ConfigurablePipe, PipeConfig, Pipeline
from typing import Dict, List
from pydantic import BaseModel

# Define data models
class User(BaseModel):
    name: str
    age: int
    email: str

# Define pipe configurations
class FilterConfig(PipeConfig):
    min_age: int

class EnrichConfig(PipeConfig):
    domain: str

# Create pipes
class AgeFilterPipe(ConfigurablePipe[List[User], List[User]]):
    def __init__(self, config: FilterConfig):
        super().__init__(config)
    
    async def process(self, users: List[User]) -> List[User]:
        return [user for user in users if user.age >= self.config.min_age]

class EmailEnrichPipe(ConfigurablePipe[List[User], List[Dict]]):
    def __init__(self, config: EnrichConfig):
        super().__init__(config)
    
    async def process(self, users: List[User]) -> List[Dict]:
        return [{
            "name": user.name,
            "age": user.age,
            "email": user.email,
            "domain": self.config.domain,
            "full_email": f"{user.email}@{self.config.domain}"
        } for user in users]

# Create and run the pipeline
async def main():
    # Create sample data
    users = [
        User(name="Alice", age=25, email="alice"),
        User(name="Bob", age=17, email="bob"),
        User(name="Charlie", age=30, email="charlie")
    ]
    
    # Configure pipes
    age_filter = AgeFilterPipe(FilterConfig(min_age=18))
    email_enricher = EmailEnrichPipe(EnrichConfig(domain="example.com"))
    
    # Create pipeline
    pipeline = Pipeline()
    pipeline.add_pipe(age_filter)
    pipeline.add_pipe(email_enricher)
    
    # Process data
    result = await pipeline.process(users)
    print(result)

# Run the pipeline
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Output

The pipeline will output something like:

```python
[
    {
        "name": "Alice",
        "age": 25,
        "email": "alice",
        "domain": "example.com",
        "full_email": "alice@example.com"
    },
    {
        "name": "Charlie",
        "age": 30,
        "email": "charlie",
        "domain": "example.com",
        "full_email": "charlie@example.com"
    }
]
```

## Explanation

1. We define two pipes:
   - `AgeFilterPipe`: Filters out users under 18
   - `EmailEnrichPipe`: Adds domain information to emails

2. Each pipe has its own configuration class
3. The pipeline processes the data sequentially through both pipes
4. Type safety is enforced throughout the pipeline
5. All processing is done asynchronously
