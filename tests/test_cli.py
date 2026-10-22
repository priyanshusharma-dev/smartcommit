"""Tests for cli.py using Typer's CliRunner."""

from unittest.mock import patch
from typer.testing import CliRunner

from smartcommit.cli import app
from smartcommit.git_utils import StagedFile

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "smartcommit" in result.stdout


def test_cli_not_a_git_repo():
    with patch("smartcommit.cli.is_git_repository", return_value=False):
        result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "Not inside a Git repository" in result.stdout


def test_cli_no_staged_changes():
    with patch("smartcommit.cli.is_git_repository", return_value=True), \
         patch("smartcommit.cli.get_filtered_staged_diff", return_value=("", [])):
        result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "No staged changes found" in result.stdout


def test_cli_dry_run_success():
    with patch("smartcommit.cli.is_git_repository", return_value=True), \
         patch("smartcommit.cli.get_filtered_staged_diff", return_value=("diff --git ...", [])), \
         patch("smartcommit.cli.get_staged_files", return_value=[StagedFile(status="M", path="README.md")]), \
         patch("smartcommit.cli.generate_commit_message", return_value="docs(readme): update guide"):
        result = runner.invoke(app, ["--dry-run"])
        assert result.exit_code == 0
        assert "docs(readme): update guide" in result.stdout


def test_cli_auto_commit_flag():
    with patch("smartcommit.cli.is_git_repository", return_value=True), \
         patch("smartcommit.cli.get_filtered_staged_diff", return_value=("diff --git ...", [])), \
         patch("smartcommit.cli.get_staged_files", return_value=[StagedFile(status="A", path="auth.py")]), \
         patch("smartcommit.cli.generate_commit_message", return_value="feat(auth): add auth module"), \
         patch("smartcommit.cli.git_commit", return_value=(True, "[main abc1234] feat(auth): add auth module")):
        result = runner.invoke(app, ["--commit"])
        assert result.exit_code == 0
        assert "Successfully committed staged changes" in result.stdout


def test_cli_hint_passed_to_generator():
    with patch("smartcommit.cli.is_git_repository", return_value=True), \
         patch("smartcommit.cli.get_filtered_staged_diff", return_value=("diff --git ...", [])), \
         patch("smartcommit.cli.get_staged_files", return_value=[StagedFile(status="M", path="main.py")]), \
         patch("smartcommit.cli.generate_commit_message", return_value="fix: resolve memory leak") as mock_gen:
        result = runner.invoke(app, ["--dry-run", "--hint", "resolve memory leak in loop"])
        assert result.exit_code == 0
        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs["hint"] == "resolve memory leak in loop"


def test_cli_detailed_flag_passed():
    with patch("smartcommit.cli.is_git_repository", return_value=True), \
         patch("smartcommit.cli.get_filtered_staged_diff", return_value=("diff --git ...", [])), \
         patch("smartcommit.cli.get_staged_files", return_value=[]), \
         patch("smartcommit.cli.generate_commit_message", return_value="feat: detailed commit\n\n- body") as mock_gen:
        result = runner.invoke(app, ["--dry-run", "--detailed"])
        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["detailed"] is True


def test_cli_diff_stat_flag():
    with patch("smartcommit.cli.is_git_repository", return_value=True), \
         patch("smartcommit.cli.get_filtered_staged_diff", return_value=("diff ...", [])), \
         patch("smartcommit.cli.get_staged_files", return_value=[]), \
         patch("smartcommit.cli.get_diff_stat", return_value="1 file changed, 10 insertions(+)"), \
         patch("smartcommit.cli.generate_commit_message", return_value="feat: thing"):
        result = runner.invoke(app, ["--dry-run", "--stat"])
        assert result.exit_code == 0
        assert "1 file changed, 10 insertions(+)" in result.stdout
