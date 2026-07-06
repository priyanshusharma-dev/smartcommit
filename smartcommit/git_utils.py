import subprocess
from rich.console import Console

console = Console()

def get_staged_diff() -> str:
    """Get the diff of currently staged changes"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        console.print("[red]Error: Not a git repository.[/red]")
        return ""
    except Exception as e:
        console.print(f"[red]Git error: {e}[/red]")
        return ""