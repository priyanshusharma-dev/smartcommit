"""Typer CLI entry point."""

import typer
from rich.console import Console

from . import __version__
from .ai_generator import generate_commit_message
from .config import settings
from .git_utils import get_staged_diff, get_staged_files, is_git_repository
from .utils import copy_to_clipboard

app = typer.Typer(
    help="AI-powered Conventional Commit message generator that runs locally via Ollama.",
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"smartcommit {__version__}")
        raise typer.Exit()


@app.command()
def main(
    model: str = typer.Option(
        settings.default_model,
        "--model",
        "-m",
        help="Ollama model to use for generation.",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        "-c",
        help="Copy the generated message to the clipboard.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the smartcommit version and exit.",
    ),
) -> None:
    """Generate a Conventional Commit message from your staged git changes."""
    if not is_git_repository():
        console.print("[red]✗ Not inside a Git repository.[/red]")
        raise typer.Exit(code=1)

    diff = get_staged_diff()
    if not diff:
        console.print(
            "[red]✗ No staged changes found.[/red] Run [bold]git add <files>[/bold] first."
        )
        raise typer.Exit(code=1)

    staged_files = get_staged_files()

    console.print("[cyan]Generating commit message...[/cyan]")
    message = generate_commit_message(diff, staged_files, model)

    console.print("\n[bold green]Suggested Commit Message[/bold green]")
    console.print(f"[bold]{message}[/bold]")

    if copy:
        if copy_to_clipboard(message):
            console.print("[dim]✓ Copied to clipboard[/dim]")
        else:
            console.print(
                "[dim]⚠ Couldn't access the clipboard on this platform "
                "(Linux needs xclip installed).[/dim]"
            )

    console.print(f'\n[dim]Tip: git commit -m "{message}"[/dim]')


if __name__ == "__main__":
    app()