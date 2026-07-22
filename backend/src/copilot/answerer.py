"""AI Copilot: natural-language Q&A over stored feedback.

Retrieval (app/services/copilot_service.py) finds the evidence; this module only words
the answer around it - same "facts from data, LLM for prose only" split as
src/reports/generator.py. Dry-run (deterministic, no API call) unless a key is configured
and the caller opts into `live=True` - same cost-safety convention as the classifier and
report generator.
"""

import os

from dotenv import load_dotenv

from src.classification.classifier import GROQ_BASE_URL

load_dotenv()

SYSTEM_PROMPT = (
    "You are a support analyst assistant. Answer the user's question about customer feedback "
    "using ONLY the feedback excerpts provided below. If the excerpts don't contain enough "
    "information to answer, say so plainly. Do not invent feedback, customers, or facts not "
    "present in the excerpts. Keep the answer to 2-4 sentences, plain text, no markdown."
)


def _build_user_prompt(question: str, retrieved: list[dict]) -> str:
    lines = [f"Question: {question}", "", "Feedback excerpts:"]
    for r in retrieved:
        lines.append(f"- [{r['feedback_id']}] ({r.get('sentiment') or 'unknown'} sentiment): {r['text_preview']}")
    return "\n".join(lines)


def build_deterministic_answer(retrieved: list[dict]) -> str:
    if not retrieved:
        return "No related feedback found for this question."
    sentiments = [r["sentiment"] for r in retrieved if r.get("sentiment")]
    top_sentiment = max(set(sentiments), key=sentiments.count) if sentiments else "unknown"
    ids = ", ".join(r["feedback_id"] for r in retrieved)
    return (
        f"Found {len(retrieved)} related feedback item(s): {ids}. "
        f"Most common sentiment among them: {top_sentiment}. Review the linked feedback for full context."
    )


class CopilotAnswerer:
    def __init__(self, provider=None, model=None, api_key=None, dry_run=None, timeout=None):
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "anthropic")).lower()
        self.model = model or os.environ.get("LLM_MODEL", "")
        self.api_key = api_key or os.environ.get(self._api_key_env_var(), "")
        self.timeout = timeout or float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
        self.dry_run = dry_run if dry_run is not None else not bool(self.api_key)
        self._client = None

    def _api_key_env_var(self) -> str:
        return {"openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY"}.get(self.provider, "ANTHROPIC_API_KEY")

    def answer(self, question: str, retrieved: list[dict]) -> tuple[str, str]:
        """Returns (answer_text, model_name)."""
        if self.dry_run:
            return build_deterministic_answer(retrieved), "dry-run-stub"

        user_prompt = _build_user_prompt(question, retrieved)
        if self.provider in ("openai", "groq"):
            text = self._call_openai_compatible(user_prompt)
        else:
            text = self._call_anthropic(user_prompt)
        return text.strip(), f"{self.provider}:{self.model}"

    def _call_anthropic(self, user_prompt: str) -> str:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
        response = self._client.messages.create(
            model=self.model, max_tokens=300, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))

    def _call_openai_compatible(self, user_prompt: str) -> str:
        if self._client is None:
            import openai

            base_url = GROQ_BASE_URL if self.provider == "groq" else None
            self._client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout, base_url=base_url)
        response = self._client.chat.completions.create(
            model=self.model, max_tokens=300,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
        )
        return response.choices[0].message.content or ""
