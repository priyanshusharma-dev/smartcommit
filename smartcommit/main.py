import typer
from rich.console import Console
from .cli import app

console = Console()

def main():
    """Entry point for the CLI"""
    app()

if __name__ == "__main__":
    main()