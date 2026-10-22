"""Typer CLI entry point for smartcommit."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .ai_generator import generate_commit_candidates, generate_commit_message
from .config import settings
from .git_utils import (
    get_diff_stat,
    get_filtered_staged_diff,
    get_staged_files,
    git_commit,
    is_git_repository,
)
from .utils import copy_to_clipboard

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(
    name="smartcommit",
    help="AI-powered Conventional Commit message generator that runs locally via Ollama.",
    add_completion=False,
)
console = Console(safe_box=True)


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
    detailed: bool = typer.Option(
        False,
        "--detailed",
        "-d",
        help="Generate a detailed multi-line commit message with body and bullet points.",
    ),
    short: bool = typer.Option(
        False,
        "--short",
        "-s",
        help="Force a single-line commit subject.",
    ),
    hint: Optional[str] = typer.Option(
        None,
        "--hint",
        "-H",
        help="Provide developer context or intent (e.g. 'fixes issue #42').",
    ),
    candidates: int = typer.Option(
        1,
        "--candidates",
        "-n",
        help="Number of candidate commit messages to generate (1 to 5).",
    ),
    commit: bool = typer.Option(
        False,
        "--commit",
        "-y",
        "--yes",
        help="Commit staged changes directly with the generated message.",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        "-c",
        help="Copy the generated message to the system clipboard.",
    ),
    emoji: Optional[bool] = typer.Option(
        None,
        "--emoji/--no-emoji",
        help="Prefix commit messages with Conventional Commit gitmoji.",
    ),
    show_stat: bool = typer.Option(
        False,
        "--stat",
        "--diff",
        help="Display staged diff summary stats before generating.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Generate and print the commit message without interactive prompts.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show the smartcommit version and exit.",
    ),
) -> None:
    """Generate a Conventional Commit message from your staged git changes."""
    if not is_git_repository():
        console.print("[red]x Not inside a Git repository.[/red]")
        raise typer.Exit(code=1)

    diff, noise_files = get_filtered_staged_diff(max_chars=settings.max_diff_chars)
    if not diff:
        console.print(
            "[red]x No staged changes found.[/red] Run [bold]git add <files>[/bold] first."
        )
        raise typer.Exit(code=1)

    staged_files = get_staged_files()

    if show_stat:
        diff_stat = get_diff_stat()
        if diff_stat:
            console.print(Panel(diff_stat, title="Staged Changes Stat", border_style="dim"))

    if noise_files:
        console.print(
            f"[dim]i Summarized {len(noise_files)} lockfile/asset diff(s) for context clarity.[/dim]"
        )

    # Configure options
    if emoji is not None:
        settings.use_emoji = emoji

    is_detailed = True if detailed else (False if short else settings.detailed)
    candidates_count = max(1, min(candidates, 5))
    current_hint = hint

    selected_message = _generate_message_or_candidates(
        diff=diff,
        staged_files=staged_files,
        model=model,
        detailed=is_detailed,
        hint=current_hint,
        candidates_count=candidates_count,
    )

    # Fast path for non-interactive flags
    if commit:
        _perform_commit(selected_message)
        if copy:
            _perform_copy(selected_message)
        return

    if dry_run or not sys.stdout.isatty():
        _display_message_panel(selected_message)
        if copy:
            _perform_copy(selected_message)
        console.print(f'\n[dim]Tip: git commit -m "{selected_message}"[/dim]')
        return

    # Interactive workflow
    while True:
        _display_message_panel(selected_message)

        if copy:
            _perform_copy(selected_message)

        action = typer.prompt(
            "\nAction: [c]ommit, [e]dit, [r]egenerate, cop[y], [q]uit",
            default="c",
        ).strip().lower()

        if action in {"c", "commit", "yes", "y" and copy}:
            if action in {"c", "commit", "yes"}:
                _perform_commit(selected_message)
                break
        elif action in {"e", "edit"}:
            selected_message = typer.prompt(
                "Edit commit message",
                default=selected_message,
            ).strip()
            continue
        elif action in {"r", "regenerate", "regen"}:
            new_hint = typer.prompt(
                "Add a hint or context for regeneration (press enter to keep current)",
                default=current_hint or "",
                show_default=bool(current_hint),
            ).strip()
            current_hint = new_hint or current_hint
            console.print("[cyan]Regenerating commit message...[/cyan]")
            selected_message = _generate_message_or_candidates(
                diff=diff,
                staged_files=staged_files,
                model=model,
                detailed=is_detailed,
                hint=current_hint,
                candidates_count=1,
            )
            continue
        elif action in {"y", "copy"}:
            _perform_copy(selected_message)
            continue
        elif action in {"q", "quit", "exit"}:
            console.print("[dim]Aborted without committing.[/dim]")
            raise typer.Exit(code=0)
        else:
            console.print(f"[yellow]Unknown action '{action}'.[/yellow]")


def _generate_message_or_candidates(
    diff: str,
    staged_files: list,
    model: str,
    detailed: bool,
    hint: Optional[str],
    candidates_count: int,
) -> str:
    """Generate message or prompt user to select from candidate options."""
    if candidates_count > 1:
        console.print(f"[cyan]Generating {candidates_count} commit candidates...[/cyan]")
        candidate_list = generate_commit_candidates(
            diff=diff,
            staged_files=staged_files,
            model=model,
            count=candidates_count,
            detailed=detailed,
            hint=hint,
        )
        if len(candidate_list) > 1 and sys.stdout.isatty():
            console.print("\n[bold cyan]Select a Commit Candidate:[/bold cyan]")
            for idx, cand in enumerate(candidate_list, start=1):
                first_line = cand.splitlines()[0]
                console.print(f"  [bold green][{idx}][/bold green] {first_line}")

            choice = typer.prompt(
                f"Choose candidate [1-{len(candidate_list)}]",
                default="1",
            ).strip()
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(candidate_list):
                    return candidate_list[choice_idx]
            except ValueError:
                pass
            return candidate_list[0]
        elif candidate_list:
            return candidate_list[0]

    console.print("[cyan]Generating commit message...[/cyan]")
    return generate_commit_message(
        diff=diff,
        staged_files=staged_files,
        model=model,
        detailed=detailed,
        hint=hint,
    )


def _display_message_panel(message: str) -> None:
    """Render the commit message in a styled Rich panel."""
    console.print(
        Panel(
            f"[bold]{message}[/bold]",
            title="[bold green]Suggested Commit Message[/bold green]",
            border_style="green",
            expand=False,
        )
    )


def _perform_commit(message: str) -> None:
    """Execute git commit and show output."""
    success, output = git_commit(message)
    if success:
        console.print("[bold green]+ Successfully committed staged changes![/bold green]")
        if output:
            first_line = output.splitlines()[0] if output.splitlines() else output
            console.print(f"[dim]{first_line}[/dim]")
    else:
        console.print(f"[bold red]x Commit failed:[/bold red] {output}")
        raise typer.Exit(code=1)


def _perform_copy(message: str) -> None:
    """Copy message to clipboard with feedback."""
    if copy_to_clipboard(message):
        console.print("[dim]+ Copied to clipboard[/dim]")
    else:
        console.print(
            "[dim]! Could not access system clipboard (Linux may require xclip).[/dim]"
        )


if __name__ == "__main__":
    app()