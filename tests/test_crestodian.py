"""Tests for crestodian audit and dialogue helpers."""

import asyncio
import json
from pathlib import Path

import pytest

from openclaw.crestodian.audit import (
    append_crestodian_audit_entry,
    resolve_crestodian_audit_path,
)
from openclaw.crestodian.dialogue import (
    approval_question,
    is_yes,
    should_ask_assistant,
)


def test_resolve_audit_path_default(tmp_path):
    p = resolve_crestodian_audit_path(state_dir=str(tmp_path))
    assert p.endswith("audit/crestodian.jsonl")
    assert str(tmp_path) in p


def test_resolve_audit_path_env(tmp_path):
    p = resolve_crestodian_audit_path(env={"OPENCLAW_STATE_DIR": str(tmp_path)})
    assert str(tmp_path) in p


async def test_append_audit_entry(tmp_path):
    audit = tmp_path / "audit" / "crestodian.jsonl"
    written = await append_crestodian_audit_entry(
        {"operation": "apply", "summary": "test op"},
        audit_path=str(audit),
    )
    assert written == str(audit)
    assert audit.exists()
    lines = audit.read_text().strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["operation"] == "apply"
    assert rec["summary"] == "test op"
    assert "timestamp" in rec


async def test_append_multiple_entries(tmp_path):
    audit = tmp_path / "audit" / "crestodian.jsonl"
    await append_crestodian_audit_entry({"operation": "a"}, audit_path=str(audit))
    await append_crestodian_audit_entry({"operation": "b"}, audit_path=str(audit))
    lines = audit.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["operation"] == "a"
    assert json.loads(lines[1])["operation"] == "b"


async def test_append_with_details(tmp_path):
    audit = tmp_path / "audit" / "crestodian.jsonl"
    await append_crestodian_audit_entry(
        {"operation": "apply", "configPath": "/x", "configHashBefore": "h1",
         "configHashAfter": "h2", "details": {"k": "v"}},
        audit_path=str(audit),
    )
    rec = json.loads(audit.read_text().strip())
    assert rec["configPath"] == "/x"
    assert rec["details"] == {"k": "v"}


def test_approval_question_with_description():
    class Op:
        description = "enable channel X"
        kind = "enable"
    q = approval_question(Op())
    assert "enable channel X" in q
    assert q.startswith("Apply this operation:")


def test_approval_question_with_dict():
    q = approval_question({"kind": "none", "summary": "do thing"})
    assert "do thing" in q


def test_approval_question_fallback_kind():
    class Op:
        kind = "disable"
    q = approval_question(Op())
    assert "disable" in q


def test_is_yes_affirmative():
    assert is_yes("y")
    assert is_yes("yes")
    assert is_yes("Yes")
    assert is_yes("apply")
    assert is_yes("do it")
    assert is_yes("approve")
    assert is_yes("approved")
    assert is_yes("  yes  ")


def test_is_yes_negative():
    assert not is_yes("no")
    assert not is_yes("n")
    assert not is_yes("cancel")
    assert not is_yes("")
    assert not is_yes("maybe")


def test_should_ask_assistant_none_kind():
    assert should_ask_assistant("do something", {"kind": "none"}) is True


def test_should_ask_assistant_known_kind():
    assert should_ask_assistant("enable X", {"kind": "enable"}) is False


def test_should_ask_assistant_empty():
    assert should_ask_assistant("", {"kind": "none"}) is False
    assert should_ask_assistant("   ", {"kind": "none"}) is False


def test_should_ask_assistant_quit_exit():
    assert should_ask_assistant("quit", {"kind": "none"}) is False
    assert should_ask_assistant("exit", {"kind": "none"}) is False
    assert should_ask_assistant("QUIT", {"kind": "none"}) is False
