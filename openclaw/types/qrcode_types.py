from typing import Any, Callable, Dict, List, Literal, Optional, Union


QrCodeErrorCorrectionLevel = Literal["L", "M", "Q", "H", "low", "medium", "quartile", "high"]


class QrCodeColorOptions:
    dark: Optional[str]
    light: Optional[str]


class QrCodeRenderOptions:
    color: Optional[QrCodeColorOptions]
    error_correction_level: Optional[QrCodeErrorCorrectionLevel]
    margin: Optional[int]
    scale: Optional[int]
    small: Optional[bool]
    type: Optional[Literal["image/png", "png", "svg", "terminal", "utf8"]]
    width: Optional[int]


class QrCodeSymbol:
    modules: "_QrCodeModules"


class _QrCodeModules:
    data: Any
    size: int


def create(text: str, options: Optional[QrCodeRenderOptions] = None) -> QrCodeSymbol:
    ...


async def toString(text: str, options: Optional[QrCodeRenderOptions] = None) -> str:
    ...


async def toDataURL(text: str, options: Optional[QrCodeRenderOptions] = None) -> str:
    ...


async def toFile(file_path: str, text: str, options: Optional[QrCodeRenderOptions] = None) -> None:
    ...


class _QrCodeModule:
    create: Callable[..., QrCodeSymbol]
    toString: Callable[..., Awaitable[str]]
    toDataURL: Callable[..., Awaitable[str]]
    toFile: Callable[..., Awaitable[None]]


qrcode = _QrCodeModule()
