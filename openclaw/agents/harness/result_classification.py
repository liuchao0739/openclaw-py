"""Agent harness result classification helper.

Harness lifecycle wraps raw attempt results with harness id metadata and lets
harness-specific classifiers attach non-ok result categories.
"""

from __future__ import annotations

from typing import Any


def apply_agent_harness_result_classification(
    harness: Any,
    result: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Apply a harness classifier while replacing any stale prior classification."""
    classify = getattr(harness, "classify", None)
    harness_id = getattr(harness, "id", None)
    if classify is None:
        return {**result, "agentHarnessId": harness_id}

    # Reclassify from the raw result so retries or wrappers cannot preserve an
    # obsolete classification from an earlier harness.
    result_without_previous = {k: v for k, v in result.items() if k != "agentHarnessResultClassification"}
    classification = classify(result_without_previous, params)
    if not classification or classification == "ok":
        return {**result_without_previous, "agentHarnessId": harness_id}
    return {
        **result_without_previous,
        "agentHarnessId": harness_id,
        "agentHarnessResultClassification": classification,
    }
