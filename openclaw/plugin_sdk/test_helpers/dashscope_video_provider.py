"""Dashscope video provider test helpers mock video provider runtime behavior.

Mirrors src/plugin-sdk/test-helpers/dashscope-video-provider.ts.
"""

from __future__ import annotations

from typing import Any, ClassVar


def mock_successful_dashscope_video_task(
    mocks: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> None:
    """Mock a successful DashScope async video generation task lifecycle."""
    options = params or {}
    request_id = options.get("requestId", "req-1")
    task_id = options.get("taskId", "task-1")
    task_status = options.get("taskStatus", "SUCCEEDED")
    video_url = options.get("videoUrl", "https://example.com/out.mp4")

    class _SubmitResponse:
        ok = True

        async def json(self) -> dict[str, Any]:
            return {
                "request_id": request_id,
                "output": {"task_id": task_id},
            }

    async def _release() -> None:
        return None

    mocks["postJsonRequestMock"].return_value = {
        "response": _SubmitResponse(),
        "release": _release,
    }

    class _PollResponse:
        headers: ClassVar[dict[str, str]] = {}

        async def json(self) -> dict[str, Any]:
            return {
                "output": {
                    "task_status": task_status,
                    "results": [{"video_url": video_url}],
                }
            }

    class _DownloadResponse:
        headers: ClassVar[dict[str, str]] = {"content-type": "video/mp4"}

        async def aread(self) -> bytes:
            return b"mp4-bytes"

    mocks["fetchWithTimeoutMock"].side_effect = [_PollResponse(), _DownloadResponse()]


def expect_dashscope_video_task_poll(
    fetch_with_timeout_mock: Any,
    params: dict[str, Any] | None = None,
) -> None:
    """Assert the DashScope task poll used the expected URL and timeout."""
    options = params or {}
    base_url = options.get("baseUrl", "https://dashscope-intl.aliyuncs.com")
    task_id = options.get("taskId", "task-1")
    timeout_ms = options.get("timeoutMs", 120_000)
    assert fetch_with_timeout_mock.call_count >= 1
    first_call = fetch_with_timeout_mock.call_args_list[0]
    assert first_call.args[0] == f"{base_url}/api/v1/tasks/{task_id}"
    assert first_call.args[1]["method"] == "GET"
    assert first_call.args[2] == timeout_ms


def expect_successful_dashscope_video_result(
    result: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> None:
    """Assert a DashScope video generation result matches the mocked task output."""
    options = params or {}
    request_id = options.get("requestId", "req-1")
    task_id = options.get("taskId", "task-1")
    task_status = options.get("taskStatus", "SUCCEEDED")
    videos = result.get("videos") or []
    assert len(videos) == 1
    assert videos[0].get("mimeType") == "video/mp4"
    metadata = result.get("metadata") or {}
    assert metadata.get("requestId") == request_id
    assert metadata.get("taskId") == task_id
    assert metadata.get("taskStatus") == task_status
