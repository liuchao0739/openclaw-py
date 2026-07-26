"""Document Extract plugin module implements document extractor behavior."""

from __future__ import annotations

import asyncio
import base64
import importlib
from typing import Any

MAX_EXTRACTED_TEXT_CHARS = 200_000
MAX_RENDER_DIMENSION = 10_000

_pdf_engine_loader: asyncio.Task[Any] | None = None


async def _load_pdf_engine() -> Any:
    global _pdf_engine_loader
    if _pdf_engine_loader is None:

        async def _create_engine() -> Any:
            try:
                clawpdf = importlib.import_module("clawpdf")
                create_engine = clawpdf.create_engine
                engine = create_engine()
                if asyncio.iscoroutine(engine):
                    return await engine
                return engine
            except Exception as err:
                raise RuntimeError("Dependency clawpdf is required for PDF extraction") from err

        _pdf_engine_loader = asyncio.create_task(_create_engine())
        try:
            return await _pdf_engine_loader
        except Exception:
            _pdf_engine_loader = None
            raise
    return await _pdf_engine_loader


def _to_document_image(image: Any) -> dict[str, str]:
    image_bytes = image["bytes"] if isinstance(image, dict) else image.bytes
    mime_type = image["mimeType"] if isinstance(image, dict) else image.mimeType
    return {
        "type": "image",
        "data": base64.b64encode(bytes(image_bytes)).decode("ascii"),
        "mimeType": mime_type,
    }


def _is_pdf_password_error(err: BaseException) -> bool:
    return getattr(err, "code", None) == "password"


async def _open_pdf_document(
    *,
    engine: Any,
    input_data: bytes | bytearray | memoryview,
    password: str | None = None,
) -> Any:
    try:
        if password:
            return await engine.open(input_data, {"password": password})
        return await engine.open(input_data)
    except Exception as err:
        if _is_pdf_password_error(err):
            raise RuntimeError(
                "PDF requires a password or password is incorrect."
            ) from err
        raise


async def _extract_pdf_content(request: dict[str, Any]) -> dict[str, Any]:
    engine = await _load_pdf_engine()
    buffer = request["buffer"]
    if not isinstance(buffer, (bytes, bytearray, memoryview)):
        buffer = bytes(buffer)
    pdf = await _open_pdf_document(
        engine=engine,
        input_data=buffer,
        password=request.get("password"),
    )
    try:
        page_count = getattr(pdf, "pageCount", None)
        page_numbers = request.get("pageNumbers")
        max_pages = request["maxPages"]
        if page_numbers is not None:
            pages = [
                page
                for page in page_numbers
                if isinstance(page, int) and page_count is not None and 1 <= page <= page_count
            ][:max_pages]
        else:
            pages = None

        page_selection = {"pages": pages} if pages is not None else {"maxPages": max_pages}

        text_result = await pdf.extract(
            {
                "mode": "text",
                **page_selection,
                "maxTextChars": MAX_EXTRACTED_TEXT_CHARS,
            }
        )
        text = text_result["text"] if isinstance(text_result, dict) else text_result.text

        if len(text.strip()) >= request["minTextChars"]:
            return {"text": text, "images": []}

        if pages is not None:
            image_pages = pages
        else:
            image_pages = list(range(1, min(page_count or 0, max_pages) + 1))

        on_image_extraction_error = request.get("onImageExtractionError")
        try:
            images: list[dict[str, str]] = []
            remaining_pixels = request["maxPixels"]
            for index, page_number in enumerate(image_pages):
                if remaining_pixels <= 0:
                    break
                pages_remaining = len(image_pages) - index
                max_pixels_per_page = max(1, (remaining_pixels + pages_remaining - 1) // pages_remaining)
                image_result = await pdf.extract(
                    {
                        "mode": "images",
                        "pages": [page_number],
                        "image": {
                            "maxDimension": MAX_RENDER_DIMENSION,
                            "maxPixels": max_pixels_per_page,
                            "forms": True,
                        },
                    }
                )
                result_images = (
                    image_result["images"]
                    if isinstance(image_result, dict)
                    else image_result.images
                )
                for image in result_images:
                    images.append(_to_document_image(image))
                    width = image["width"] if isinstance(image, dict) else image.width
                    height = image["height"] if isinstance(image, dict) else image.height
                    remaining_pixels -= width * height
            return {"text": text, "images": images}
        except Exception as err:  # noqa: BLE001
            if callable(on_image_extraction_error):
                on_image_extraction_error(err)
            return {"text": text, "images": []}
    finally:
        destroy = pdf.destroy
        destroyed = destroy()
        if asyncio.iscoroutine(destroyed):
            await destroyed


def create_pdf_document_extractor() -> dict[str, Any]:
    return {
        "id": "pdf",
        "label": "PDF",
        "mimeTypes": ["application/pdf"],
        "autoDetectOrder": 10,
        "extract": _extract_pdf_content,
    }
