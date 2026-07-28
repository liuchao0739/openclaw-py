from typing import Dict, Optional
import os
import base64


def renderQrPngBase64(text: str) -> str:
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        import io
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except ImportError:
        raise RuntimeError("qrcode package not installed")


def renderQrPngDataUrl(text: str) -> str:
    base64_data = renderQrPngBase64(text)
    return f"data:image/png;base64,{base64_data}"


def writeQrPngTempFile(text: str, params: Dict) -> Dict:
    tmp_root = params.get("tmpRoot", "/tmp")
    dir_prefix = params.get("dirPrefix", "device-pair-qr-")
    file_name = params.get("fileName", "pair-qr.png")

    import tempfile
    with tempfile.TemporaryDirectory(prefix=dir_prefix, dir=tmp_root) as tmp_dir:
        file_path = os.path.join(tmp_dir, file_name)
        base64_data = renderQrPngBase64(text)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_data))
        return {"filePath": file_path}

__all__ = ["renderQrPngBase64", "renderQrPngDataUrl", "writeQrPngTempFile"]