"""Deterministic rule-based + VADER baseline classifier.

Exists purely as a comparison point for the few-shot LLM classifier - kept
intentionally small and unsophisticated.
"""

import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.classification.schemas import CATEGORY_MAP, ClassificationOutput, ClassifierInput

_analyzer = SentimentIntensityAnalyzer()

# (module_name, keyword_pattern) - first match wins, order encodes priority
# (e.g. "google calendar sync" must hit Integrations before Task Management's
# generic "calendar").
_MODULE_RULES: list[tuple[str, str]] = [
    ("Integrations", r"\b(slack|jira|zapier|trello|webhook|google calendar|integration|sync(ing)?)\b"),
    ("Billing", r"\b(billing|invoice|charge(d)?|tax|refund|subscription|renewal|pricing|plan|currency|discount)\b"),
    ("Mobile App", r"\b(mobile|ios|android|phone|tablet)\b"),
    ("Reports", r"\b(report|export|csv|excel)\b"),
    ("Notifications", r"\b(notification|notif|digest|push|alert)\b"),
    ("Authentication", r"\b(login|log in|logged|logout|log out|sso|okta|password|sign in|session|permission)\b"),
    ("Task Management", r"\b(task|subtask|project|board|calendar|due date)\b"),
    ("Dashboard", r"\b(dashboard|widget|search|workspace)\b"),
]

_BUG_RE = re.compile(
    r"\b(crash(es|ed)?|broken|bug|doesn.?t work|not working|stopped working|"
    r"error|fail(s|ing)?|wrong|incorrect|duplicate|truncat\w*|force close)\b",
    re.I,
)
_FEATURE_RE = re.compile(
    r"\b(please add|would love|can we get|feature request|would be great|"
    r"could we|any timeline|would help if|would like)\b",
    re.I,
)
_PERFORMANCE_RE = re.compile(
    r"\b(slow|laggy|lag|sluggish|delay(ed)?|takes (almost |over )?\d+|seconds?\b.*load)\b",
    re.I,
)
_SERVICE_RE = re.compile(
    r"\b(support (agent|team)?|waited \d+|canned response|unacceptable|"
    r"rejected|not on our roadmap|no notice|closed my ticket)\b",
    re.I,
)
_PRAISE_RE = re.compile(
    r"\b(love|great|awesome|fantastic|best|appreciate|thanks|thank you|"
    r"5 stars|nice work|genuinely great|big win|huge win)\b",
    re.I,
)
_USABILITY_RE = re.compile(
    r"\b(confusing|not obvious|hard to find|unclear|took (me |a )?(a )?while|"
    r"buried|not clear|inconsistent)\b",
    re.I,
)
_URGENT_RE = re.compile(r"\b(blocking|urgent|asap|immediately|critical|escalate)\b", re.I)
_ANNOYED_RE = re.compile(r"\b(annoying|frustrat\w*|furious|ridiculous)\b", re.I)


def _detect_module(text: str) -> tuple[str, bool]:
    for module, pattern in _MODULE_RULES:
        if re.search(pattern, text, re.I):
            return module, True
    return "Dashboard", False


def _detect_feedback_type(text: str) -> tuple[str, bool]:
    if _BUG_RE.search(text):
        return "Bug report", True
    if _FEATURE_RE.search(text):
        return "Feature request", True
    if _PERFORMANCE_RE.search(text):
        return "Performance issue", True
    if _SERVICE_RE.search(text):
        return "Service complaint", True
    stripped = text.strip()
    if stripped.endswith("?") or re.match(r"^(how|what|why|is there|does|can i|could you)\b", stripped, re.I):
        return "Question", True
    if _PRAISE_RE.search(text):
        return "Praise", True
    if _USABILITY_RE.search(text):
        return "Usability issue", True
    return "Other", False


def _detect_sentiment(text: str) -> str:
    scores = _analyzer.polarity_scores(text)
    if scores["pos"] > 0.15 and scores["neg"] > 0.15:
        return "Mixed"
    if scores["compound"] >= 0.3:
        return "Positive"
    if scores["compound"] <= -0.3:
        return "Negative"
    return "Neutral"


def _detect_urgency(text: str, sentiment: str, tier: str | None) -> str:
    if _URGENT_RE.search(text):
        return "High"
    if tier == "Enterprise" and sentiment in ("Negative", "Mixed"):
        return "High"
    if sentiment in ("Negative", "Mixed") or _ANNOYED_RE.search(text):
        return "Medium"
    return "Low"


def classify_baseline(record: ClassifierInput) -> ClassificationOutput:
    """Rule-based + VADER classification. No API calls, fully deterministic."""
    text = record.feedback_text

    module, module_matched = _detect_module(text)
    ftype, type_matched = _detect_feedback_type(text)
    sentiment = _detect_sentiment(text)
    urgency = _detect_urgency(text, sentiment, record.customer_tier)
    category = CATEGORY_MAP[ftype]

    matched = sum([module_matched, type_matched])
    confidence = round(min(0.5 + 0.2 * matched, 0.9), 2)
    reasoning = (
        f"Rule-based: type matched={type_matched}, module matched={module_matched}, "
        f"VADER sentiment={sentiment}."
    )[:200]

    return ClassificationOutput(
        feedback_type=ftype,
        category=category,
        product_module=module,
        sentiment=sentiment,
        urgency=urgency,
        confidence=confidence,
        reasoning=reasoning,
    )
