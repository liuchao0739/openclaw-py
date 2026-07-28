from __future__ import annotations

from openclaw_extensions.googlechat.src.doctor_contract import run_google_chat_doctor


def run_google_chat_channel_doctor(params: dict) -> dict:
    return run_google_chat_doctor(params)


__all__ = ["run_google_chat_channel_doctor"]