"""Tests for media-understanding format helpers."""

from __future__ import annotations

from openclaw_packages.media_understanding_common import format_media_understanding_body


def test_replaces_placeholder_body_with_transcript() -> None:
    body = format_media_understanding_body(
        body="<media:audio>",
        outputs=[
            {
                "kind": "audio.transcription",
                "attachment_index": 0,
                "text": "hello world",
                "provider": "groq",
            },
        ],
    )
    assert body == "[Audio]\nTranscript:\nhello world"


def test_includes_user_text_when_body_is_meaningful() -> None:
    body = format_media_understanding_body(
        body="caption here",
        outputs=[
            {
                "kind": "audio.transcription",
                "attachment_index": 0,
                "text": "transcribed",
                "provider": "groq",
            },
        ],
    )
    assert body == "[Audio]\nUser text:\ncaption here\nTranscript:\ntranscribed"


def test_strips_leading_media_placeholders_from_user_text() -> None:
    body = format_media_understanding_body(
        body="<media:audio> caption here",
        outputs=[
            {
                "kind": "audio.transcription",
                "attachment_index": 0,
                "text": "transcribed",
                "provider": "groq",
            },
        ],
    )
    assert body == "[Audio]\nUser text:\ncaption here\nTranscript:\ntranscribed"


def test_strips_repeated_leading_media_placeholders_from_user_text() -> None:
    body = format_media_understanding_body(
        body="<media:image> <media:audio> caption here",
        outputs=[
            {
                "kind": "audio.transcription",
                "attachment_index": 0,
                "text": "transcribed",
                "provider": "groq",
            },
        ],
    )
    assert body == "[Audio]\nUser text:\ncaption here\nTranscript:\ntranscribed"


def test_treats_repeated_media_placeholders_without_captions_as_synthetic_text() -> None:
    body = format_media_understanding_body(
        body="<media:image> <media:audio>",
        outputs=[
            {
                "kind": "image.description",
                "attachment_index": 0,
                "text": "a chart",
                "provider": "openai",
            },
        ],
    )
    assert body == "[Image]\nDescription:\na chart"


def test_keeps_user_text_once_when_multiple_outputs_exist() -> None:
    body = format_media_understanding_body(
        body="caption here",
        outputs=[
            {
                "kind": "audio.transcription",
                "attachment_index": 0,
                "text": "audio text",
                "provider": "groq",
            },
            {
                "kind": "video.description",
                "attachment_index": 1,
                "text": "video text",
                "provider": "google",
            },
        ],
    )
    assert body == (
        "User text:\ncaption here\n\n"
        "[Audio]\nTranscript:\naudio text\n\n"
        "[Video]\nDescription:\nvideo text"
    )


def test_formats_image_outputs() -> None:
    body = format_media_understanding_body(
        body="<media:image>",
        outputs=[
            {
                "kind": "image.description",
                "attachment_index": 0,
                "text": "a cat",
                "provider": "openai",
            },
        ],
    )
    assert body == "[Image]\nDescription:\na cat"


def test_labels_audio_transcripts_by_attachment_order() -> None:
    body = format_media_understanding_body(
        outputs=[
            {
                "kind": "audio.transcription",
                "attachment_index": 0,
                "text": "first clip was silent",
                "provider": "openclaw",
            },
            {
                "kind": "audio.transcription",
                "attachment_index": 1,
                "text": "second clip has speech",
                "provider": "groq",
            },
        ],
    )
    assert body == (
        "[Audio 1/2]\nTranscript:\nfirst clip was silent\n\n"
        "[Audio 2/2]\nTranscript:\nsecond clip has speech"
    )
