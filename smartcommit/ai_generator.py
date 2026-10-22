"""AI-backed commit message generation with dual Ollama backends (HTTP + CLI)
and an intelligent rule-based fallback engine.

Design:
    1. Try local Ollama HTTP API directly (fast, no shell overhead, deterministic).
    2. Fall back to Ollama CLI subprocess (with --nowordwrap and ANSI stripping).
    3. If Ollama is unavailable or times out, seamlessly fall back to an
       advanced heuristic engine that inspects staged files and diff contents.
    4. Supports single-line, multi-line detailed (subject + body), candidate
       selection, developer hints, and conventional gitmoji styling.
"""

import json
import re
import subprocess
import urllib.error
import urllib.request
from typing import Optional

from rich.console import Console

from .config import settings
from .git_utils import StagedFile
from .utils import load_prompt, strip_ansi

console = Console()

_EMOJI_BY_TYPE = {
    "feat": "✨",
    "fix": "🐛",
    "docs": "📝",
    "style": "💄",
    "refactor": "♻️",
    "perf": "⚡",
    "test": "✅",
    "chore": "🔧",
    "ci": "👷",
    "build": "📦",
}


class AIGenerationError(Exception):
    """Raised internally when the AI backend cannot produce a usable message."""


def generate_commit_message(
    diff: str,
    staged_files: Optional[list[StagedFile]] = None,
    model: Optional[str] = None,
    detailed: Optional[bool] = None,
    hint: Optional[str] = None,
) -> str:
    """Generate a Conventional Commit message for the given staged diff.

    Tries the AI backend first, then transparently falls back to a
    rule-based message derived from the changed files and diff.
    """
    model = model or settings.default_model
    staged_files = staged_files or []
    is_detailed = settings.detailed if detailed is None else detailed

    try:
        message = _generate_with_ai(
            diff=diff,
            staged_files=staged_files,
            model=model,
            detailed=is_detailed,
            hint=hint,
            count=1,
        )
    except FileNotFoundError:
        console.print(
            "[yellow]! Ollama is not installed or not available on PATH.[/yellow] "
            "[dim]Install it from https://ollama.ai for AI-generated messages.[/dim]"
        )
        message = None
    except subprocess.TimeoutExpired:
        console.print(
            f"[yellow]! AI generation timed out after {settings.ai_timeout_seconds}s.[/yellow] "
            "[dim]Try a smaller diff, a lighter model, or raise SMARTCOMMIT_AI_TIMEOUT_SECONDS.[/dim]"
        )
        message = None
    except AIGenerationError as exc:
        console.print(f"[yellow]! AI generation failed:[/yellow] {exc}")
        message = None
    except Exception as exc:  # Safety net: never crash the CLI
        console.print(f"[yellow]! Unexpected error calling AI backend:[/yellow] {exc}")
        message = None

    if not message:
        console.print("[cyan]-> Using rule-based fallback (analyzing changed files & diff)...[/cyan]")
        message = generate_fallback_message(staged_files, diff=diff, detailed=is_detailed)

    return _apply_emoji(message) if settings.use_emoji else message


def generate_commit_candidates(
    diff: str,
    staged_files: Optional[list[StagedFile]] = None,
    model: Optional[str] = None,
    count: int = 3,
    detailed: Optional[bool] = None,
    hint: Optional[str] = None,
) -> list[str]:
    """Generate multiple candidate commit messages for the developer to choose from.

    Falls back to generating varied heuristic messages if AI generation fails.
    """
    model = model or settings.default_model
    staged_files = staged_files or []
    is_detailed = settings.detailed if detailed is None else detailed

    try:
        raw_output = _generate_with_ai(
            diff=diff,
            staged_files=staged_files,
            model=model,
            detailed=is_detailed,
            hint=hint,
            count=count,
        )
        candidates = _extract_candidates(raw_output, count, detailed=is_detailed)
        if candidates:
            return [_apply_emoji(c) if settings.use_emoji else c for c in candidates]
    except Exception as exc:
        console.print(f"[yellow]! AI candidate generation fallback triggered: {exc}[/yellow]")

    # Fallback: produce varied heuristic messages
    candidates = _generate_fallback_candidates(staged_files, diff=diff, count=count, detailed=is_detailed)
    return [_apply_emoji(c) if settings.use_emoji else c for c in candidates]


def _build_prompt(
    diff: str,
    staged_files: list[StagedFile],
    detailed: bool,
    hint: Optional[str] = None,
    count: int = 1,
) -> str:
    """Build the prompt combining instructions, context, developer hint, and diff."""
    system_prompt = load_prompt()
    diff_for_prompt = diff[: settings.max_diff_chars]
    was_truncated = len(diff) > settings.max_diff_chars

    prompt_parts = [system_prompt, "\n"]

    if staged_files:
        files_summary = "\n".join(f"- {f.status} {f.path}" for f in staged_files[:15])
        if len(staged_files) > 15:
            files_summary += f"\n- ... and {len(staged_files) - 15} more files"
        prompt_parts.append(f"Changed Files Summary:\n{files_summary}\n")

    if hint:
        prompt_parts.append(f"Developer Hint / Intent:\n{hint.strip()}\n")

    if detailed:
        prompt_parts.append(
            "Instructions for Detailed Commit Message:\n"
            "- First line: <type>(<scope>): <subject line under 72 chars>\n"
            "- Second line: blank line\n"
            "- Third line onwards: A concise explanation of why the change was made, "
            "followed by bullet points (- ...) detailing key technical changes.\n"
        )
    else:
        prompt_parts.append(
            "Instructions for Commit Message:\n"
            "- Provide a complete, expressive single subject line: <type>(<scope>): <description>\n"
            "- Express the full purpose clearly (aim for 50-100 characters). Ensure the sentence is complete and never cut off mid-thought.\n"
            "- Lowercase start after colon, imperative mood, no trailing period, no dangling words.\n"
        )

    if count > 1:
        prompt_parts.append(
            f"Generate exactly {count} distinct candidate commit messages.\n"
            "Format as a numbered list:\n1. <candidate 1>\n2. <candidate 2>\n3. <candidate 3>\n"
        )

    prompt_parts.append(f"Git Diff:\n```\n{diff_for_prompt}\n```")

    if was_truncated:
        prompt_parts.append(
            "\n(Note: the diff above was truncated due to size. Base the message on the visible changes.)"
        )

    return "\n".join(prompt_parts)


def _call_ollama_api(prompt: str, model: str) -> Optional[str]:
    """Call Ollama via its local HTTP REST API for fast, reliable JSON inference."""
    host = settings.ollama_host.rstrip("/")
    url = f"{host}/api/generate"

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=settings.ai_timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return data.get("response", "")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _call_ollama_cli(prompt: str, model: str) -> str:
    """Call Ollama via the CLI subprocess as a secondary backend."""
    cmd = ["ollama", "run", "--nowordwrap", model]
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=settings.ai_timeout_seconds,
        )
    except FileNotFoundError:
        # Retry without --nowordwrap in case older Ollama version does not support it
        cmd = ["ollama", "run", model]
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=settings.ai_timeout_seconds,
        )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise AIGenerationError(stderr or f"Ollama CLI exited with code {result.returncode}.")

    return result.stdout


def _generate_with_ai(
    diff: str,
    staged_files: list[StagedFile],
    model: str,
    detailed: bool = False,
    hint: Optional[str] = None,
    count: int = 1,
) -> str:
    """Orchestrate AI generation via Ollama (CLI subprocess or HTTP API)."""
    prompt = _build_prompt(diff, staged_files, detailed=detailed, hint=hint, count=count)

    console.print(f"[dim]Calling {model} via Ollama...[/dim]")

    raw_output: Optional[str] = None
    if getattr(settings, "use_api", False):
        raw_output = _call_ollama_api(prompt, model)

    if not raw_output or not raw_output.strip():
        raw_output = _call_ollama_cli(prompt, model)

    if count > 1:
        console.print("[green]+ Generated candidates with AI[/green]")
        return raw_output

    cleaned = _clean_message(raw_output, detailed=detailed)
    if not cleaned or len(cleaned) < 5:
        raise AIGenerationError("Ollama returned an empty response.")

    console.print("[green]+ Generated with AI[/green]")
    return cleaned


_DANGLING_ENDINGS = {
    "and", "or", "to", "for", "with", "of", "in", "on",
    "the", "a", "an", "by", "from", "at", "as", "that",
    "which", "about", "into", "over", "after", "before",
    "but", "so", "yet", "nor", "if", "then", "else",
}


def _truncate_header(header: str, max_len: int) -> str:
    """Clamp header to max length without breaking words or leaving dangling connectors."""
    if len(header) <= max_len:
        return header

    truncated = header[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 25:
        truncated = truncated[:last_space].rstrip(" ,;:-")

    # Prevent ending on dangling conjunctions, prepositions, or articles
    words = truncated.split()
    while words and words[-1].lower() in _DANGLING_ENDINGS:
        words.pop()
        truncated = " ".join(words).rstrip(" ,;:-")

    return truncated


def _clean_message(raw: str, detailed: bool = False) -> str:
    """Strip ANSI codes, markdown code fences, meta preambles, and formatting."""
    text = strip_ansi(raw).strip()

    # Strip code block fences if model wrapped entire output in ```
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Strip conversational prefixes
    prefixes = [
        "Commit message:",
        "Commit Message:",
        "Suggested commit message:",
        "Suggested commit:",
        "Conventional commit:",
        "Here is the commit message:",
        "Here is your commit message:",
    ]
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()

    # Strip enclosing quotation marks
    text = text.strip("`").strip('"').strip("'").strip()

    if not detailed:
        # Extract the first non-empty line
        for line in text.splitlines():
            line = line.strip().strip("`").strip('"').strip("'")
            if line:
                # Remove trailing period if present on subject line
                if line.endswith(".") and not line.endswith("..."):
                    line = line[:-1]
                return _truncate_header(line, settings.max_length)
        return ""

    # In detailed mode: clean first line and preserve body
    lines = text.splitlines()
    cleaned_lines: list[str] = []
    first_line_found = False

    for line in lines:
        stripped = line.rstrip()
        if not first_line_found:
            if not stripped:
                continue
            first_line = stripped.strip("`").strip('"').strip("'")
            if first_line.endswith(".") and not first_line.endswith("..."):
                first_line = first_line[:-1]
            cleaned_lines.append(_truncate_header(first_line, settings.max_length))
            first_line_found = True
        else:
            cleaned_lines.append(stripped)

    # Ensure a blank line exists after the subject line if a body exists
    if len(cleaned_lines) > 1 and cleaned_lines[1].strip() != "":
        cleaned_lines.insert(1, "")

    return "\n".join(cleaned_lines).strip()


def _extract_candidates(raw_text: str, expected_count: int, detailed: bool = False) -> list[str]:
    """Parse candidate commit messages from a numbered list output."""
    cleaned = strip_ansi(raw_text).strip()
    candidates: list[str] = []

    # Try regex match for numbered list: "1. ... \n2. ... "
    pattern = re.compile(r"^(?:Candidate\s+)?(\d+)[\.\):]\s*(.+)$", re.MULTILINE)
    matches = pattern.findall(cleaned)

    if matches:
        for _, match_text in matches[:expected_count]:
            candidate = _clean_message(match_text, detailed=False)
            if candidate and len(candidate) > 5:
                candidates.append(candidate)

    if not candidates:
        # Split by non-empty lines if no numbers matched
        for line in cleaned.splitlines():
            cand = _clean_message(line, detailed=False)
            if cand and len(cand) > 5:
                candidates.append(cand)
            if len(candidates) >= expected_count:
                break

    return candidates


# --- Enhanced Rule-Based Fallback Engine ---------------------------------

_KEYWORD_TO_TYPE = {
    "test": "test",
    "spec": "test",
    "fixture": "test",
    ".github/": "ci",
    ".gitlab-ci": "ci",
    "docker": "build",
    "pyproject": "build",
    "package.json": "build",
    "requirements": "build",
    "setup.py": "build",
    "cargo.toml": "build",
    "readme": "docs",
    "changelog": "docs",
    "license": "docs",
    "contributing": "docs",
    "docs/": "docs",
}

_EXT_TO_TYPE = {
    ".md": "docs",
    ".rst": "docs",
    ".txt": "docs",
    ".yml": "ci",
    ".yaml": "ci",
    ".toml": "build",
}


def _infer_type_from_diff(diff: str, files: list[StagedFile]) -> str:
    """Inspect diff text and staged files to infer the most accurate commit type."""
    paths = [f.path.lower() for f in files]

    # Priority 1: Check known file paths
    for path in paths:
        for keyword, ctype in _KEYWORD_TO_TYPE.items():
            if keyword in path:
                return ctype

    for path in paths:
        for ext, ctype in _EXT_TO_TYPE.items():
            if path.endswith(ext):
                return ctype

    # Priority 2: Inspect diff additions for semantic code indicators
    diff_lower = diff.lower()
    if re.search(r"\+(?:def test_|it\(|describe\(|assert |expect\()", diff):
        return "test"
    if any(k in diff_lower for k in ["fix", "bug", "issue", "resolve", "handle_error", "except", "catch"]):
        return "fix"
    if any(k in diff_lower for k in ["cache", "optimize", "perf", "latency", "vectorize"]):
        return "perf"
    if any(k in diff_lower for k in ["refactor", "rename", "clean"]):
        return "refactor"

    # Priority 3: Fallback based on Git file status
    statuses = {f.status for f in files}
    if statuses == {"A"}:
        return "feat"
    if statuses == {"D"}:
        return "chore"
    if statuses <= {"M"}:
        return "fix"

    return "feat"


def _infer_scope(files: list[StagedFile]) -> Optional[str]:
    """Derive a clean, concise domain scope from changed files."""
    if not files:
        return None

    # If single file, extract basename without extension or immediate directory
    if len(files) == 1:
        path = files[0].path
        parts = path.replace("\\", "/").split("/")
        filename = parts[-1]
        name_no_ext = filename.rsplit(".", 1)[0].lower()

        # If file is like test_cli.py or cli_test.py, scope is cli
        name_clean = re.sub(r"^(test_|tests_)|(_test|_tests)$", "", name_no_ext)
        if name_clean in {"cli", "config", "git", "ai", "utils", "main", "app", "auth", "api", "client"}:
            return name_clean

        # Check directory name if file is generic like __init__.py, index.ts
        if len(parts) > 1 and name_clean in {"__init__", "index", "main", "base"}:
            return parts[-2].lower()

        return name_clean if len(name_clean) <= 12 else None

    # If multiple files, check if they share a common directory
    dirs = {f.path.replace("\\", "/").split("/")[0] for f in files if "/" in f.path.replace("\\", "/")}
    if len(dirs) == 1:
        domain = next(iter(dirs)).lower()
        # If top directory is src or lib, inspect second level
        if domain in {"src", "lib", "pkg"}:
            subdirs = {
                f.path.replace("\\", "/").split("/")[1]
                for f in files
                if len(f.path.replace("\\", "/").split("/")) > 2
            }
            if len(subdirs) == 1:
                return next(iter(subdirs)).lower()
        return domain

    return None


def generate_fallback_message(
    files: list[StagedFile],
    diff: str = "",
    detailed: bool = False,
) -> str:
    """Build a high-quality Conventional Commit message heuristically."""
    if not files:
        return "chore: update project files"

    commit_type = _infer_type_from_diff(diff, files)
    scope = _infer_scope(files)

    if len(files) == 1:
        file = files[0]
        name = file.path.replace("\\", "/").split("/")[-1]
        action = "add" if file.status == "A" else ("remove" if file.status == "D" else "update")
        subject = f"{action} {name}"
    elif scope:
        subject = f"update {scope} module ({len(files)} files)"
    else:
        subject = f"update {len(files)} files across project"

    header = f"{commit_type}({scope})" if scope else commit_type
    first_line = f"{header}: {subject}"
    if len(first_line) > settings.max_length:
        first_line = first_line[: settings.max_length]

    if not detailed:
        return first_line

    # Build detailed body for fallback
    body_lines = [
        first_line,
        "",
        "Summary of staged changes:",
    ]
    for f in files[:8]:
        action_name = {"A": "Added", "M": "Updated", "D": "Removed", "R": "Renamed"}.get(f.status, "Modified")
        body_lines.append(f"- {action_name} {f.path}")
    if len(files) > 8:
        body_lines.append(f"- ... and {len(files) - 8} more files")

    return "\n".join(body_lines)


def _generate_fallback_candidates(
    files: list[StagedFile],
    diff: str = "",
    count: int = 3,
    detailed: bool = False,
) -> list[str]:
    """Generate diverse heuristic fallback candidates."""
    base_msg = generate_fallback_message(files, diff=diff, detailed=detailed)
    candidates = [base_msg]

    if count <= 1 or not files:
        return candidates

    scope = _infer_scope(files)
    header = f"refactor({scope})" if scope else "refactor"
    alt_subject = f"{header}: refactor and enhance implementation"
    if alt_subject not in candidates:
        candidates.append(alt_subject[: settings.max_length])

    header_chore = f"chore({scope})" if scope else "chore"
    alt_chore = f"{header_chore}: update project codebase"
    if alt_chore not in candidates and len(candidates) < count:
        candidates.append(alt_chore[: settings.max_length])

    return candidates[:count]


def _apply_emoji(message: str) -> str:
    """Prepend the appropriate gitmoji to the commit subject line."""
    lines = message.splitlines()
    if not lines:
        return message

    first_line = lines[0]
    commit_type = first_line.split("(")[0].split(":")[0].strip()
    emoji = _EMOJI_BY_TYPE.get(commit_type)

    if not emoji:
        return message

    lines[0] = f"{emoji} {first_line}"
    return "\n".join(lines)