"""Tests for ai_generator.py -- AI generation, candidate parsing, detailed mode, and heuristics."""

import subprocess
from unittest.mock import patch, MagicMock

from smartcommit.ai_generator import (
    generate_commit_candidates,
    generate_commit_message,
    generate_fallback_message,
    _clean_message,
    _extract_candidates,
    _apply_emoji,
    _truncate_header,
)
from smartcommit.config import settings
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
    assert len(message) <= settings.max_length


def test_fallback_infers_semantic_types_from_diff_content():
    test_diff = "+def test_something():\n+    assert True"
    msg = generate_fallback_message([StagedFile(status="M", path="foo.py")], diff=test_diff)
    assert msg.startswith("test")

    fix_diff = "+# fix bug in session expiration\n+handle_error(e)"
    msg_fix = generate_fallback_message([StagedFile(status="M", path="foo.py")], diff=fix_diff)
    assert msg_fix.startswith("fix")

    perf_diff = "+# cache computed results to optimize latency\n+result_cache[k] = val"
    msg_perf = generate_fallback_message([StagedFile(status="M", path="foo.py")], diff=perf_diff)
    assert msg_perf.startswith("perf")


def test_fallback_detailed_mode():
    files = [
        StagedFile(status="A", path="smartcommit/auth.py"),
        StagedFile(status="M", path="smartcommit/cli.py"),
    ]
    msg = generate_fallback_message(files, detailed=True)
    lines = msg.splitlines()
    assert len(lines) >= 3
    assert lines[1] == ""
    assert any("Added smartcommit/auth.py" in line for line in lines)


# --- End-to-end AI generator tests (mocked) -------------------------------

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


def test_generate_commit_message_detailed_preserves_body():
    raw_ai = (
        "feat(auth): add JWT bearer authentication\n\n"
        "- Validate incoming tokens\n"
        "- Add refresh endpoint\n"
    )
    mock_result = MagicMock(stdout=raw_ai, returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        message = generate_commit_message("diff ...", [], model="llama3.2:3b", detailed=True)
    lines = message.splitlines()
    assert lines[0] == "feat(auth): add JWT bearer authentication"
    assert lines[1] == ""
    assert "- Validate incoming tokens" in lines


def test_generate_commit_candidates_parses_numbered_list():
    raw_ai = (
        "1. feat(cli): add interactive commit menu\n"
        "2. feat(cli): prompt for commit confirmation\n"
        "3. refactor(cli): simplify user prompts\n"
    )
    mock_result = MagicMock(stdout=raw_ai, returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        cands = generate_commit_candidates("diff ...", [], model="llama3.2:3b", count=3)
    assert len(cands) == 3
    assert cands[0] == "feat(cli): add interactive commit menu"
    assert cands[1] == "feat(cli): prompt for commit confirmation"
    assert cands[2] == "refactor(cli): simplify user prompts"


def test_extract_candidates_variations():
    raw = (
        "Candidate 1: feat(cli): first option\n"
        "Candidate 2: feat(cli): second option\n"
    )
    cands = _extract_candidates(raw, 2)
    assert len(cands) == 2
    assert cands[0] == "feat(cli): first option"
    assert cands[1] == "feat(cli): second option"


def test_clean_message_strips_ansi_and_fences():
    raw = "\x1b[32m```\nfeat(cli): add version command\n```\x1b[0m"
    cleaned = _clean_message(raw)
    assert cleaned == "feat(cli): add version command"


def test_clean_message_strips_conversational_prefixes():
    raw = "Here is your commit message: feat(core): implement feature"
    assert _clean_message(raw) == "feat(core): implement feature"


def test_apply_emoji():
    single = "feat(auth): add login"
    assert _apply_emoji(single) == "✨ feat(auth): add login"

    multi = "fix(git): handle error\n\n- Details here"
    applied_multi = _apply_emoji(multi)
    assert applied_multi.startswith("🐛 fix(git): handle error")
    assert "- Details here" in applied_multi


def test_truncate_header_removes_dangling_connectors():
    # If cut off at 72, it would end with "and", but the new implementation strips dangling "and"
    raw = "fix(app): update global CSS file to remove redundant imports and optimize page load performance"
    truncated = _truncate_header(raw, max_len=72)
    assert not truncated.endswith("and")
    assert truncated == "fix(app): update global CSS file to remove redundant imports"


def test_clean_message_preserves_full_expressive_subjects():
    # Full 106-character message should be preserved completely without being cut off
    expressive = "feat: enhance commit message generation with detailed mode, candidate selection, and interactive workflows"
    cleaned = _clean_message(expressive)
    assert cleaned == expressive