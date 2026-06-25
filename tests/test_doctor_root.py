"""Tests for commands/doctor root — types, emit notes, finalize config flow."""

from __future__ import annotations

from openclaw.commands.doctor.emit_notes import (
    emit_doctor_notes,
    sanitize_doctor_note,
)
from openclaw.commands.doctor.finalize_config_flow import (
    finalize_doctor_config_flow,
)


class TestSanitizeDoctorNote:
    def test_plain_text(self):
        assert sanitize_doctor_note("hello world") == "hello world"

    def test_with_ansi(self):
        assert sanitize_doctor_note("\x1b[31mred\x1b[0m text") == "red text"

    def test_multiline(self):
        result = sanitize_doctor_note("line1\n\x1b[32mline2\x1b[0m")
        assert result == "line1\nline2"


class TestEmitDoctorNotes:
    def test_emit_all(self):
        notes: list[tuple[str, str | None]] = []

        def note_fn(message: str, title: str | None = None) -> None:
            notes.append((message, title))

        emit_doctor_notes(
            note_fn,
            change_notes=["change1"],
            info_notes=["info1"],
            warning_notes=["warn1"],
        )
        assert len(notes) == 3
        assert notes[0] == ("change1", "Doctor changes")
        assert notes[1] == ("info1", "Doctor info")
        assert notes[2] == ("warn1", "Doctor warnings")

    def test_emit_empty(self):
        notes: list[tuple[str, str | None]] = []
        emit_doctor_notes(lambda m, t=None: notes.append((m, t)))
        assert notes == []

    def test_sanitizes(self):
        notes: list[str] = []
        emit_doctor_notes(
            lambda m, t=None: notes.append(m),
            change_notes=["\x1b[31mred\x1b[0m"],
        )
        assert notes == ["red"]


class TestFinalizeConfigFlow:
    async def test_no_repair_with_changes_confirmed(self):
        async def confirm(params):
            return True

        result = await finalize_doctor_config_flow(
            cfg={"old": True},
            candidate={"new": True},
            pending_changes=True,
            should_repair=False,
            fix_hints=[],
            confirm=confirm,
            note=lambda m, t=None: None,
        )
        assert result["shouldWriteConfig"] is True
        assert result["cfg"] == {"new": True}

    async def test_no_repair_with_changes_declined(self):
        notes: list[str] = []

        async def confirm(params):
            return False

        result = await finalize_doctor_config_flow(
            cfg={"old": True},
            candidate={"new": True},
            pending_changes=True,
            should_repair=False,
            fix_hints=["hint1"],
            confirm=confirm,
            note=lambda m, t=None: notes.append(m),
        )
        assert result["shouldWriteConfig"] is False
        assert result["cfg"] == {"old": True}
        assert "hint1" in notes[0]

    async def test_repair_mode_with_changes(self):
        result = await finalize_doctor_config_flow(
            cfg={"old": True},
            candidate={"new": True},
            pending_changes=True,
            should_repair=True,
            fix_hints=[],
            confirm=lambda p: None,
            note=lambda m, t=None: None,
        )
        assert result["shouldWriteConfig"] is True

    async def test_no_changes(self):
        result = await finalize_doctor_config_flow(
            cfg={"cfg": True},
            candidate={"cfg": True},
            pending_changes=False,
            should_repair=False,
            fix_hints=[],
            confirm=lambda p: None,
            note=lambda m, t=None: None,
        )
        assert result["shouldWriteConfig"] is False
