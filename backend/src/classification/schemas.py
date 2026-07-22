"""
Label taxonomy, input/output schemas, and the data-leakage guard for the
classification pipeline. Labels below mirror docs/taxonomy.md exactly - do not
add or rename values here without updating that document too.
"""

from typing import Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Controlled vocabulary (must match docs/taxonomy.md / data/context files)
# ---------------------------------------------------------------------------

FeedbackType = Literal[
    "Bug report",
    "Feature request",
    "Usability issue",
    "Performance issue",
    "Service complaint",
    "Praise",
    "Question",
    "Other",
]

Category = Literal[
    "Technical Issue",
    "Product Feedback",
    "Support Experience",
    "Positive Feedback",
    "Inquiry",
    "Other",
]

ProductModule = Literal[
    "Authentication",
    "Dashboard",
    "Task Management",
    "Notifications",
    "Billing",
    "Integrations",
    "Reports",
    "Mobile App",
]

Sentiment = Literal["Positive", "Neutral", "Negative", "Mixed"]

Urgency = Literal["Low", "Medium", "High"]

Source = Literal[
    "Support ticket", "Survey", "App review", "Chat", "Email", "Community post",
]

CustomerTier = Literal["Free", "Pro", "Enterprise"]

# Case-insensitive lookup so real-world CSVs ("support ticket", "PRO", ...) still classify
# instead of raising a validation error - unrecognized values just fall back to None
# (no source/tier context for that record) rather than crashing.
_SOURCE_LOOKUP: dict[str, str] = {s.lower(): s for s in get_args(Source)}
_TIER_LOOKUP: dict[str, str] = {t.lower(): t for t in get_args(CustomerTier)}

# feedback_type -> category roll-up, as defined in docs/data_dictionary.md
CATEGORY_MAP: dict[str, str] = {
    "Bug report": "Technical Issue",
    "Performance issue": "Technical Issue",
    "Feature request": "Product Feedback",
    "Usability issue": "Product Feedback",
    "Service complaint": "Support Experience",
    "Praise": "Positive Feedback",
    "Question": "Inquiry",
    "Other": "Other",
}

# ---------------------------------------------------------------------------
# Data-leakage guard
# ---------------------------------------------------------------------------

# Fields the classifier is allowed to see. Anything else present on an input
# record is dropped (not just ignored) before it ever reaches a prompt.
ALLOWED_INPUT_FIELDS: frozenset[str] = frozenset(
    {"feedback_text", "source", "customer_tier", "product_version", "rating", "language"}
)

# Fields that are evaluation labels only and must never be seen by the
# classifier. Presence of any of these (with a non-empty value) in a payload
# about to be sent to a prompt or API call is a hard error.
LEAKAGE_FIELDS: frozenset[str] = frozenset(
    {
        "feedback_type",
        "category",
        "product_module",
        "sentiment",
        "urgency",
        "theme_hint",
        "related_context_id",
        "is_gold_label",
        "label_source",
    }
)


class LeakageError(ValueError):
    """Raised when a target/evaluation-label field is about to leak into classifier input."""


def assert_no_leakage(payload: dict) -> None:
    """Raise LeakageError if any label field is present in payload with a non-empty value."""
    leaked = [
        key
        for key in LEAKAGE_FIELDS
        if key in payload and payload[key] not in (None, "", "nan")
    ]
    if leaked:
        raise LeakageError(f"Leakage fields present in classifier payload: {leaked}")


def strip_leakage_fields(record: dict) -> dict:
    """Return a copy of record containing only ALLOWED_INPUT_FIELDS keys that are present."""
    cleaned = {k: v for k, v in record.items() if k in ALLOWED_INPUT_FIELDS}
    assert_no_leakage(cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


class ClassifierInput(BaseModel):
    """The only fields the classifier (rule-based or LLM) is allowed to consume."""

    model_config = ConfigDict(extra="forbid")

    feedback_text: str = Field(min_length=1)
    source: Optional[Source] = None
    customer_tier: Optional[CustomerTier] = None
    product_version: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    language: Optional[str] = None

    @classmethod
    def from_record(cls, record: dict) -> "ClassifierInput":
        """Build a ClassifierInput from a raw dict, stripping any leakage fields first.

        Real-world data (CSV imports especially) won't reliably match our controlled
        vocabulary's exact casing/wording for `source`/`customer_tier` - those are matched
        case-insensitively, and anything unrecognized degrades to None instead of raising,
        since a classification run must never crash on a single record's messy metadata.
        """
        cleaned = strip_leakage_fields(record)
        # normalize empty-string optionals (as read from CSV) to None
        for key in ("source", "customer_tier", "product_version", "language"):
            if cleaned.get(key) == "":
                cleaned[key] = None
        if cleaned.get("source"):
            cleaned["source"] = _SOURCE_LOOKUP.get(str(cleaned["source"]).strip().lower())
        if cleaned.get("customer_tier"):
            cleaned["customer_tier"] = _TIER_LOOKUP.get(str(cleaned["customer_tier"]).strip().lower())
        rating = cleaned.get("rating")
        if rating in ("", None):
            cleaned["rating"] = None
        else:
            try:
                cleaned["rating"] = int(float(rating))
            except (TypeError, ValueError):
                cleaned["rating"] = None
        return cls(**cleaned)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------


class ClassificationOutput(BaseModel):
    """Strict structured-output schema every classifier prediction must satisfy."""

    model_config = ConfigDict(extra="forbid")

    feedback_type: FeedbackType
    category: Category
    product_module: ProductModule
    sentiment: Sentiment
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1, max_length=400)


PREDICTION_FIELDS = ("feedback_type", "category", "product_module", "sentiment", "urgency")
