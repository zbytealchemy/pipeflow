"""Command-line interface for Pipeflow."""
import asyncio
import json
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

import click
from rich.console import Console
from rich.table import Table

from pipeflow.core import BasePipe, ConfigurablePipe, PipeConfig
from pipeflow.streams import Stream, StreamConfig

T = TypeVar("T")
U = TypeVar("U")
InputType = Union[Dict[str, Any], List[Dict[str, Any]]]
OutputType = Union[Dict[str, Any], List[Dict[str, Any]]]

console = Console()


@runtime_checkable
class PipeProtocol(Protocol):
    """Protocol for pipe objects to help with type checking."""

    async def __call__(self, data: InputType) -> OutputType:
        """Process data through the pipe.

        Args:
            data: Input data to process

        Returns:
            Processed output data
        """

    async def process(self, data: InputType) -> OutputType:
        """Process data through the pipe.

        Args:
            data: Input data to process

        Returns:
            Processed output data
        """


@click.group()
def cli() -> None:
    """Pipeflow CLI - A type-safe data processing pipeline framework."""


@overload
def _create_pipe(
    pipe_class: Type[ConfigurablePipe[InputType, OutputType, Any]],
    pipe_config: PipeConfig,
) -> ConfigurablePipe[InputType, OutputType, Any]:
    """Create a configurable pipe instance.

    Args:
        pipe_class: Pipe class to create instance of
        pipe_config: Configuration for the pipe

    Returns:
        Configured pipe instance
    """


@overload
def _create_pipe(
    pipe_class: Type[BasePipe[InputType, OutputType]],
    pipe_config: Optional[PipeConfig] = None,
) -> BasePipe[InputType, OutputType]:
    ...


def _create_pipe(
    pipe_class: Union[
        Type[ConfigurablePipe[InputType, OutputType, Any]],
        Type[BasePipe[InputType, OutputType]],
    ],
    pipe_config: Optional[PipeConfig] = None,
) -> BasePipe[InputType, OutputType]:
    """Create a pipe instance with proper typing."""
    if issubclass(pipe_class, ConfigurablePipe):
        if pipe_config is None:
            raise ValueError("Config is required for ConfigurablePipe")
        return cast(BasePipe[InputType, OutputType], pipe_class(pipe_config))
    return pipe_class()


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--input-file",
    "-i",
    type=click.Path(exists=True),
    required=True,
    help="Input file to process",
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(),
    required=True,
    help="Output file to write results to",
)
@click.option(
    "--batch-size", "-b", type=int, default=None, help="Batch size for processing"
)
@click.option(
    "--window-size", "-w", type=float, default=None, help="Window size in seconds"
)
def run(
    config_file: str,
    input_file: str,
    output_file: str,
    batch_size: Optional[int],
    window_size: Optional[float],
) -> None:
    """Run a pipeline from a configuration file."""
    try:
        # Load configuration
        config = json.loads(Path(config_file).read_text(encoding="utf-8"))
        pipe_config = PipeConfig(**config.get("pipe_config", {}))

        # Create stream config with defaults if not provided
        stream_config_dict = config.get("stream_config", {})
        if batch_size is not None:
            stream_config_dict["batch_size"] = batch_size
        if window_size is not None:
            stream_config_dict["window_size"] = window_size
        stream_config = StreamConfig(**stream_config_dict)

        # Import and create pipe
        pipe_class = _import_class(config["pipe_class"])
        pipe = _create_pipe(pipe_class, pipe_config)

        # Process data
        asyncio.run(_process_data(pipe, input_file, output_file, stream_config))

        console.print("[green]Pipeline completed successfully![/green]")

    except Exception as e:
        console.print(f"[red]Error running pipeline: {str(e)}[/red]")
        raise click.Abort()


@cli.command()
def list_pipes() -> None:
    """List available pipes in the current project."""
    try:
        pipes = _discover_pipes()

        table = Table(title="Available Pipes")
        table.add_column("Name", style="cyan")
        table.add_column("Module", style="green")
        table.add_column("Description")

        for pipe_info in pipes:
            table.add_row(
                pipe_info["name"], pipe_info["module"], pipe_info.get("description", "")
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing pipes: {str(e)}[/red]")
        raise click.Abort()


@cli.command()
@click.argument("pipe_name")
def info(pipe_name: str) -> None:
    """Show detailed information about a pipe.

    Args:
        pipe_name: Name of the pipe to show information for
    """
    try:
        pipe_class = _find_pipe(pipe_name)
        if pipe_class is None:
            console.print(f"[red]Pipe '{pipe_name}' not found[/red]")
            raise click.Abort()

        pipe_details = _get_pipe_info(pipe_class)
        table = Table(title=f"Pipe: {pipe_name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        for key, value in pipe_details.items():
            table.add_row(key, str(value))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error getting pipe info: {str(e)}[/red]")
        raise click.Abort()


async def _process_data(
    pipe: BasePipe[InputType, OutputType],
    input_file: str,
    output_file: str,
    config: StreamConfig,
) -> None:
    """Process data through a pipe."""

    async def data_source() -> AsyncIterator[Dict[str, Any]]:
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

    stream = Stream(data_source(), config=config)

    with open(output_file, "w", encoding="utf-8") as f:
        async for result in stream.process(pipe):
            f.write(json.dumps(result) + "\n")


def _import_class(class_path: str) -> Type[BasePipe[InputType, OutputType]]:
    """Import a class from a string path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return cast(Type[BasePipe[InputType, OutputType]], getattr(module, class_name))


def _discover_pipes() -> list[Dict[str, Any]]:
    """Discover available pipes in the project."""
    # This is a placeholder. In a real implementation,
    # we would scan the project directory for pipe classes.
    return []


def _find_pipe(
    pipe_name: str,
) -> Optional[Type[BasePipe[InputType, OutputType]]]:
    """Find a pipe class by name.

    Args:
        pipe_name: Name of the pipe to find

    Returns:
        The pipe class if found, None otherwise
    """
    for pipe_info in _discover_pipes():
        if pipe_info["name"] == pipe_name:
            return _import_class(pipe_info["module"])
    return None


def _get_pipe_info(pipe_class: Type[BasePipe[InputType, OutputType]]) -> Dict[str, Any]:
    """Get information about a pipe class."""
    return {
        "name": pipe_class.__name__,
        "module": pipe_class.__module__,
        "description": pipe_class.__doc__,
        "config_fields": {},  # Would be populated from class inspection
    }


if __name__ == "__main__":
    cli()
