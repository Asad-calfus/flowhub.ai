"""Few-shot LLM classifier: structured JSON output, Pydantic validation, one retry,
local caching, and dry-run mode for development without API calls.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from pydantic import ValidationError

from src.classification.baseline import classify_baseline
from src.classification.prompt_builder import build_prompt
from src.classification.schemas import ClassificationOutput, ClassifierInput, assert_no_leakage

load_dotenv()

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CACHE_PATH = os.path.join(REPO_ROOT, "results", "cache", "llm_cache.json")

MAX_ATTEMPTS = 2  # one initial call + one retry

_run_logger = logging.getLogger("classification.runs")


@dataclass
class ClassificationResult:
    feedback_id: str
    output: Optional[ClassificationOutput]
    error: Optional[str] = None
    retries: int = 0
    latency_seconds: float = 0.0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    from_cache: bool = False
    dry_run: bool = False
    raw_response: Optional[str] = None


def _log_classification(model: str, result: "ClassificationResult") -> None:
    _run_logger.info(json.dumps({
        "record_id": result.feedback_id,
        "model": model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_seconds": round(result.latency_seconds, 4),
        "predicted_label": result.output.feedback_type if result.output else None,
        "cache_hit": result.from_cache,
        "dry_run": result.dry_run,
        "error": result.error,
    }))


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if text.count("```") >= 2 else text.strip("`")
        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text


class FewShotClassifier:
    def __init__(
        self,
        examples: list[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        dry_run: Optional[bool] = None,
        cache_path: str = DEFAULT_CACHE_PATH,
        timeout: Optional[float] = None,
    ):
        self.examples = examples
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "anthropic")).lower()
        self.model = model or os.environ.get("LLM_MODEL", "")
        self.api_key = api_key or os.environ.get(self._api_key_env_var(), "")
        self.timeout = timeout or float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
        self.dry_run = dry_run if dry_run is not None else not bool(self.api_key)
        self.cache_path = cache_path
        self.failures: list[dict] = []
        self._client = None
        self.cache = self._load_cache()

    def _api_key_env_var(self) -> str:
        return "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"

    # -- cache -------------------------------------------------------------

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            with open(self.cache_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)

    # -- LLM call (or dry-run stub) -----------------------------------------

    def _call_llm(self, system_prompt: str, user_prompt: str, record: ClassifierInput) -> tuple[str, dict, float]:
        """Return (raw_text_response, usage_dict, latency_seconds)."""
        start = time.perf_counter()
        if self.dry_run:
            # Deterministic local stub so the full parse/validate/retry path is exercised
            # without any network call. Uses the rule-based baseline to produce a
            # plausible-shaped JSON body - NOT a stand-in for real LLM accuracy.
            stub_output = classify_baseline(record)
            payload = stub_output.model_dump()
            payload["reasoning"] = "DRY_RUN stub - no API call made."
            raw = json.dumps(payload)
            latency = time.perf_counter() - start
            return raw, {"input_tokens": 0, "output_tokens": 0}, latency

        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, start)
        return self._call_anthropic(system_prompt, user_prompt, start)

    def _call_anthropic(self, system_prompt: str, user_prompt: str, start: float) -> tuple[str, dict, float]:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency = time.perf_counter() - start
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
        }
        return text, usage, latency

    def _call_openai(self, system_prompt: str, user_prompt: str, start: float) -> tuple[str, dict, float]:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)

        # JSON mode cuts down on invalid-JSON retries (each retry doubles token spend),
        # which matters more for a paid key than for Anthropic's free-tier-friendly dry runs.
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        latency = time.perf_counter() - start
        text = response.choices[0].message.content or ""
        usage = {
            "input_tokens": getattr(response.usage, "prompt_tokens", None),
            "output_tokens": getattr(response.usage, "completion_tokens", None),
        }
        return text, usage, latency

    # -- public API ----------------------------------------------------------

    def classify(self, feedback_id: str, record: ClassifierInput, force: bool = False) -> ClassificationResult:
        if not force and feedback_id in self.cache:
            cached = self.cache[feedback_id]
            if cached.get("output") is not None:
                result = ClassificationResult(
                    feedback_id=feedback_id,
                    output=ClassificationOutput(**cached["output"]),
                    retries=cached.get("retries", 0),
                    latency_seconds=cached.get("latency_seconds", 0.0),
                    input_tokens=cached.get("input_tokens"),
                    output_tokens=cached.get("output_tokens"),
                    from_cache=True,
                    dry_run=cached.get("dry_run", False),
                )
                _log_classification(self.model, result)
                return result

        payload = record.model_dump()
        assert_no_leakage(payload)

        system_prompt, user_prompt = build_prompt(record, self.examples)

        last_error = None
        raw_response = None
        total_latency = 0.0
        total_in_tokens = 0
        total_out_tokens = 0

        for attempt in range(MAX_ATTEMPTS):
            raw_response, usage, latency = self._call_llm(system_prompt, user_prompt, record)
            total_latency += latency
            total_in_tokens += usage.get("input_tokens") or 0
            total_out_tokens += usage.get("output_tokens") or 0

            try:
                cleaned = _strip_json_fences(raw_response)
                parsed = json.loads(cleaned)
                output = ClassificationOutput(**parsed)
                result = ClassificationResult(
                    feedback_id=feedback_id,
                    output=output,
                    retries=attempt,
                    latency_seconds=total_latency,
                    input_tokens=total_in_tokens or None,
                    output_tokens=total_out_tokens or None,
                    dry_run=self.dry_run,
                    raw_response=raw_response,
                )
                self.cache[feedback_id] = {
                    "output": output.model_dump(),
                    "retries": attempt,
                    "latency_seconds": total_latency,
                    "input_tokens": total_in_tokens or None,
                    "output_tokens": total_out_tokens or None,
                    "dry_run": self.dry_run,
                }
                self._save_cache()
                _log_classification(self.model, result)
                return result
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = str(exc)
                user_prompt = (
                    user_prompt
                    + f"\n\nYour previous response was invalid ({last_error[:200]}). "
                    "Return ONLY a single valid JSON object matching the required schema."
                )

        # Both attempts failed - store the failure instead of silently skipping it.
        failure = {
            "feedback_id": feedback_id,
            "error": last_error,
            "raw_response": raw_response,
        }
        self.failures.append(failure)
        result = ClassificationResult(
            feedback_id=feedback_id,
            output=None,
            error=last_error,
            retries=MAX_ATTEMPTS - 1,
            latency_seconds=total_latency,
            input_tokens=total_in_tokens or None,
            output_tokens=total_out_tokens or None,
            dry_run=self.dry_run,
            raw_response=raw_response,
        )
        _log_classification(self.model, result)
        return result
