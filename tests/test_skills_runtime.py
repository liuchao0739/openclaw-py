"""Tests for skills/runtime snapshot hydration."""

from openclaw.skills.runtime.snapshot_hydration import hydrate_resolved_skills


def test_keeps_existing_skills():
    snapshot = {"resolvedSkills": ["skill1"], "other": "data"}
    result = hydrate_resolved_skills(snapshot, lambda: {"resolvedSkills": ["new"]})
    assert result["resolvedSkills"] == ["skill1"]
    assert result["other"] == "data"


def test_hydrates_missing_skills():
    snapshot = {"other": "data"}
    result = hydrate_resolved_skills(snapshot, lambda: {"resolvedSkills": ["new"]})
    assert result["resolvedSkills"] == ["new"]
    assert result["other"] == "data"


def test_hydrates_none_skills():
    snapshot = {"resolvedSkills": None}
    result = hydrate_resolved_skills(snapshot, lambda: {"resolvedSkills": ["new"]})
    assert result["resolvedSkills"] == ["new"]


def test_rebuild_not_called_when_present():
    called = [0]

    def rebuild():
        called[0] += 1
        return {"resolvedSkills": ["x"]}

    snapshot = {"resolvedSkills": ["existing"]}
    hydrate_resolved_skills(snapshot, rebuild)
    assert called[0] == 0


def test_rebuild_called_when_missing():
    called = [0]

    def rebuild():
        called[0] += 1
        return {"resolvedSkills": ["x"]}

    snapshot = {}
    hydrate_resolved_skills(snapshot, rebuild)
    assert called[0] == 1


def test_does_not_mutate_original():
    snapshot = {"other": "data"}
    result = hydrate_resolved_skills(snapshot, lambda: {"resolvedSkills": ["x"]})
    assert "resolvedSkills" not in snapshot
    assert "resolvedSkills" in result
