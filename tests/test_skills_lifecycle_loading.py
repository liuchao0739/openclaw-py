"""Tests for skills lifecycle and loading modules."""

import asyncio

from openclaw.skills.lifecycle.install_types import SkillInstallResult
from openclaw.skills.loading.skill_version import compute_skill_prompt_version
from openclaw.skills.loading.serialize import serialize_by_key


class TestSkillInstallResult:
    def test_typeddict(self):
        result: SkillInstallResult = {
            "ok": True,
            "message": "installed",
            "stdout": "",
            "stderr": "",
            "code": 0,
        }
        assert result["ok"] is True


class TestComputeSkillPromptVersion:
    def test_deterministic(self):
        assert compute_skill_prompt_version("hello") == compute_skill_prompt_version("hello")

    def test_different_content(self):
        assert compute_skill_prompt_version("a") != compute_skill_prompt_version("b")

    def test_format(self):
        result = compute_skill_prompt_version("test")
        assert result.startswith("sha256:")
        assert len(result) == 23  # "sha256:" + 16 hex chars

    def test_empty(self):
        result = compute_skill_prompt_version("")
        assert result.startswith("sha256:")


class TestSerializeByKey:
    def test_serializes_same_key(self):
        order = []

        async def task_a():
            order.append("a-start")
            await asyncio.sleep(0.01)
            order.append("a-end")

        async def task_b():
            order.append("b-start")
            await asyncio.sleep(0.01)
            order.append("b-end")

        async def main():
            t1 = asyncio.create_task(serialize_by_key("k", task_a))
            t2 = asyncio.create_task(serialize_by_key("k", task_b))
            await asyncio.gather(t1, t2)

        asyncio.run(main())
        assert order == ["a-start", "a-end", "b-start", "b-end"]

    def test_returns_result(self):
        async def task():
            return 42

        result = asyncio.run(serialize_by_key("key", task))
        assert result == 42

    def test_propagates_error(self):
        async def task():
            raise ValueError("boom")

        async def main():
            try:
                await serialize_by_key("err", task)
            except ValueError:
                return "caught"

        result = asyncio.run(main())
        assert result == "caught"
