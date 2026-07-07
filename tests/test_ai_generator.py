"""Tests for ai_generator.py -- both the AI path (mocked) and the rule-based fallback."""

import subprocess
from unittest.mock import patch, MagicMock

from smartcommit.ai_generator import generate_commit_message, generate_fallback_message
from smartcommit.git_utils import StagedFile


# --- Rule-based fallback: the part that must actually be "smart" ---------

def test_fallback_infers_feat_for_only_added_files():
    files = [StagedFile(status="A", path="smartcommit/new_feature.py")]
    message = generate_fallback_message(files)
    assert message.startswith("feat")


def test_fallback_infers_docs_for_markdown_files():
    files = [StagedFile(status="M", path="README.md")]
    message = generate_fallback_message(files)
    assert message.startswith("docs")


def test_fallback_infers_test_for_test_files():
    files = [StagedFile(status="A", path="tests/test_cli.py")]
    message = generate_fallback_message(files)
    assert message.startswith("test")


def test_fallback_infers_chore_for_only_deleted_files():
    files = [StagedFile(status="D", path="old_module.py")]
    message = generate_fallback_message(files)
    assert message.startswith("chore")


def test_fallback_infers_scope_from_shared_directory():
    files = [
        StagedFile(status="M", path="smartcommit/cli.py"),
        StagedFile(status="M", path="smartcommit/config.py"),
    ]
    message = generate_fallback_message(files)
    assert "(smartcommit)" in message


def test_fallback_handles_no_staged_files():
    assert generate_fallback_message([]) == "chore: update project files"


def test_fallback_respects_max_length():
    files = [StagedFile(status="M", path=f"file_{i}.py") for i in range(50)]
    message = generate_fallback_message(files)
    assert len(message) <= 72


# --- End-to-end fallback trigger: AI unavailable --------------------------

def test_generate_commit_message_falls_back_when_ollama_missing():
    files = [StagedFile(status="A", path="smartcommit/new_feature.py")]
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        message = generate_commit_message("diff --git a/x b/x", files, model="llama3.2:3b")
    assert message.startswith("feat")


def test_generate_commit_message_falls_back_on_timeout():
    files = [StagedFile(status="M", path="README.md")]
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ollama", timeout=20)):
        message = generate_commit_message("diff --git a/x b/x", files, model="llama3.2:3b")
    assert message.startswith("docs")


def test_generate_commit_message_uses_ai_output_when_available():
    mock_result = MagicMock(stdout="feat: add login endpoint\n", returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        message = generate_commit_message("diff --git a/x b/x", [], model="llama3.2:3b")
    assert message == "feat: add login endpoint"


def test_generate_commit_message_falls_back_on_empty_ai_response():
    mock_result = MagicMock(stdout="   ", returncode=0, stderr="")
    files = [StagedFile(status="A", path="smartcommit/new_feature.py")]
    with patch("subprocess.run", return_value=mock_result):
        message = generate_commit_message("diff --git a/x b/x", files, model="llama3.2:3b")
    assert message.startswith("feat")