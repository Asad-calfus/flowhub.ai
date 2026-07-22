"""Rough $/1M-token pricing for cost estimation only - not billing-accurate.

Update these numbers if provider pricing changes; the estimator is meant to catch
"this will cost $4 for 30 records" mistakes before a live run, not to be exact.
"""

# (input $ per 1M tokens, output $ per 1M tokens)
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "llama-3.1-8b-instant": (0.05, 0.08),
}

# Recommended cost-efficient default per provider.
RECOMMENDED_MODEL = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "groq": "llama-3.1-8b-instant",
}

# Which env var holds the API key for each provider - shared by the /status and
# /analysis/estimate endpoints so "is a key configured" is checked the same way everywhere.
API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    rates = PRICING.get(model)
    if rates is None:
        return None
    in_rate, out_rate = rates
    return (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate


def estimate_run_cost_usd(
    model: str, n_records: int, avg_input_tokens: int = 550, avg_output_tokens: int = 60
) -> float | None:
    """Rough pre-flight estimate for an n-record run, before any API calls are made."""
    return estimate_cost_usd(model, n_records * avg_input_tokens, n_records * avg_output_tokens)
