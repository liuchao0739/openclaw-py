"""Quality contract and fallback helpers for compaction safeguard summaries."""

from __future__ import annotations

REQUIRED_SUMMARY_SECTIONS = (
    "## Decisions",
    "## Open TODOs",
    "## Constraints/Rules",
    "## Pending user asks",
    "## Exact identifiers",
)

STRICT_EXACT_IDENTIFIERS_INSTRUCTION = (
    "For ## Exact identifiers, preserve literal values exactly as seen "
    "(IDs, URLs, file paths, ports, hashes, dates, times)."
)


def build_compaction_structure_instructions(
    custom_instructions: str | None = None,
    identifier_policy: str | None = None,
) -> str:
    if identifier_policy == "off":
        id_instruction = (
            "For ## Exact identifiers, include identifiers only when needed for continuity; "
            "do not enforce literal-preservation rules."
        )
    else:
        id_instruction = STRICT_EXACT_IDENTIFIERS_INSTRUCTION
    sections_template = (
        "Produce a compact, factual summary with these exact section headings:\n"
        + "\n".join(REQUIRED_SUMMARY_SECTIONS)
        + f"\n{id_instruction}\n"
        "Do not omit unresolved asks from the user.\n"
        "When prior compaction summaries are present, re-distill them with new messages "
        "and remove stale duplicate detail."
    )
    custom = custom_instructions.strip() if custom_instructions else ""
    if not custom:
        return sections_template
    return f"{sections_template}\n\nAdditional context from /compact:\n{custom}"


def _has_required_summary_sections(summary: str) -> bool:
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    cursor = 0
    for heading in REQUIRED_SUMMARY_SECTIONS:
        found = False
        for idx in range(cursor, len(lines)):
            if lines[idx] == heading:
                cursor = idx + 1
                found = True
                break
        if not found:
            return False
    return True


def build_structured_fallback_summary(previous_summary: str | None) -> str:
    trimmed = (previous_summary or "").strip()
    if trimmed and _has_required_summary_sections(trimmed):
        return trimmed
    return "\n".join(
        [
            "## Decisions",
            trimmed or "No prior history.",
            "",
            "## Open TODOs",
            "None.",
            "",
            "## Constraints/Rules",
            "None.",
            "",
            "## Pending user asks",
            "None.",
            "",
            "## Exact identifiers",
            "None captured.",
        ]
    )


def append_summary_section(summary: str, section: str) -> str:
    if not section:
        return summary
    if not summary.strip():
        return section.lstrip()
    return f"{summary}{section}"