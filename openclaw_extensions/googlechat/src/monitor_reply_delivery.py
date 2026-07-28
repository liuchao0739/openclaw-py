from __future__ import annotations

from openclaw.plugin_sdk.reply_payload import (
    deliver_text_or_media_reply,
    resolve_sendable_outbound_reply_parts,
)
from openclaw_extensions.googlechat.src.api import (
    delete_google_chat_message,
    send_google_chat_message,
    update_google_chat_message,
    upload_google_chat_attachment,
)


async def deliver_google_chat_reply(params: dict) -> None:
    payload = params.get("payload", {})
    account = params["account"]
    space_id = params["spaceId"]
    runtime = params["runtime"]
    core = params["core"]
    status_sink = params.get("statusSink")
    typing_message_name = params.get("typingMessageName")

    reply = resolve_sendable_outbound_reply_parts(payload)
    media_count = reply.get("mediaCount", 0)
    has_media = reply.get("hasMedia", False)
    text = reply.get("text", "")
    first_text_chunk = True
    suppress_caption = False

    if has_media and typing_message_name:
        try:
            await delete_google_chat_message({
                "account": account,
                "messageName": typing_message_name,
            })
            typing_message_name = None
        except Exception as err:
            runtime.get("error", lambda m: None)(f"Google Chat typing cleanup failed: {err}")
            if typing_message_name:
                fallback_text = text if reply.get("hasText") else ("Sent attachments." if media_count > 1 else "Sent attachment.")
                try:
                    await update_google_chat_message({
                        "account": account,
                        "messageName": typing_message_name,
                        "text": fallback_text,
                    })
                    suppress_caption = bool((text or "").strip())
                except Exception as update_err:
                    runtime.get("error", lambda m: None)(f"Google Chat typing update failed: {update_err}")
                    typing_message_name = None

    chunk_limit = account.config.get("textChunkLimit", 4000)
    chunk_mode = core.channel.text.resolve_chunk_mode(params.get("config"), "googlechat", account.account_id)

    async def _send_text_message(chunk: str) -> None:
        await send_google_chat_message({
            "account": account,
            "space": space_id,
            "text": chunk,
            "thread": payload.get("replyToId"),
        })

    async def _send_text(chunk: str) -> None:
        nonlocal first_text_chunk, typing_message_name
        try:
            if first_text_chunk and typing_message_name:
                await update_google_chat_message({
                    "account": account,
                    "messageName": typing_message_name,
                    "text": chunk,
                })
            else:
                await _send_text_message(chunk)
            first_text_chunk = False
            if status_sink:
                status_sink({"lastOutboundAt": __import__("time").time() * 1000})
        except Exception as err:
            runtime.get("error", lambda m: None)(f"Google Chat message send failed: {err}")
            if first_text_chunk and typing_message_name:
                typing_message_name = None
                try:
                    await _send_text_message(chunk)
                    if status_sink:
                        status_sink({"lastOutboundAt": __import__("time").time() * 1000})
                except Exception as fallback_err:
                    runtime.get("error", lambda m: None)(f"Google Chat message fallback send failed: {fallback_err}")
                finally:
                    first_text_chunk = False

    async def _send_media(media_params: dict) -> None:
        media_url = media_params.get("mediaUrl")
        caption = media_params.get("caption", "")
        try:
            loaded = await core.channel.media.read_remote_media_buffer({
                "url": media_url,
                "maxBytes": (account.config.get("mediaMaxMb", 20)) * 1024 * 1024,
            })
            upload = await upload_google_chat_attachment({
                "account": account,
                "space": space_id,
                "buffer": loaded["buffer"],
                "contentType": loaded.get("contentType"),
                "filename": loaded.get("fileName", "attachment"),
            })
            if not upload.get("attachmentUploadToken"):
                raise RuntimeError("missing attachment upload token")
            await send_google_chat_message({
                "account": account,
                "space": space_id,
                "text": caption,
                "thread": payload.get("replyToId"),
                "attachments": [{
                    "attachmentUploadToken": upload["attachmentUploadToken"],
                    "contentName": loaded.get("fileName"),
                }],
            })
            if status_sink:
                status_sink({"lastOutboundAt": __import__("time").time() * 1000})
        except Exception as err:
            runtime.get("error", lambda m: None)(f"Google Chat attachment send failed: {err}")

    await deliver_text_or_media_reply(
        payload,
        text="" if suppress_caption else reply.get("text", ""),
        chunk_text=lambda value: core.channel.text.chunk_markdown_text_with_mode(value, chunk_limit, chunk_mode),
        send_text=_send_text,
        send_media=_send_media,
    )


__all__ = ["deliver_google_chat_reply"]