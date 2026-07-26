"""Tests for the PDF document extractor plugin."""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from openclaw_extensions.document_extract import document_extractor


def _request(**overrides: Any) -> dict[str, Any]:
    return {
        "buffer": b"%PDF-1.4",
        "mimeType": "application/pdf",
        "maxPages": 2,
        "maxPixels": 100,
        "minTextChars": 10,
        **overrides,
    }


@pytest.fixture(autouse=True)
def reset_pdf_engine_loader() -> None:
    document_extractor._pdf_engine_loader = None
    yield
    document_extractor._pdf_engine_loader = None


@pytest.fixture
def pdf_document() -> SimpleNamespace:
    return SimpleNamespace(
        pageCount=2,
        extract=AsyncMock(),
        destroy=MagicMock(),
    )


@pytest.fixture
def clawpdf_mocks(
    monkeypatch: pytest.MonkeyPatch,
    pdf_document: SimpleNamespace,
) -> tuple[AsyncMock, AsyncMock]:
    create_engine_mock = AsyncMock()
    open_pdf_mock = AsyncMock(return_value=pdf_document)

    async def _create_engine() -> SimpleNamespace:
        return SimpleNamespace(open=open_pdf_mock)

    create_engine_mock.side_effect = _create_engine

    original_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> Any:
        if name == "clawpdf":
            return SimpleNamespace(create_engine=create_engine_mock)
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    return create_engine_mock, open_pdf_mock


@pytest.mark.asyncio
async def test_declares_pdf_support(clawpdf_mocks: tuple[AsyncMock, AsyncMock]) -> None:
    extractor = document_extractor.create_pdf_document_extractor()
    extract = extractor.pop("extract")

    assert callable(extract)
    assert extractor == {
        "id": "pdf",
        "label": "PDF",
        "mimeTypes": ["application/pdf"],
        "autoDetectOrder": 10,
    }


@pytest.mark.asyncio
async def test_extracts_text_first_and_renders_each_fallback_page_with_its_own_pixel_budget(
    clawpdf_mocks: tuple[AsyncMock, AsyncMock],
    pdf_document: SimpleNamespace,
) -> None:
    _, open_pdf_mock = clawpdf_mocks
    pdf_document.extract.side_effect = [
        {"text": "", "images": []},
        {
            "text": "",
            "images": [
                {
                    "type": "image",
                    "bytes": b"png1",
                    "mimeType": "image/png",
                    "page": 1,
                    "width": 5,
                    "height": 10,
                }
            ],
        },
        {
            "text": "",
            "images": [
                {
                    "type": "image",
                    "bytes": b"png2",
                    "mimeType": "image/png",
                    "page": 2,
                    "width": 5,
                    "height": 10,
                }
            ],
        },
    ]
    extractor = document_extractor.create_pdf_document_extractor()

    result = await extractor["extract"](_request())

    assert result is not None
    open_pdf_mock.assert_awaited_once()
    open_args = open_pdf_mock.await_args.args
    assert isinstance(open_args[0], (bytes, bytearray, memoryview))
    pdf_document.extract.assert_any_await(
        {
            "mode": "text",
            "maxPages": 2,
            "maxTextChars": 200_000,
        }
    )
    pdf_document.extract.assert_any_await(
        {
            "mode": "images",
            "pages": [1],
            "image": {"maxDimension": 10_000, "maxPixels": 50, "forms": True},
        }
    )
    pdf_document.extract.assert_any_await(
        {
            "mode": "images",
            "pages": [2],
            "image": {"maxDimension": 10_000, "maxPixels": 50, "forms": True},
        }
    )
    assert result == {
        "text": "",
        "images": [
            {"type": "image", "data": "cG5nMQ==", "mimeType": "image/png"},
            {"type": "image", "data": "cG5nMg==", "mimeType": "image/png"},
        ],
    }
    pdf_document.destroy.assert_called_once()


@pytest.mark.asyncio
async def test_skips_image_fallback_when_enough_text_is_extracted(
    clawpdf_mocks: tuple[AsyncMock, AsyncMock],
    pdf_document: SimpleNamespace,
) -> None:
    pdf_document.extract.return_value = {"text": "enough text", "images": []}
    extractor = document_extractor.create_pdf_document_extractor()

    result = await extractor["extract"](_request(minTextChars=5))

    assert result == {"text": "enough text", "images": []}
    pdf_document.extract.assert_awaited_once()
    pdf_document.destroy.assert_called_once()


@pytest.mark.asyncio
async def test_opens_encrypted_pdfs_with_the_request_password(
    clawpdf_mocks: tuple[AsyncMock, AsyncMock],
    pdf_document: SimpleNamespace,
) -> None:
    _, open_pdf_mock = clawpdf_mocks
    pdf_document.extract.return_value = {"text": "enough text", "images": []}
    extractor = document_extractor.create_pdf_document_extractor()

    await extractor["extract"](_request(password="secret"))

    open_pdf_mock.assert_awaited_once()
    open_args = open_pdf_mock.await_args.args
    assert isinstance(open_args[0], (bytes, bytearray, memoryview))
    assert open_args[1] == {"password": "secret"}
    pdf_document.destroy.assert_called_once()


@pytest.mark.asyncio
async def test_normalizes_clawpdf_password_errors(
    clawpdf_mocks: tuple[AsyncMock, AsyncMock],
    pdf_document: SimpleNamespace,
) -> None:
    _, open_pdf_mock = clawpdf_mocks
    password_error = RuntimeError("bad password")
    password_error.code = "password"  # type: ignore[attr-defined]
    open_pdf_mock.side_effect = password_error
    extractor = document_extractor.create_pdf_document_extractor()

    with pytest.raises(RuntimeError, match="PDF requires a password or password is incorrect."):
        await extractor["extract"](_request(password="wrong"))

    pdf_document.destroy.assert_not_called()


@pytest.mark.asyncio
async def test_filters_selected_pages_and_renders_them_one_page_per_image_call(
    clawpdf_mocks: tuple[AsyncMock, AsyncMock],
    pdf_document: SimpleNamespace,
) -> None:
    pdf_document.extract.side_effect = [
        {"text": "", "images": []},
        {"text": "", "images": []},
        {"text": "", "images": []},
    ]
    extractor = document_extractor.create_pdf_document_extractor()

    await extractor["extract"](_request(pageNumbers=[3, 2, 0, 1], maxPages=2))

    assert pdf_document.extract.await_args_list[0].args[0] == {
        "mode": "text",
        "pages": [2, 1],
        "maxTextChars": 200_000,
    }
    assert pdf_document.extract.await_args_list[1].args[0] == {
        "mode": "images",
        "pages": [2],
        "image": {"maxDimension": 10_000, "maxPixels": 50, "forms": True},
    }
    assert pdf_document.extract.await_args_list[2].args[0]["mode"] == "images"
    assert pdf_document.extract.await_args_list[2].args[0]["pages"] == [1]


@pytest.mark.asyncio
async def test_reports_image_fallback_failures_and_returns_extracted_text(
    clawpdf_mocks: tuple[AsyncMock, AsyncMock],
    pdf_document: SimpleNamespace,
) -> None:
    on_image_extraction_error = MagicMock()
    failure = RuntimeError("render failed")
    pdf_document.extract.side_effect = [
        {"text": "short", "images": []},
        failure,
    ]
    extractor = document_extractor.create_pdf_document_extractor()

    result = await extractor["extract"](_request(onImageExtractionError=on_image_extraction_error))

    assert result == {"text": "short", "images": []}
    on_image_extraction_error.assert_called_once_with(failure)
    pdf_document.destroy.assert_called_once()
