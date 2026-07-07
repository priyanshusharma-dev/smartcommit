"""Tests for git_utils.py. All git calls are mocked -- no real repo needed."""

import subprocess
from unittest.mock import patch, MagicMock

from smartcommit.git_utils import get_staged_diff, get_staged_files, is_git_repository, StagedFile


def _mock_result(stdout="", returncode=0):
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    return result


def test_is_git_repository_true():
    with patch("subprocess.run", return_value=_mock_result("true")):
        assert is_git_repository() is True


def test_is_git_repository_false_when_not_a_repo():
    with patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(128, "git", stderr="not a git repository"),
    ):
        assert is_git_repository() is False


def test_is_git_repository_false_when_git_missing():
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        assert is_git_repository() is False


def test_get_staged_diff_returns_stripped_output():
    with patch("subprocess.run", return_value=_mock_result("  diff --git a/x b/x\n  ")):
        assert get_staged_diff() == "diff --git a/x b/x"


def test_get_staged_diff_returns_empty_string_on_error():
    with patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(128, "git", stderr="fatal error"),
    ):
        assert get_staged_diff() == ""


def test_get_staged_files_parses_name_status_output():
    raw_output = "A\tsmartcommit/new_module.py\nM\tREADME.md\nD\told_file.py\n"
    with patch("subprocess.run", return_value=_mock_result(raw_output)):
        files = get_staged_files()

    assert files == [
        StagedFile(status="A", path="smartcommit/new_module.py"),
        StagedFile(status="M", path="README.md"),
        StagedFile(status="D", path="old_file.py"),
    ]


def test_get_staged_files_handles_rename_status_codes():
    # Git reports renames as e.g. "R100\told.py\tnew.py"
    raw_output = "R100\told.py\tnew.py\n"
    with patch("subprocess.run", return_value=_mock_result(raw_output)):
        files = get_staged_files()

    assert files == [StagedFile(status="R", path="new.py")]


def test_get_staged_files_returns_empty_list_on_error():
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(128, "git")):
        assert get_staged_files() == []