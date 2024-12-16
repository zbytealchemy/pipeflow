"""Command-line interface for Pipeflow."""
import asyncio
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

import click
from rich.console import Console
from rich.table import Table

from pipeflow.core import BasePipe, PipeConfig
from pipeflow.streams import Stream, StreamConfig

console = Console()


@click.group()
def cli() -> None:
    """Pipeflow CLI - A type-safe data processing pipeline framework."""
    pass


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
    window_size: float,
) -> None:
    """Run a pipeline from a configuration file."""
    try:
        config = json.loads(Path(config_file).read_text())
        pipe_config = PipeConfig(**config.get("pipe_config", {}))

        batch_size = 1 if not batch_size else batch_size
        stream_config = StreamConfig(
            batch_size=batch_size,
            window_size=timedelta(window_size),
            **config.get("stream_config", {}),
        )

        # Import and create pipe
        pipe_class = _import_class(config["pipe_class"])
        pipe = pipe_class(pipe_config)

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
    """Show detailed information about a pipe."""
    try:
        pipe_class = _find_pipe(pipe_name)
        if not pipe_class:
            raise click.BadParameter(f"Pipe '{pipe_name}' not found")

        info = _get_pipe_info(pipe_class)

        console.print(f"\n[cyan]Pipe: {info['name']}[/cyan]")
        console.print(f"[green]Module:[/green] {info['module']}")
        console.print(f"\n{info.get('description', '')}")

        if info.get("config_fields"):
            console.print("\n[yellow]Configuration Fields:[/yellow]")
            for field, details in info["config_fields"].items():
                console.print(f"  {field}: {details['type']}")
                if details.get("description"):
                    console.print(f"    {details['description']}")

    except Exception as e:
        console.print(f"[red]Error getting pipe info: {str(e)}[/red]")
        raise click.Abort()


async def _process_data(
    pipe: BasePipe, input_file: str, output_file: str, config: StreamConfig
) -> None:
    """Process data through a pipe."""

    async def data_source() -> AsyncGenerator[Dict[str, Any], None]:
        with open(input_file) as f:
            for line in f:
                yield json.loads(line)

    stream = Stream(data_source(), config=config)

    with open(output_file, "w") as f:
        async for result in stream.process(pipe):
            f.write(json.dumps(result) + "\n")


def _import_class(class_path: str) -> type:
    """Import a class from a string path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return type(getattr(module, class_name))


def _discover_pipes() -> list[Dict[str, Any]]:
    """Discover available pipes in the project."""
    # This is a placeholder. In a real implementation,
    # we would scan the project directory for pipe classes.
    return []


def _find_pipe(name: str) -> Optional[type]:
    """Find a pipe class by name."""
    # This is a placeholder. In a real implementation,
    # we would look up the pipe class by name.
    return None


def _get_pipe_info(pipe_class: type) -> Dict[str, Any]:
    """Get information about a pipe class."""
    return {
        "name": pipe_class.__name__,
        "module": pipe_class.__module__,
        "description": pipe_class.__doc__,
        "config_fields": {},  # Would be populated from class inspection
    }


if __name__ == "__main__":
    cli()
