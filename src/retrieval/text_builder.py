"""Builds consistent embedding text per record type. Feedback text is built from an
explicit whitelist (not the full row) and leakage-checked, so a future new column can
never silently leak a label into the embedding.
"""

from src.classification.schemas import assert_no_leakage

FEEDBACK_TEXT_FIELDS = ("feedback_text", "source", "customer_tier", "product_version", "language")


def build_feedback_text(record: dict) -> str:
    whitelisted = {k: record.get(k, "") for k in FEEDBACK_TEXT_FIELDS}
    assert_no_leakage(whitelisted)
    parts = [
        whitelisted["feedback_text"],
        f"source: {whitelisted['source']}" if whitelisted["source"] else "",
        f"tier: {whitelisted['customer_tier']}" if whitelisted["customer_tier"] else "",
        f"version: {whitelisted['product_version']}" if whitelisted["product_version"] else "",
        f"language: {whitelisted['language']}" if whitelisted["language"] else "",
    ]
    return " | ".join(p for p in parts if p)


def build_bug_text(bug: dict) -> str:
    return " | ".join(
        p for p in [
            bug.get("title", ""),
            bug.get("description", ""),
            f"module: {bug.get('product_module', '')}",
            f"affected: {bug.get('affected_versions', '')}",
            f"status: {bug.get('status', '')}",
        ] if p
    )


def build_feature_request_text(fr: dict) -> str:
    return " | ".join(
        p for p in [
            fr.get("title", ""),
            fr.get("description", ""),
            f"module: {fr.get('product_module', '')}",
            f"roadmap: {fr.get('roadmap_status', '')}",
        ] if p
    )


def build_release_text(release: dict) -> str:
    return " | ".join(
        p for p in [
            release.get("version", ""),
            release.get("main_changes", ""),
            f"modules: {release.get('affected_modules', '')}",
            f"limitations: {release.get('known_limitations', '')}",
        ] if p
    )
