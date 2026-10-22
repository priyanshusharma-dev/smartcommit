"""Small shared helpers: prompt loading, ANSI stripping, and clipboard support."""

import platform
import re
import subprocess
from pathlib import Path

_ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    """Remove terminal ANSI escape sequences from raw string."""
    return _ANSI_ESCAPE_PATTERN.sub("", text)


def load_prompt(filename: str = "conventional_prompt.txt") -> str:
    """Load the prompt instructions from prompts/<filename>.

    Falls back to a built-in prompt if the file is missing so the tool
    still works from a partial install or a zipped/pip-installed package.
    """
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / filename

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()

    return (
        "You are an expert software engineer following Conventional Commits 1.0.0.\n"
        "Generate a clear, professional commit message for the git diff.\n"
        "Rules:\n"
        "- Format: <type>(<scope>): <description>\n"
        "- Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore\n"
        "- Scope: concise module name in lowercase\n"
        "- Imperative mood, lowercase description, under 72 chars, no trailing period\n"
        "- Respond with ONLY the commit message. No explanations or quotes."
    )


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard on Windows, macOS, or Linux.

    Returns False (never raises) if no clipboard utility is available, so
    callers can degrade gracefully instead of crashing.
    """
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run("clip", input=text, text=True, check=True)
        elif system == "Darwin":
            subprocess.run("pbcopy", input=text, text=True, check=True)
        else:
            # Requires xclip on Linux: sudo apt install xclip
            subprocess.run(
                ["xclip", "-selection", "clipboard"], input=text, text=True, check=True
            )
        return True
    except Exception:
        return False