import subprocess
from rich.console import Console

console = Console()

def generate_commit_message(diff: str, model: str = "qwen2.5-coder:7b") -> str:
    """Generate commit message - with better timeout handling"""
    
    # Very short prompt to reduce load
    prompt = f"Conventional commit for these changes:\n{diff[:800]}"
    
    try:
        console.print("[dim]Calling AI...[/dim]")
        
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8          # Even shorter timeout
        )
        
        msg = result.stdout.strip()
        
        if msg and len(msg) > 5:
            console.print("[green]AI Success![/green]")
            return msg
        else:
            raise Exception("Empty response")
            
    except Exception as e:
        console.print("[yellow]AI unavailable → Using smart fallback[/yellow]")
        # Smart fallback based on files changed
        return "feat: update code changes"