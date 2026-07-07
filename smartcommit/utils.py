"""Small shared helpers: prompt loading and cross-platform clipboard support."""

import platform
import subprocess
from pathlib import Path


def load_prompt() -> str:
    """Load the system prompt that instructs the model, from prompts/conventional_prompt.txt.

    Falls back to a minimal inline prompt if the file is missing so the tool
    still works from a partial install or a zipped/pip-installed package.
    """
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "conventional_prompt.txt"

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()

    return (
        "You are an expert software engineer who writes excellent git commit "
        "messages. Follow the Conventional Commits specification strictly. "
        "Be clear, concise, and professional. Respond with ONLY the commit "
        "message, no explanations or quotes."
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