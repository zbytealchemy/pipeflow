"""Example of composing pipes using lambda functions and function composition."""
import asyncio
from typing import Any, Callable, TypeVar

from pipeflow import BasePipe

T = TypeVar("T")
U = TypeVar("U")


class LambdaPipe(BasePipe[T, U]):
    """Create a pipe from a lambda or function."""

    def __init__(self, func: Callable[[T], U], name: str = None):
        """Initialize the pipe with a function.

        Args:
            func: Function to execute in the pipe
            name: Optional name for the pipe
        """
        super().__init__(name=name or func.__name__)
        self.func = func

    async def process(self, data: T) -> U:
        """Execute the function on the input data."""
        return self.func(data)


def compose(*pipes: BasePipe) -> BasePipe:
    """Compose multiple pipes into a single pipe.

    Args:
        *pipes: Pipes to compose

    Returns:
        A new pipe that runs all pipes in sequence
    """

    class ComposedPipe(BasePipe):
        async def process(self, data: Any) -> Any:
            result = data
            for pipe in pipes:
                result = await pipe(result)
            return result

    return ComposedPipe(name=" -> ".join(p.name for p in pipes))


async def main():
    # Create pipes using lambda functions
    double = LambdaPipe(lambda x: x * 2, name="double")
    add_ten = LambdaPipe(lambda x: x + 10, name="add_ten")
    to_string = LambdaPipe(lambda x: f"Result: {x}", name="to_string")

    # Create a pipeline using function composition
    pipeline = compose(double, add_ten, to_string)

    # Process some data
    result = await pipeline(5)
    print(f"Pipeline: {pipeline.name}")
    print("Input: 5")
    print(f"Output: {result}")

    # Example with list processing
    numbers = [1, 2, 3, 4, 5]
    list_pipeline = compose(
        LambdaPipe(lambda nums: [x for x in nums if x % 2 == 0], name="even_only"),
        LambdaPipe(lambda nums: [x * x for x in nums], name="square"),
        LambdaPipe(lambda nums: sum(nums), name="sum"),
    )

    result = await list_pipeline(numbers)
    print(f"\nList Pipeline: {list_pipeline.name}")
    print(f"Input: {numbers}")
    print(f"Output: {result}")

    # Example with dictionary transformation
    data = {"name": "alice", "age": 30, "city": "new york"}
    dict_pipeline = compose(
        LambdaPipe(
            lambda d: {k: v.upper() if isinstance(v, str) else v for k, v in d.items()},
            name="uppercase_strings",
        ),
        LambdaPipe(
            lambda d: {
                k: f"{v}!" if isinstance(v, str) else v + 1 for k, v in d.items()
            },
            name="transform_values",
        ),
    )

    result = await dict_pipeline(data)
    print(f"\nDict Pipeline: {dict_pipeline.name}")
    print(f"Input: {data}")
    print(f"Output: {result}")


if __name__ == "__main__":
    asyncio.run(main())
