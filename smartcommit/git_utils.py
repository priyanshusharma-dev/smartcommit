"""Git interaction layer: reads staged changes without shelling out unsafely."""

import subprocess
from dataclasses import dataclass


class GitError(Exception):
    """Raised when a git command fails or git/the repo is unavailable."""


@dataclass
class StagedFile:
    """A single staged file and its git status letter (A/M/D/R/etc.)."""

    status: str
    path: str


def _run_git(args: list[str]) -> str:
    """Run a git command safely (list-form args, no shell=True) and return stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout
    except FileNotFoundError as exc:
        raise GitError("Git is not installed or not available on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git error"
        raise GitError(stderr) from exc


def is_git_repository() -> bool:
    """Return True if the current directory is inside a git working tree."""
    try:
        _run_git(["rev-parse", "--is-inside-work-tree"])
        return True
    except GitError:
        return False


def get_staged_diff() -> str:
    """Return the diff of currently staged changes, or '' if none/on error."""
    try:
        return _run_git(["diff", "--cached"]).strip()
    except GitError:
        return ""


def get_staged_files() -> list[StagedFile]:
    """Return the list of staged files with their status letters.

    Used by the rule-based fallback to infer a sensible commit type/scope
    when the AI backend is unavailable.
    """
    try:
        output = _run_git(["diff", "--cached", "--name-status"]).strip()
    except GitError:
        return []

    files: list[StagedFile] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0]  # first char handles rename codes like "R100"
        path = parts[-1]
        files.append(StagedFile(status=status, path=path))
    return files