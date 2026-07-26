"""Tests for plugins/compat registry — mirrors registry.test.ts."""

from __future__ import annotations

import re
import subprocess
from calendar import monthrange
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from openclaw.plugins.compat.registry import (
    get_plugin_compat_record,
    is_plugin_compat_code,
    list_deprecated_plugin_compat_records,
    list_plugin_compat_records,
)

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_ROOTS_FOR_DEPRECATED_CALL_GUARD = (
    "src",
    "extensions",
    "packages",
    "test",
    "scripts",
)
DEPRECATED_TARGET_PARSER_CALL_PATTERN = re.compile(
    r"\.parseExplicitTarget\?\.\s*\(|"
    r"parseExplicitTargetFor(?:Channel|LoadedChannel)\s*\(|"
    r"resolveRouteTargetFor(?:Channel|LoadedChannel)\s*\(",
)
DEPRECATED_TARGET_PARSER_COMPAT_FILES = frozenset(
    {
        "src/auto-reply/reply/group-id.ts",
        "src/channels/plugins/target-parsing-loaded.ts",
        "src/channels/plugins/target-parsing.test.ts",
        "src/infra/outbound/outbound-session.ts",
        "src/infra/outbound/outbound-session.test-helpers.ts",
        "src/plugins/compat/registry.test.ts",
    }
)

KNOWN_DEPRECATED_SURFACE_MARKERS = (
    {
        "code": "legacy-extension-api-import",
        "file": "src/extensionAPI.ts",
        "marker": "openclaw/extension-api is deprecated",
    },
    {
        "code": "memory-split-registration",
        "file": "src/plugins/memory-state.ts",
        "marker": "registerMemoryPromptSection",
    },
    {
        "code": "provider-static-capabilities-bag",
        "file": "src/plugins/types.ts",
        "marker": "Legacy static provider capability bag",
    },
    {
        "code": "provider-discovery-type-aliases",
        "file": "src/plugins/types.ts",
        "marker": "ProviderPluginDiscovery = ProviderPluginCatalog",
    },
    {
        "code": "provider-thinking-policy-hooks",
        "file": "src/plugins/types.ts",
        "marker": "Prefer `resolveThinkingProfile`",
    },
    {
        "code": "provider-external-oauth-profiles-hook",
        "file": "src/plugins/types.ts",
        "marker": "resolveExternalOAuthProfiles",
    },
    {
        "code": "agent-tool-result-harness-alias",
        "file": "src/plugins/agent-tool-result-middleware-types.ts",
        "marker": "AgentToolResultMiddlewareHarness",
    },
    {
        "code": "embedded-pi-agent-sdk-aliases",
        "file": "src/plugins/runtime/types-core.ts",
        "marker": "runEmbeddedPiAgent",
    },
    {
        "code": "runtime-config-load-write",
        "file": "src/plugins/runtime/runtime-config.ts",
        "marker": "RUNTIME_CONFIG_LOAD_WRITE_COMPAT_CODE",
    },
    {
        "code": "runtime-taskflow-legacy-alias",
        "file": "src/plugins/runtime/types-core.ts",
        "marker": "taskFlow",
    },
    {
        "code": "runtime-subagent-get-session-alias",
        "file": "src/plugins/runtime/types.ts",
        "marker": "getSessionMessages",
    },
    {
        "code": "runtime-stt-alias",
        "file": "src/plugins/runtime/types-core.ts",
        "marker": "stt",
    },
    {
        "code": "runtime-inbound-envelope-alias",
        "file": "src/plugins/runtime/types-channel.ts",
        "marker": "formatInboundEnvelope",
    },
    {
        "code": "channel-native-message-schema-helpers",
        "file": "src/plugin-sdk/channel-actions.ts",
        "marker": "createMessageToolButtonsSchema",
    },
    {
        "code": "channel-mention-gating-legacy-helpers",
        "file": "src/plugin-sdk/channel-inbound.ts",
        "marker": "resolveMentionGatingWithBypass",
    },
    {
        "code": "provider-web-search-core-wrapper",
        "file": "src/plugin-sdk/provider-web-search.ts",
        "marker": "createPluginBackedWebSearchProvider",
    },
    {
        "code": "approval-capability-approvals-alias",
        "file": "src/plugin-sdk/approval-delivery-helpers.ts",
        "marker": "approvals?: Partial<ChannelApprovalCapabilitySurfaces>",
    },
    {
        "code": "plugin-sdk-test-utils-alias",
        "file": "src/plugin-sdk/test-utils.ts",
        "marker": "focused `openclaw/plugin-sdk/*` test subpaths",
    },
    {
        "code": "plugin-install-config-ledger",
        "file": "src/config/plugin-install-config-migration.ts",
        "marker": "stripShippedPluginInstallConfigRecords",
    },
    {
        "code": "bundled-plugin-load-path-aliases",
        "file": "src/commands/doctor/shared/bundled-plugin-load-paths.ts",
        "marker": "plugins.load.paths",
    },
    {
        "code": "plugin-owned-web-search-config",
        "file": "src/commands/doctor/shared/legacy-web-search-migrate.ts",
        "marker": "tools.web.search",
    },
    {
        "code": "plugin-owned-web-fetch-config",
        "file": "src/commands/doctor/shared/legacy-web-fetch-migrate.ts",
        "marker": "tools.web.fetch.firecrawl",
    },
    {
        "code": "plugin-owned-x-search-config",
        "file": "src/commands/doctor/shared/legacy-x-search-migrate.ts",
        "marker": "tools.web.x_search",
    },
    {
        "code": "bundled-channel-config-schema-legacy",
        "file": "src/plugin-sdk/channel-config-schema-legacy.ts",
        "marker": "Compatibility surface for bundled channel schemas",
    },
    {
        "code": "plugin-sdk-testing-barrel",
        "file": "src/plugin-sdk/testing.ts",
        "marker": "@deprecated Broad compatibility barrel",
    },
    {
        "code": "legacy-root-sdk-import",
        "file": "src/plugin-sdk/compat.ts",
        "marker": "@deprecated Use `openclaw/plugin-sdk/channel-outbound`.",
    },
    {
        "code": "legacy-deactivate-hook-alias",
        "file": "src/plugins/hook-types.ts",
        "marker": "@deprecated Use gateway_stop",
    },
    {
        "code": "legacy-subagent-spawning-hook",
        "file": "src/plugins/hook-types.ts",
        "marker": "@deprecated Core prepares thread-bound subagent bindings",
    },
    {
        "code": "deprecated-memory-embedding-provider-api",
        "file": "src/plugins/types.ts",
        "marker": "registerMemoryEmbeddingProvider",
    },
    {
        "code": "channel-route-key-aliases",
        "file": "src/plugin-sdk/channel-route.ts",
        "marker": "channelRouteIdentityKey",
    },
    {
        "code": "channel-target-comparable-aliases",
        "file": "src/channels/plugins/target-parsing-loaded.ts",
        "marker": "ComparableChannelTarget",
    },
    {
        "code": "channel-explicit-target-parser",
        "file": "src/channels/plugins/types.core.ts",
        "marker": "parseExplicitTarget?:",
    },
    {
        "code": "channel-explicit-target-parser",
        "file": "src/plugin-sdk/channel-route.ts",
        "marker": "resolveChannelRouteTargetWithParser",
    },
    {
        "code": "channel-explicit-target-parser",
        "file": "src/channels/plugins/target-parsing-loaded.ts",
        "marker": "ParsedChannelExplicitTarget",
    },
    {
        "code": "channel-explicit-target-parser",
        "file": "src/channels/plugins/target-parsing-loaded.ts",
        "marker": "parseExplicitTargetForLoadedChannel",
    },
    {
        "code": "channel-explicit-target-parser",
        "file": "src/channels/plugins/target-parsing-loaded.ts",
        "marker": "resolveRouteTargetForLoadedChannel",
    },
    {
        "code": "channel-messaging-targets-subpath",
        "file": "src/plugin-sdk/messaging-targets.ts",
        "marker": "openclaw/plugin-sdk/channel-targets",
    },
    {
        "code": "whatsapp-web-inbound-flat-message-aliases",
        "file": "extensions/whatsapp/src/inbound/types.ts",
        "marker": "DeprecatedWebInboundMessageFlatAliases",
    },
    {
        "code": "whatsapp-web-inbound-admission-top-level-fields",
        "file": "extensions/whatsapp/src/inbound/types.ts",
        "marker": "DeprecatedWebInboundAdmissionTopLevelFields",
    },
)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).date()


def _add_utc_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _expect_non_empty_string_list(values: list[str], label: str) -> None:
    assert values, label
    assert re.search(r"\S", values[0]), label
    for value in values:
        assert re.search(r"\S", value), label


def _list_git_tracked_files(ts_repo: Path, pathspecs: tuple[str, ...]) -> list[str] | None:
    result = subprocess.run(
        ["git", "ls-files", "--", *pathspecs],
        cwd=ts_repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return sorted(
        line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()
    )


def _list_tracked_source_files(ts_repo: Path) -> list[str]:
    tracked = _list_git_tracked_files(ts_repo, SOURCE_ROOTS_FOR_DEPRECATED_CALL_GUARD)
    if tracked is None:
        pytest.skip("git ls-files unavailable in TypeScript source repo")
    return [file for file in tracked if re.search(r"\.(?:ts|tsx|mts|cts)$", file)]


@pytest.fixture(scope="module")
def deprecated_target_parser_offenders(ts_repo: Path) -> list[str]:
    offenders: list[str] = []
    for file in _list_tracked_source_files(ts_repo):
        if file in DEPRECATED_TARGET_PARSER_COMPAT_FILES:
            continue
        path = ts_repo / file
        content = path.read_text(encoding="utf-8")
        if DEPRECATED_TARGET_PARSER_CALL_PATTERN.search(content):
            offenders.append(file)
    return offenders


class TestPluginCompatibilityRegistry:
    def test_keeps_compatibility_codes_unique_and_lookup_safe(self) -> None:
        records = list_plugin_compat_records()
        codes = [record.code for record in records]

        assert len(set(codes)) == len(codes)
        assert is_plugin_compat_code("legacy-root-sdk-import") is True
        assert is_plugin_compat_code("missing-code") is False
        assert get_plugin_compat_record("legacy-root-sdk-import").owner == "sdk"

    def test_requires_dated_deprecation_metadata_for_deprecated_records(self) -> None:
        for record in list_deprecated_plugin_compat_records():
            assert DATE_PATTERN.fullmatch(record.deprecated or ""), record.code
            assert DATE_PATTERN.fullmatch(record.warning_starts or ""), record.code
            assert DATE_PATTERN.fullmatch(record.remove_after or ""), record.code
            if not record.warning_starts or not record.remove_after:
                raise AssertionError(f"{record.code} is missing deprecation window dates")
            max_remove_after = _add_utc_months(_parse_date(record.warning_starts), 3)
            remove_after = _parse_date(record.remove_after)
            assert remove_after <= max_remove_after, record.code
            assert re.search(r"\S", record.replacement or ""), record.code
            assert (record.docs_path or "").startswith("/"), record.code

    def test_keeps_every_record_actionable(self, ts_repo: Path) -> None:
        for record in list_plugin_compat_records():
            assert DATE_PATTERN.fullmatch(record.introduced), record.code
            assert record.docs_path.startswith("/"), record.code
            _expect_non_empty_string_list(record.surfaces, f"{record.code}: surfaces")
            _expect_non_empty_string_list(record.diagnostics, f"{record.code}: diagnostics")
            _expect_non_empty_string_list(record.tests, f"{record.code}: tests")
            for test_path in record.tests:
                assert (ts_repo / test_path).is_file(), f"{record.code}: {test_path}"

    def test_tracks_known_plugin_facing_deprecated_surfaces(self, ts_repo: Path) -> None:
        for surface in KNOWN_DEPRECATED_SURFACE_MARKERS:
            assert is_plugin_compat_code(surface["code"]), surface["code"]
            content = (ts_repo / surface["file"]).read_text(encoding="utf-8")
            assert surface["marker"] in content, surface["file"]

    def test_keeps_deprecated_explicit_target_parser_calls_inside_compatibility_shims(
        self,
        deprecated_target_parser_offenders: list[str],
    ) -> None:
        assert deprecated_target_parser_offenders == []
