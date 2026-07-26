"""Tests for ACPX doctor state migration."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from openclaw_extensions.acpx.doctor_contract_api import state_migrations
from openclaw_extensions.acpx.src.process_lease import open_acpx_process_lease_state_store
from openclaw_extensions.acpx.src.state import (
    ACPX_GATEWAY_INSTANCE_KEY,
    ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
    ACPX_GATEWAY_INSTANCE_NAMESPACE,
    ACPX_LEGACY_GATEWAY_INSTANCE_FILE,
    ACPX_LEGACY_PROCESS_LEASE_FILE,
)
from tests.openclaw_extensions.acpx_test_support import (
    create_plugin_state_keyed_store_for_tests,
    reset_plugin_state_store_for_tests,
)


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    reset_plugin_state_store_for_tests()
    return tmp_path


@pytest.fixture
def env(state_dir: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    test_env = {**os.environ, "OPENCLAW_STATE_DIR": str(state_dir)}
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(state_dir))
    return test_env


def _create_doctor_context(env: dict[str, str]) -> dict:
    def open_plugin_state_keyed_store(options: dict):
        return create_plugin_state_keyed_store_for_tests("acpx", {**options, "env": env})

    return {"open_plugin_state_keyed_store": open_plugin_state_keyed_store}


def _migration_params(state_dir: Path, env: dict[str, str]) -> dict:
    return {
        "config": {},
        "env": env,
        "state_dir": str(state_dir),
        "oauth_dir": str(state_dir / "oauth"),
        "context": _create_doctor_context(env),
    }


@pytest.mark.asyncio
async def test_imports_legacy_gateway_identity_and_open_process_leases(
    state_dir: Path, env: dict[str, str]
):
    gateway_path = state_dir / ACPX_LEGACY_GATEWAY_INSTANCE_FILE
    lease_path = state_dir / "acpx" / ACPX_LEGACY_PROCESS_LEASE_FILE
    lease = {
        "leaseId": "lease-1",
        "gatewayInstanceId": "gw-test",
        "sessionKey": "agent:codex:acp:test",
        "wrapperRoot": str(state_dir / "acpx"),
        "wrapperPath": str(state_dir / "acpx" / "codex-acp-wrapper.mjs"),
        "rootPid": 101,
        "commandHash": "hash",
        "startedAt": 1,
        "state": "open",
    }
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    gateway_path.write_text("gw-test\n", encoding="utf-8")
    lease_path.write_text(
        json.dumps(
            {
                "version": 1,
                "leases": [
                    lease,
                    {**lease, "leaseId": "closed-lease", "state": "closed"},
                ],
            }
        ),
        encoding="utf-8",
    )

    migration = state_migrations[0]
    detection = await migration["detect_legacy_state"](_migration_params(state_dir, env))
    assert detection is not None
    assert any("ACPX gateway instance id" in line for line in detection["preview"])
    assert any("1 open lease" in line for line in detection["preview"])

    result = await migration["migrate_legacy_state"](_migration_params(state_dir, env))

    assert result["warnings"] == []
    assert result["changes"][0] == "Migrated ACPX gateway instance id -> plugin state"
    assert "Archived ACPX gateway-instance-id legacy source" in result["changes"][1]
    assert result["changes"][2] == (
        "Migrated ACPX process leases -> plugin state (1 imported, 0 already present)"
    )
    assert "Archived ACPX process-leases legacy source" in result["changes"][3]
    assert not gateway_path.exists()
    assert Path(f"{gateway_path}.migrated").exists()
    assert not lease_path.exists()
    assert Path(f"{lease_path}.migrated").exists()

    gateway_store = _create_doctor_context(env)["open_plugin_state_keyed_store"](
        {
            "namespace": ACPX_GATEWAY_INSTANCE_NAMESPACE,
            "maxEntries": ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
        }
    )
    gateway_record = await gateway_store.lookup(ACPX_GATEWAY_INSTANCE_KEY)
    assert gateway_record is not None
    assert gateway_record["instanceId"] == "gw-test"
    lease_store = open_acpx_process_lease_state_store(
        _create_doctor_context(env)["open_plugin_state_keyed_store"]
    )
    assert await lease_store.lookup("lease-1") == lease
    assert await lease_store.lookup("closed-lease") is None


@pytest.mark.asyncio
async def test_ignores_legacy_process_lease_files_without_open_cleanup_work(
    state_dir: Path,
    env: dict[str, str],
):
    lease_path = state_dir / "acpx" / ACPX_LEGACY_PROCESS_LEASE_FILE
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    lease_path.write_text(
        json.dumps(
            {
                "version": 1,
                "leases": [
                    {
                        "leaseId": "closed-lease",
                        "gatewayInstanceId": "gw-test",
                        "sessionKey": "agent:codex:acp:test",
                        "wrapperRoot": str(state_dir / "acpx"),
                        "wrapperPath": str(state_dir / "acpx" / "codex-acp-wrapper.mjs"),
                        "rootPid": 101,
                        "commandHash": "hash",
                        "startedAt": 1,
                        "state": "closed",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    migration = state_migrations[0]
    assert await migration["detect_legacy_state"](_migration_params(state_dir, env)) is None
    assert await migration["migrate_legacy_state"](_migration_params(state_dir, env)) == {
        "changes": [],
        "warnings": [],
    }
    assert lease_path.exists()


@pytest.mark.asyncio
async def test_leaves_legacy_leases_when_canonical_gateway_id_would_not_reap(
    state_dir: Path,
    env: dict[str, str],
):
    gateway_path = state_dir / ACPX_LEGACY_GATEWAY_INSTANCE_FILE
    lease_path = state_dir / "acpx" / ACPX_LEGACY_PROCESS_LEASE_FILE
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    gateway_path.write_text("legacy-gw\n", encoding="utf-8")
    lease_path.write_text(
        json.dumps(
            {
                "version": 1,
                "leases": [
                    {
                        "leaseId": "lease-1",
                        "gatewayInstanceId": "legacy-gw",
                        "sessionKey": "agent:codex:acp:test",
                        "wrapperRoot": str(state_dir / "acpx"),
                        "wrapperPath": str(state_dir / "acpx" / "codex-acp-wrapper.mjs"),
                        "rootPid": 101,
                        "commandHash": "hash",
                        "startedAt": 1,
                        "state": "open",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    context = _create_doctor_context(env)
    await context["open_plugin_state_keyed_store"](
        {
            "namespace": ACPX_GATEWAY_INSTANCE_NAMESPACE,
            "maxEntries": ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
        }
    ).register(
        ACPX_GATEWAY_INSTANCE_KEY,
        {"instanceId": "current-gw", "createdAt": 2},
    )
    await open_acpx_process_lease_state_store(context["open_plugin_state_keyed_store"]).register(
        "current-lease",
        {
            "leaseId": "current-lease",
            "gatewayInstanceId": "current-gw",
            "sessionKey": "agent:codex:acp:current",
            "wrapperRoot": str(state_dir / "acpx"),
            "wrapperPath": str(state_dir / "acpx" / "codex-acp-wrapper.mjs"),
            "rootPid": 202,
            "commandHash": "hash-current",
            "startedAt": 2,
            "state": "open",
        },
    )

    result = await state_migrations[0]["migrate_legacy_state"](_migration_params(state_dir, env))

    assert result["changes"] == []
    assert result["warnings"] == [
        (
            "Skipped ACPX process lease migration because legacy leases do not match "
            "the canonical gateway instance id; left legacy sources in place for manual cleanup"
        )
    ]
    assert gateway_path.exists()
    assert lease_path.exists()
    assert (
        await open_acpx_process_lease_state_store(context["open_plugin_state_keyed_store"]).lookup(
            "lease-1"
        )
        is None
    )


@pytest.mark.asyncio
async def test_adopts_legacy_gateway_id_when_upgraded_startup_created_empty_sqlite_id(
    state_dir: Path,
    env: dict[str, str],
):
    gateway_path = state_dir / ACPX_LEGACY_GATEWAY_INSTANCE_FILE
    lease_path = state_dir / "acpx" / ACPX_LEGACY_PROCESS_LEASE_FILE
    legacy_lease = {
        "leaseId": "legacy-lease",
        "gatewayInstanceId": "legacy-gw",
        "sessionKey": "agent:codex:acp:test",
        "wrapperRoot": str(state_dir / "acpx"),
        "wrapperPath": str(state_dir / "acpx" / "codex-acp-wrapper.mjs"),
        "rootPid": 101,
        "commandHash": "hash",
        "startedAt": 1,
        "state": "open",
    }
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    gateway_path.write_text("legacy-gw\n", encoding="utf-8")
    lease_path.write_text(
        json.dumps({"version": 1, "leases": [legacy_lease]}),
        encoding="utf-8",
    )
    context = _create_doctor_context(env)
    await context["open_plugin_state_keyed_store"](
        {
            "namespace": ACPX_GATEWAY_INSTANCE_NAMESPACE,
            "maxEntries": ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
        }
    ).register(
        ACPX_GATEWAY_INSTANCE_KEY,
        {"instanceId": "fresh-empty-gw", "createdAt": 2},
    )

    result = await state_migrations[0]["migrate_legacy_state"](_migration_params(state_dir, env))

    assert result["warnings"] == []
    assert result["changes"][0] == "Migrated ACPX gateway instance id -> plugin state"
    assert "Archived ACPX gateway-instance-id legacy source" in result["changes"][1]
    assert result["changes"][2] == (
        "Migrated ACPX process leases -> plugin state (1 imported, 0 already present)"
    )
    gateway_store = context["open_plugin_state_keyed_store"](
        {
            "namespace": ACPX_GATEWAY_INSTANCE_NAMESPACE,
            "maxEntries": ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
        }
    )
    assert (await gateway_store.lookup(ACPX_GATEWAY_INSTANCE_KEY))["instanceId"] == "legacy-gw"
    assert (
        await open_acpx_process_lease_state_store(context["open_plugin_state_keyed_store"]).lookup(
            "legacy-lease"
        )
        == legacy_lease
    )
