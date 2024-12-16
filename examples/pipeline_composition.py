"""Example of composing pipes into a pipeline using pipeflow."""
import asyncio
from dataclasses import dataclass
from typing import List, Optional

from pydantic import ConfigDict

from pipeflow import BasePipe, ConfigurablePipe, PipeConfig


@dataclass
class Order:
    """Sample order data class."""

    id: str
    customer: str
    amount: float
    status: str


class ValidationPipe(BasePipe[Order, Optional[Order]]):
    """Validate order data."""

    async def process(self, data: Order) -> Optional[Order]:
        """Validate order amount and status."""
        if data.amount <= 0:
            return None
        if data.status not in ["pending", "completed"]:
            return None
        return data


class EnrichConfig(PipeConfig):
    """Configuration for order enrichment."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    premium_threshold: float


class EnrichmentPipe(ConfigurablePipe[Order, Order]):
    """Enrich order with customer tier."""

    def __init__(self, config: EnrichConfig):
        super().__init__(config)

    async def process(self, data: Order) -> Order:
        """Add premium flag based on order amount."""
        if data.amount >= self.config.premium_threshold:
            data.customer = f"{data.customer} (Premium)"
        return data


class Pipeline:
    """Simple pipeline to chain pipes together."""

    def __init__(self, pipes: List[BasePipe]):
        self.pipes = pipes

    async def process(self, data: Order) -> Optional[Order]:
        """Process data through all pipes in sequence."""
        result = data
        for pipe in self.pipes:
            if result is None:
                break
            result = await pipe(result)
        return result


async def main():
    # Create sample orders
    orders = [
        Order("1", "Alice", 150.0, "pending"),
        Order("2", "Bob", -50.0, "pending"),  # Invalid amount
        Order("3", "Charlie", 500.0, "completed"),
        Order("4", "David", 50.0, "cancelled"),  # Invalid status
    ]

    # Create pipeline
    pipeline = Pipeline(
        [ValidationPipe(), EnrichmentPipe(EnrichConfig(premium_threshold=200.0))]
    )

    # Process orders
    print("Processing orders:")
    for order in orders:
        print(f"\nInput order: {order}")
        result = await pipeline.process(order)
        print(f"Output: {result}")


if __name__ == "__main__":
    asyncio.run(main())
