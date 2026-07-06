import os
from pathlib import Path

def load_prompt() -> str:
    """Load the system prompt from file"""
    prompt_path = Path(__file__).parent.parent / "prompts" / "conventional_prompt.txt"
    
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    else:
        # Fallback prompt
        return """You are an expert software engineer who writes excellent git commit messages.
Follow Conventional Commits specification strictly.
Be clear, concise, and professional."""


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard (Windows)"""
    try:
        import subprocess
        subprocess.run("clip", input=text, text=True, check=True)
        return True
    except:
        return False