"""AI-backed commit message generation, with a genuine rule-based fallback.

Design:
    1. Try the local Ollama model with the real system prompt (no silent
       truncation without warning, real timeout/error handling).
    2. If that fails for ANY reason (Ollama missing, model missing, timeout,
       empty response), fall back to a heuristic generator that inspects
       which files actually changed and infers a sensible Conventional
       Commit type/scope -- not a hardcoded string.
"""

import subprocess

from rich.console import Console

from .config import settings
from .git_utils import StagedFile
from .utils import load_prompt

console = Console()

_EMOJI_BY_TYPE = {
    "feat": "✨", "fix": "🐛", "docs": "📝", "style": "💄",
    "refactor": "♻️", "perf": "⚡", "test": "✅", "chore": "🔧",
    "ci": "👷", "build": "📦",
}


class AIGenerationError(Exception):
    """Raised internally when the AI backend can't produce a usable message."""


def generate_commit_message(
    diff: str,
    staged_files: list[StagedFile] | None = None,
    model: str | None = None,
) -> str:
    """Generate a Conventional Commit message for the given staged diff.

    Tries the AI backend first, then transparently falls back to a
    rule-based message derived from the changed files. The caller always
    gets a usable message back -- this function never raises.
    """
    model = model or settings.default_model
    staged_files = staged_files or []

    try:
        message = _generate_with_ai(diff, model)
    except FileNotFoundError:
        console.print(
            "[yellow]⚠ Ollama isn't installed or isn't on PATH.[/yellow] "
            "[dim]Install it from https://ollama.ai to enable AI-generated messages.[/dim]"
        )
        message = None
    except subprocess.TimeoutExpired:
        console.print(
            f"[yellow]⚠ AI generation timed out after {settings.ai_timeout_seconds}s.[/yellow] "
            "[dim]Try a smaller diff, a lighter model, or raise SMARTCOMMIT_AI_TIMEOUT_SECONDS.[/dim]"
        )
        message = None
    except AIGenerationError as exc:
        console.print(f"[yellow]⚠ AI generation failed:[/yellow] {exc}")
        message = None
    except Exception as exc:  # last-resort safety net; never crash the CLI
        console.print(f"[yellow]⚠ Unexpected error calling the AI backend:[/yellow] {exc}")
        message = None

    if message is None:
        console.print("[cyan]↪ Using rule-based fallback (analyzing changed files)...[/cyan]")
        message = generate_fallback_message(staged_files)

    return _apply_emoji(message) if settings.use_emoji else message


def _generate_with_ai(diff: str, model: str) -> str:
    """Call Ollama with the real system prompt. Raises on any failure."""
    system_prompt = load_prompt()

    diff_for_prompt = diff[: settings.max_diff_chars]
    was_truncated = len(diff) > settings.max_diff_chars

    prompt = f"{system_prompt}\n\nGit diff to summarize:\n```\n{diff_for_prompt}\n```\n"
    if was_truncated:
        prompt += (
            "\n(Note: the diff above was truncated for length. Base the "
            "message on what's visible.)\n"
        )

    console.print(f"[dim]Calling {model} via Ollama...[/dim]")
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=settings.ai_timeout_seconds,
    )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise AIGenerationError(stderr or f"Ollama exited with code {result.returncode}.")

    message = _clean_message(result.stdout)
    if not message or len(message) < 5:
        raise AIGenerationError("Ollama returned an empty response.")

    console.print("[green]✓ Generated with AI[/green]")
    return message


def _clean_message(raw: str) -> str:
    """Strip code fences/quotes some models wrap responses in; keep first real line."""
    text = raw.strip().strip("`").strip('"').strip("'").strip()
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[: settings.max_length] if len(line) > settings.max_length else line
    return text


# --- Rule-based fallback -----------------------------------------------

_TYPE_BY_PATH_KEYWORD = {
    "test": "test", "spec": "test",
    ".github/workflows": "ci", "ci": "ci",
    "dockerfile": "build", "requirements": "build",
    "pyproject": "build", "setup.py": "build", "setup.cfg": "build",
    "readme": "docs", "changelog": "docs", "license": "docs", "docs/": "docs",
}

_TYPE_BY_EXTENSION = {
    ".md": "docs", ".rst": "docs", ".txt": "docs",
    ".yml": "ci", ".yaml": "ci",
}


def _infer_type(files: list[StagedFile]) -> str:
    """Guess a Conventional Commit type by inspecting which files changed."""
    paths = [f.path.lower() for f in files]

    for path in paths:
        for keyword, commit_type in _TYPE_BY_PATH_KEYWORD.items():
            if keyword in path:
                return commit_type

    for path in paths:
        for ext, commit_type in _TYPE_BY_EXTENSION.items():
            if path.endswith(ext):
                return commit_type

    statuses = {f.status for f in files}
    if statuses == {"A"}:
        return "feat"      # only new files -> likely a new feature
    if statuses == {"D"}:
        return "chore"     # only deletions -> cleanup
    if statuses <= {"M"}:
        return "fix"       # only modifications -> treat conservatively as a fix
    return "chore"          # mixed additions/deletions/renames


def _infer_scope(files: list[StagedFile]) -> str | None:
    """Guess a scope from a shared top-level directory, if there is one."""
    dirs = {f.path.split("/")[0] for f in files if "/" in f.path}
    if len(dirs) == 1:
        return next(iter(dirs))
    return None


def generate_fallback_message(files: list[StagedFile]) -> str:
    """Build a Conventional Commit message heuristically from changed files.

    This is a genuine fallback: it inspects real filenames/statuses instead
    of returning a fixed string, so the message still reflects what changed.
    """
    if not files:
        return "chore: update project files"

    commit_type = _infer_type(files)
    scope = _infer_scope(files)

    if len(files) == 1:
        subject = f"update {files[0].path}"
    elif scope:
        subject = f"update {scope} module ({len(files)} files)"
    else:
        subject = f"update {len(files)} files across the project"

    header = f"{commit_type}({scope})" if scope else commit_type
    message = f"{header}: {subject}"
    return message[: settings.max_length]


def _apply_emoji(message: str) -> str:
    commit_type = message.split("(")[0].split(":")[0].strip()
    emoji = _EMOJI_BY_TYPE.get(commit_type)
    return f"{emoji} {message}" if emoji else message