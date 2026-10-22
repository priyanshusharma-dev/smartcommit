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
    """Return the list of staged files with their status letters."""
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


_NOISE_FILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    "pipfile.lock",
    "composer.lock",
    "go.sum",
    "gemfile.lock",
    "flake.lock",
}

_NOISE_EXTENSIONS = (
    ".min.js",
    ".min.css",
    ".map",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".wasm",
)


def get_diff_stat() -> str:
    """Return the stat summary of currently staged changes, or '' if none/on error."""
    try:
        return _run_git(["diff", "--cached", "--stat"]).strip()
    except GitError:
        return ""


def get_filtered_staged_diff(max_chars: int = 8000) -> tuple[str, list[str]]:
    """Return a clean diff optimized for AI context, filtering out large lockfile noise.

    Returns:
        tuple[str, list[str]]: The processed diff string and a list of skipped noise file paths.
    """
    files = get_staged_files()
    if not files:
        return "", []

    noise_files: list[str] = []
    informative_files: list[str] = []

    for f in files:
        filename = f.path.split("/")[-1].lower()
        if filename in _NOISE_FILE_NAMES or filename.endswith(_NOISE_EXTENSIONS):
            noise_files.append(f.path)
        else:
            informative_files.append(f.path)

    # If all files are noise files, don't exclude them completely
    files_to_diff = informative_files if informative_files else [f.path for f in files]

    try:
        diff_text = _run_git(["diff", "--cached", "--", *files_to_diff]).strip()
    except GitError:
        diff_text = get_staged_diff()

    if len(diff_text) > max_chars:
        diff_text = diff_text[:max_chars].rstrip() + "\n\n[...diff truncated for context length...]"

    return diff_text, noise_files


def git_commit(message: str) -> tuple[bool, str]:
    """Execute git commit with the given message.

    Returns:
        tuple[bool, str]: (Success status, stdout or error message)
    """
    try:
        output = _run_git(["commit", "-m", message])
        return True, output.strip()
    except GitError as exc:
        return False, str(exc)