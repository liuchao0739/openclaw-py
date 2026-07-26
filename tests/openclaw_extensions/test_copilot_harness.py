"""Tests for GitHub Copilot agent harness."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from openclaw_extensions.copilot.harness import AggregateError, create_copilot_agent_harness
from openclaw_extensions.copilot.src.provider_bridge import COPILOT_BYOK_PROVIDER_ERROR

ATTEMPT_PARAMS = {"provider": "github-copilot", "model": "gpt-4.1"}
ATTEMPT_RESULT = {"ok": True}
TEST_SESSION_CONFIG = {
    "availableTools": [],
    "model": "gpt-4.1",
    "tools": [],
    "workingDirectory": "/workspace",
}


class AbortSignal:
    def __init__(self) -> None:
        self.aborted = False
        self.reason: Any = None
        self._listeners: list[Any] = []

    def add_event_listener(self, event: str, callback: Any, once: bool = False) -> None:
        if event != "abort":
            return
        self._listeners.append((callback, once))

    def _emit(self) -> None:
        for callback, _once in list(self._listeners):
            callback()


class AbortController:
    def __init__(self) -> None:
        self.signal = AbortSignal()

    def abort(self, reason: Any = None) -> None:
        self.signal.aborted = True
        self.signal.reason = reason
        self.signal._emit()


def make_pool_mock() -> MagicMock:
    pool = MagicMock()
    pool.acquire = AsyncMock()
    pool.release = AsyncMock()
    pool.dispose = AsyncMock(return_value=[])
    pool.size = MagicMock(return_value=0)
    return pool


def make_session_store_mock() -> dict[str, Any]:
    entries: dict[str, Any] = {}

    def register(key: str, value: dict[str, Any]) -> None:
        entries[key] = value

    def lookup(key: str) -> dict[str, Any] | None:
        return entries.get(key)

    def delete(key: str) -> bool:
        return entries.pop(key, None) is not None

    store = MagicMock()
    store.register = MagicMock(side_effect=register)
    store.lookup = MagicMock(side_effect=lookup)
    store.delete = MagicMock(side_effect=delete)
    return {"entries": entries, "store": store}


def create_deferred() -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    future: asyncio.Future[Any] = loop.create_future()

    def resolve(value: Any) -> None:
        if not future.done():
            future.set_result(value)

    def reject(reason: Any = None) -> None:
        if not future.done():
            future.set_exception(
                reason if isinstance(reason, BaseException) else Exception(str(reason))
            )

    return {"promise": future, "resolve": resolve, "reject": reject}


async def flush_async_work() -> None:
    await asyncio.sleep(0)


@pytest.fixture
def copilot_mocks(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    mocks: dict[str, Any] = {
        "run_copilot_attempt": AsyncMock(return_value=ATTEMPT_RESULT),
        "resolve_pool_acquire": MagicMock(
            return_value={
                "auth": {
                    "agentId": "test",
                    "authMode": "useLoggedInUser",
                    "copilotHome": "/tmp/copilot",
                },
                "key": {
                    "agentId": "test",
                    "authMode": "useLoggedInUser",
                    "copilotHome": "/tmp/copilot",
                },
                "options": {"copilotHome": "/tmp/copilot", "useLoggedInUser": True},
            }
        ),
        "create_copilot_byok_proxy": AsyncMock(return_value=None),
        "create_copilot_client_pool": MagicMock(return_value=make_pool_mock()),
    }

    import openclaw_extensions.copilot.src.attempt as attempt_mod
    import openclaw_extensions.copilot.src.byok_proxy as byok_proxy_mod
    import openclaw_extensions.copilot.src.runtime as runtime_mod

    monkeypatch.setattr(attempt_mod, "run_copilot_attempt", mocks["run_copilot_attempt"])
    monkeypatch.setattr(attempt_mod, "resolve_pool_acquire", mocks["resolve_pool_acquire"])
    monkeypatch.setattr(
        byok_proxy_mod, "create_copilot_byok_proxy", mocks["create_copilot_byok_proxy"]
    )
    monkeypatch.setattr(
        runtime_mod, "create_copilot_client_pool", mocks["create_copilot_client_pool"]
    )
    return mocks


def test_returns_the_copilot_id_and_default_label(copilot_mocks: dict[str, Any]) -> None:
    harness = create_copilot_agent_harness()
    assert harness["id"] == "copilot"
    assert harness["label"] == "GitHub Copilot agent runtime"


def test_accepts_custom_id_and_label_from_options(copilot_mocks: dict[str, Any]) -> None:
    harness = create_copilot_agent_harness({"id": "sdk", "label": "SDK Harness"})
    assert harness["id"] == "sdk"
    assert harness["label"] == "SDK Harness"


def test_supports_returns_false_in_auto_runtime_even_for_github_provider(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {"provider": "github-copilot", "modelId": "gpt-4.1", "requestedRuntime": "auto"}
    ) == {
        "supported": False,
        "reason": "copilot is opt-in only",
    }


def test_supports_returns_false_in_pi_runtime(copilot_mocks: dict[str, Any]) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {"provider": "github-copilot", "modelId": "gpt-4.1", "requestedRuntime": "pi"}
    ) == {
        "supported": False,
        "reason": "copilot is opt-in only",
    }


def test_supports_returns_true_for_requested_runtime_copilot_with_github_copilot_provider(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {"provider": "github-copilot", "modelId": "gpt-4.1", "requestedRuntime": "copilot"}
    ) == {"supported": True, "priority": 100}


def test_supports_normalizes_provider_casing_and_whitespace(copilot_mocks: dict[str, Any]) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {"provider": "  GitHub-Copilot  ", "modelId": "gpt-4.1", "requestedRuntime": "copilot"}
    ) == {"supported": True, "priority": 100}


def test_supports_normalizes_requested_runtime_casing(copilot_mocks: dict[str, Any]) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {"provider": "github-copilot", "modelId": "gpt-4.1", "requestedRuntime": "  COPILOT  "}
    ) == {"supported": True, "priority": 100}


def test_supports_custom_provider_ids_for_byok_model_entries(copilot_mocks: dict[str, Any]) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {
            "provider": "custom-proxy",
            "modelId": "llama-3.1-8b",
            "modelProvider": {"api": "openai-responses", "baseUrl": "https://proxy.example/v1"},
            "providerOwnerStatus": "unowned",
            "providerOwnerPluginIds": [],
            "requestedRuntime": "copilot",
        }
    ) == {"supported": True, "priority": 100}


def test_supports_rejects_custom_provider_ids_without_supported_byok_model_shape(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness()
    reason = (
        "provider is not a supported Copilot BYOK model "
        "(requires supported api, baseUrl, and no request transport policy overrides)"
    )
    assert harness["supports"](
        {
            "provider": "custom-proxy",
            "modelId": "llama-3.1-8b",
            "providerOwnerStatus": "unowned",
            "providerOwnerPluginIds": [],
            "requestedRuntime": "copilot",
        }
    ) == {"supported": False, "reason": reason}
    assert harness["supports"](
        {
            "provider": "custom-proxy",
            "modelId": "llama-3.1-8b",
            "modelProvider": {
                "api": "openai-responses",
                "baseUrl": "https://proxy.example/v1",
                "request": {"proxy": {"mode": "env-proxy"}},
            },
            "providerOwnerStatus": "unowned",
            "providerOwnerPluginIds": [],
            "requestedRuntime": "copilot",
        }
    ) == {"supported": False, "reason": reason}


@pytest.mark.parametrize(
    ("provider", "owner_plugin_ids"),
    [
        ("anthropic", ["anthropic"]),
        ("azure-openai-responses", ["openai"]),
        ("deepinfra", ["deepinfra"]),
        ("fireworks", ["fireworks"]),
        ("github", ["github"]),
        ("openclaw", ["openclaw"]),
        ("sglang", ["sglang"]),
        ("together", ["together"]),
        ("vllm", ["vllm"]),
    ],
)
def test_supports_rejects_manifest_owned_providers_outside_the_whitelist(
    copilot_mocks: dict[str, Any], provider: str, owner_plugin_ids: list[str]
) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {
            "provider": provider,
            "modelId": "gpt-4.1",
            "requestedRuntime": "copilot",
            "providerOwnerStatus": "owned",
            "providerOwnerPluginIds": owner_plugin_ids,
        }
    ) == {"supported": False, "reason": "provider is not one of: github-copilot"}


def test_supports_rejects_ambiguous_custom_provider_ownership(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness()
    assert harness["supports"](
        {
            "provider": "custom-proxy",
            "modelId": "proxy-model",
            "modelProvider": {"api": "openai-responses", "baseUrl": "https://proxy.example/v1"},
            "requestedRuntime": "copilot",
            "providerOwnerStatus": "ambiguous",
            "providerOwnerPluginIds": ["first-owner", "second-owner"],
        }
    ) == {"supported": False, "reason": "provider is not one of: github-copilot"}


@pytest.mark.asyncio
async def test_run_attempt_lazy_imports_attempt_by_waiting_until_invocation_to_create_a_pool(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    copilot_mocks["create_copilot_client_pool"].return_value = pool
    harness = create_copilot_agent_harness()
    assert copilot_mocks["create_copilot_client_pool"].call_count == 0
    assert copilot_mocks["run_copilot_attempt"].await_count == 0
    assert await harness["runAttempt"](ATTEMPT_PARAMS) == ATTEMPT_RESULT
    assert copilot_mocks["create_copilot_client_pool"].call_count == 1
    assert copilot_mocks["run_copilot_attempt"].await_count == 1


@pytest.mark.asyncio
async def test_keeps_invalid_byok_provider_configuration_on_the_structured_attempt_path(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    copilot_mocks["create_copilot_client_pool"].return_value = pool
    copilot_mocks["resolve_pool_acquire"].side_effect = [ValueError(COPILOT_BYOK_PROVIDER_ERROR)]
    harness = create_copilot_agent_harness()
    assert await harness["runAttempt"](ATTEMPT_PARAMS) == ATTEMPT_RESULT
    copilot_mocks["run_copilot_attempt"].assert_awaited_with(ATTEMPT_PARAMS, {"pool": pool})


@pytest.mark.asyncio
async def test_run_attempt_creates_one_pool_lazily_and_reuses_it_across_two_attempts_on_the_same_harness(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    first_result = {"attempt": 1}
    second_result = {"attempt": 2}
    copilot_mocks["create_copilot_client_pool"].return_value = pool
    copilot_mocks["run_copilot_attempt"].side_effect = [first_result, second_result]
    harness = create_copilot_agent_harness()
    assert await harness["runAttempt"](ATTEMPT_PARAMS) == first_result
    assert await harness["runAttempt"](ATTEMPT_PARAMS) == second_result
    assert copilot_mocks["create_copilot_client_pool"].call_count == 1
    assert copilot_mocks["run_copilot_attempt"].await_args_list[0].args[1]["pool"] == pool
    assert copilot_mocks["run_copilot_attempt"].await_args_list[1].args[1]["pool"] == pool


@pytest.mark.asyncio
async def test_multiple_harness_instances_create_independent_pools(
    copilot_mocks: dict[str, Any],
) -> None:
    pool_one = make_pool_mock()
    pool_two = make_pool_mock()
    copilot_mocks["create_copilot_client_pool"].side_effect = [pool_one, pool_two]
    first_harness = create_copilot_agent_harness()
    second_harness = create_copilot_agent_harness()
    assert await first_harness["runAttempt"](ATTEMPT_PARAMS) == ATTEMPT_RESULT
    assert await second_harness["runAttempt"](ATTEMPT_PARAMS) == ATTEMPT_RESULT
    assert copilot_mocks["create_copilot_client_pool"].call_count == 2
    assert copilot_mocks["run_copilot_attempt"].await_args_list[0].args[1]["pool"] == pool_one
    assert copilot_mocks["run_copilot_attempt"].await_args_list[1].args[1]["pool"] == pool_two


@pytest.mark.asyncio
async def test_run_attempt_does_not_serialize_concurrent_attempts(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    copilot_mocks["create_copilot_client_pool"].return_value = pool
    copilot_mocks["run_copilot_attempt"].side_effect = [{"attempt": 1}, {"attempt": 2}]
    harness = create_copilot_agent_harness()
    assert await harness["runAttempt"](ATTEMPT_PARAMS) == {"attempt": 1}
    assert await harness["runAttempt"](ATTEMPT_PARAMS) == {"attempt": 2}
    assert copilot_mocks["create_copilot_client_pool"].call_count == 1
    assert copilot_mocks["run_copilot_attempt"].await_count == 2


@pytest.mark.asyncio
async def test_dispose_before_first_run_attempt_does_not_create_a_pool(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness()
    await harness["dispose"]()
    assert copilot_mocks["create_copilot_client_pool"].call_count == 0


@pytest.mark.asyncio
async def test_dispose_during_lazy_startup_prevents_the_attempt_from_creating_a_pool(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness()

    async def slow_attempt(*_args: Any, **_kwargs: Any) -> Any:
        await asyncio.sleep(0.05)
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = slow_attempt
    attempt_task = asyncio.create_task(harness["runAttempt"](ATTEMPT_PARAMS))
    dispose_task = asyncio.create_task(harness["dispose"]())
    with pytest.raises(RuntimeError, match="harness was disposed while starting an attempt"):
        await attempt_task
    await dispose_task
    assert copilot_mocks["create_copilot_client_pool"].call_count == 0
    assert copilot_mocks["run_copilot_attempt"].await_count == 0


@pytest.mark.asyncio
async def test_dispose_after_pool_creation_calls_pool_dispose_once_even_when_called_twice(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    copilot_mocks["create_copilot_client_pool"].return_value = pool
    harness = create_copilot_agent_harness()
    await harness["runAttempt"](ATTEMPT_PARAMS)
    await harness["dispose"]()
    await harness["dispose"]()
    assert pool.dispose.await_count == 1


@pytest.mark.asyncio
async def test_dispose_waits_for_in_flight_run_attempt_before_disposing(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    deferred = create_deferred()
    copilot_mocks["create_copilot_client_pool"].return_value = pool

    async def deferred_attempt(*_a: Any, **_k: Any) -> Any:
        return await deferred["promise"]

    copilot_mocks["run_copilot_attempt"].side_effect = deferred_attempt
    harness = create_copilot_agent_harness()
    attempt_task = asyncio.create_task(harness["runAttempt"](ATTEMPT_PARAMS))
    await flush_async_work()
    dispose_task = asyncio.create_task(harness["dispose"]())
    await flush_async_work()
    assert pool.dispose.await_count == 0
    assert not dispose_task.done()
    deferred["resolve"](ATTEMPT_RESULT)
    assert await attempt_task == ATTEMPT_RESULT
    await dispose_task
    assert pool.dispose.await_count == 1


@pytest.mark.asyncio
async def test_run_attempt_after_dispose_rejects_without_creating_a_new_pool(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness()
    await harness["dispose"]()
    with pytest.raises(RuntimeError, match="harness has been disposed; cannot start new attempts"):
        await harness["runAttempt"](ATTEMPT_PARAMS)
    assert copilot_mocks["create_copilot_client_pool"].call_count == 0


@pytest.mark.asyncio
async def test_dispose_surfaces_pool_dispose_errors_as_aggregate_error(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    errors = [RuntimeError("first"), RuntimeError("second")]
    pool.dispose = AsyncMock(return_value=errors)
    copilot_mocks["create_copilot_client_pool"].return_value = pool
    harness = create_copilot_agent_harness()
    await harness["runAttempt"](ATTEMPT_PARAMS)
    with pytest.raises(AggregateError) as exc_info:
        await harness["dispose"]()
    assert str(exc_info.value) == "[copilot] pool disposal errors"
    assert exc_info.value.errors == errors


@pytest.mark.asyncio
async def test_dispose_does_not_dispose_a_caller_supplied_pool(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    harness = create_copilot_agent_harness({"pool": pool})
    await harness["runAttempt"](ATTEMPT_PARAMS)
    await harness["dispose"]()
    assert pool.dispose.await_count == 0


@pytest.mark.asyncio
async def test_uses_options_pool_when_supplied(copilot_mocks: dict[str, Any]) -> None:
    pool = make_pool_mock()
    harness = create_copilot_agent_harness({"pool": pool})
    assert await harness["runAttempt"](ATTEMPT_PARAMS) == ATTEMPT_RESULT
    assert copilot_mocks["create_copilot_client_pool"].call_count == 0
    assert copilot_mocks["run_copilot_attempt"].await_args.args[1]["pool"] == pool


@pytest.mark.asyncio
async def test_reset_is_a_no_op_when_params_session_id_is_missing(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["reset"]({})


@pytest.mark.asyncio
async def test_reset_is_a_no_op_when_the_session_was_never_tracked(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["reset"]({"sessionId": "unknown"})


@pytest.mark.asyncio
async def test_reset_calls_delete_session_on_the_client_that_created_the_session(
    copilot_mocks: dict[str, Any],
) -> None:
    pool = make_pool_mock()
    delete_session = AsyncMock()
    client = MagicMock(deleteSession=delete_session)

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {"sdkSessionId": "sdk-sess-123", "pooledClient": {"key": {}, "client": client}}
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness({"pool": pool})
    await harness["runAttempt"]({**ATTEMPT_PARAMS, "sessionId": "oc-sess-1"})
    await harness["reset"]({"sessionId": "oc-sess-1"})
    delete_session.assert_awaited_once_with("sdk-sess-123")


@pytest.mark.asyncio
async def test_reset_does_not_call_delete_session_when_no_sdk_session_id_was_reported(
    copilot_mocks: dict[str, Any],
) -> None:
    delete_session = AsyncMock()
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["runAttempt"]({**ATTEMPT_PARAMS, "sessionId": "oc-sess-2"})
    await harness["reset"]({"sessionId": "oc-sess-2"})
    delete_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_swallows_errors_thrown_by_client_delete_session(
    copilot_mocks: dict[str, Any],
) -> None:
    delete_session = AsyncMock(side_effect=RuntimeError("session not found"))
    client = MagicMock(deleteSession=delete_session)

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {"sdkSessionId": "sdk-sess-err", "pooledClient": {"key": {}, "client": client}}
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["runAttempt"]({**ATTEMPT_PARAMS, "sessionId": "oc-sess-3"})
    await harness["reset"]({"sessionId": "oc-sess-3"})
    delete_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_forgets_the_session_after_reset_second_reset_is_a_no_op(
    copilot_mocks: dict[str, Any],
) -> None:
    delete_session = AsyncMock()
    client = MagicMock(deleteSession=delete_session)

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {"sdkSessionId": "sdk-sess-x", "pooledClient": {"key": {}, "client": client}}
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["runAttempt"]({**ATTEMPT_PARAMS, "sessionId": "oc-sess-4"})
    await harness["reset"]({"sessionId": "oc-sess-4"})
    await harness["reset"]({"sessionId": "oc-sess-4"})
    delete_session.assert_awaited_once_with("sdk-sess-x")


@pytest.mark.asyncio
async def test_reset_does_not_invoke_delete_session_for_a_different_openclaw_session_id(
    copilot_mocks: dict[str, Any],
) -> None:
    delete_session = AsyncMock()
    client = MagicMock(deleteSession=delete_session)

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {"sdkSessionId": "sdk-sess-y", "pooledClient": {"key": {}, "client": client}}
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["runAttempt"]({**ATTEMPT_PARAMS, "sessionId": "oc-A"})
    await harness["reset"]({"sessionId": "oc-B"})
    delete_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispose_clears_tracked_sessions_so_subsequent_reset_is_a_no_op(
    copilot_mocks: dict[str, Any],
) -> None:
    delete_session = AsyncMock()
    client = MagicMock(deleteSession=delete_session)

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {"sdkSessionId": "sdk-sess-d", "pooledClient": {"key": {}, "client": client}}
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["runAttempt"]({**ATTEMPT_PARAMS, "sessionId": "oc-disp"})
    await harness["dispose"]()
    await harness["reset"]({"sessionId": "oc-disp"})
    delete_session.assert_not_awaited()


def make_attempt_params(**overrides: Any) -> dict[str, Any]:
    return {
        "provider": "github-copilot",
        "model": "gpt-4.1",
        "cwd": "/ws",
        "workspaceDir": "/ws",
        "agentDir": "/home",
        "copilotHome": "/copilot-home",
        "auth": {"useLoggedInUser": True},
        "sessionId": "oc-sess-reuse",
        **overrides,
    }


@pytest.mark.asyncio
async def test_seeds_initial_replay_state_sdk_session_id_from_tracked_sessions_on_the_second_turn(
    copilot_mocks: dict[str, Any],
) -> None:
    client = MagicMock(deleteSession=AsyncMock())

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {"sdkSessionId": "sdk-sess-warm", "pooledClient": {"key": {}, "client": client}}
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    await harness["runAttempt"](make_attempt_params(runId="t1"))
    await harness["runAttempt"](make_attempt_params(runId="t2"))
    second_params = copilot_mocks["run_copilot_attempt"].await_args_list[1].args[0]
    assert second_params["initialReplayState"]["sdkSessionId"] == "sdk-sess-warm"
    assert second_params["initialReplayState"].get("replayInvalid") is None


@pytest.mark.asyncio
async def test_compact_returns_ok_false_when_session_id_is_missing(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    assert await harness["compact"]({"workspaceDir": "/ws"}) == {
        "ok": False,
        "compacted": False,
        "reason": "missing-required-params",
    }


@pytest.mark.asyncio
async def test_compact_returns_ok_false_when_the_sdk_session_is_not_tracked(
    copilot_mocks: dict[str, Any],
) -> None:
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    assert await harness["compact"](
        {"sessionId": "oc-sess-compact-1", "trigger": "budget", "currentTokenCount": 12345}
    ) == {
        "ok": False,
        "compacted": False,
        "reason": "missing_thread_binding",
        "failure": {"reason": "missing_thread_binding"},
    }


def test_run_side_question_is_not_implemented(copilot_mocks: dict[str, Any]) -> None:
    harness = create_copilot_agent_harness({"pool": make_pool_mock()})
    assert "runSideQuestion" not in harness


def make_compact_params(**overrides: Any) -> dict[str, Any]:
    return {
        "provider": "github-copilot",
        "model": {"provider": "github-copilot", "id": "gpt-4.1"},
        "cwd": "/ws",
        "workspaceDir": "/ws",
        "agentDir": "/home",
        "copilotHome": "/copilot-home",
        "auth": {"useLoggedInUser": True},
        "sessionId": "oc-sess-compact",
        "sessionFile": "/session.json",
        **overrides,
    }


@pytest.mark.asyncio
async def test_compact_calls_sdk_history_compaction_rpc(
    copilot_mocks: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    before_compaction = AsyncMock()
    after_compaction = AsyncMock()
    hook_runner = MagicMock()
    hook_runner.has_hooks = lambda name: name in ("before_compaction", "after_compaction")
    hook_runner.run_before_compaction = before_compaction
    hook_runner.run_after_compaction = after_compaction
    monkeypatch.setattr(
        "openclaw.agents.harness.prompt_compaction_hook_helpers._get_global_hook_runner",
        lambda: hook_runner,
    )

    compact = AsyncMock(
        return_value={
            "success": True,
            "tokensRemoved": 123,
            "messagesRemoved": 4,
            "summaryContent": "compacted summary",
            "contextWindow": {"tokenLimit": 1000, "currentTokens": 777, "messagesLength": 12},
        }
    )
    disconnect = AsyncMock(side_effect=RuntimeError("disconnect failed"))
    resume_session = AsyncMock(
        return_value=MagicMock(
            disconnect=disconnect, rpc=MagicMock(history=MagicMock(compact=compact))
        )
    )
    pool = make_pool_mock()
    pool.acquire = AsyncMock(
        return_value={"key": {}, "client": MagicMock(resumeSession=resume_session)}
    )
    pool.release = AsyncMock()

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {
                "sdkSessionId": "sdk-sess-compact",
                "pooledClient": {"key": {}, "client": MagicMock(resumeSession=resume_session)},
                "sessionConfig": TEST_SESSION_CONFIG,
            }
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness({"pool": pool})
    await harness["runAttempt"](
        make_compact_params(
            agentId="main", sessionId="oc-sess-compact-1", sessionKey="agent:main:main"
        )
    )
    result = await harness["compact"](
        {
            **make_compact_params(sessionId="oc-sess-compact-1"),
            "model": "gpt-4.1",
            "sessionKey": "agent:main:main",
            "currentTokenCount": 900,
            "customInstructions": "Keep decisions.",
        }
    )

    resume_session.assert_awaited_once()
    compact.assert_awaited_once_with({"customInstructions": "Keep decisions."})
    disconnect.assert_awaited_once()
    pool.release.assert_awaited_once()
    assert result["ok"] is True
    assert result["compacted"] is True


@pytest.mark.asyncio
async def test_aborts_deferred_compaction_cleanup_before_disposal(
    copilot_mocks: dict[str, Any],
) -> None:
    cleanup = create_deferred()
    abort = MagicMock(side_effect=lambda: cleanup["resolve"]("aborted"))

    async def on_attempt(_params: Any, deps: dict[str, Any]) -> Any:
        deps["onSessionEstablished"](
            {
                "sdkSessionId": "sdk-sess-pending-cleanup",
                "pooledClient": {"key": {}, "client": MagicMock()},
                "sessionConfig": TEST_SESSION_CONFIG,
            }
        )
        deps["onDeferredCompaction"](
            {
                "abort": abort,
                "cleanup": cleanup["promise"],
                "sdkSessionId": "sdk-sess-pending-cleanup",
            }
        )
        return ATTEMPT_RESULT

    copilot_mocks["run_copilot_attempt"].side_effect = on_attempt
    harness = create_copilot_agent_harness()
    await harness["runAttempt"]({**ATTEMPT_PARAMS, "sessionId": "oc-pending-cleanup"})
    await harness["dispose"]()
    abort.assert_called_once()
