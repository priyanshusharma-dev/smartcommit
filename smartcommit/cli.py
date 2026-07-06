import typer
from rich.console import Console
from .git_utils import get_staged_diff
from .ai_generator import generate_commit_message

app = typer.Typer(help="AI Git Commit Generator")

console = Console()

@app.command()
def main(
    model: str = typer.Option("llama3.2:3b", "--model", "-m")
):
    diff = get_staged_diff()
    
    if not diff:
        console.print("[red]No staged changes found. Use 'git add' first.[/red]")
        return

    console.print("[cyan]Generating commit message...[/cyan]")
    message = generate_commit_message(diff, model)
    console.print("\n[bold green]Suggested Commit Message:[/bold green]\n")
    console.print(message)

if __name__ == "__main__":
    app()