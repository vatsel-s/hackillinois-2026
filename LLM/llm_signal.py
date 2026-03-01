"""
LLM-based market direction signal using Groq + Llama 3.3 70B.

Implements the "Context-Aware Direction Inference" stage described in PLAN.md.
Instead of using FinBERT's raw sentiment tone, this module asks the LLM:
"Does this headline make YES more or less likely for *this specific market*?"

Routing logic:
  - Financial/macro markets (Fed, rates, earnings, etc.) → return FinBERT signal directly
  - Political, sports, and all other topics               → call LLM for direction

Usage:
    from LLM.llm_signal import resolve_signal

    result = resolve_signal(
        headline="Trump indicted on 4 counts",
        market_question="Will Trump win the 2024 Republican primary?",
        finbert_signal=-1,
    )
    # → {"signal": 1, "reasoning": "...", "source": "llm"}

Requires: GROQ_API_KEY environment variable
"""

import os
import json
import re

_FINANCIAL_KEYWORDS = {
    "fed", "federal reserve", "interest rate", "rates", "rate hike", "rate cut",
    "gdp", "inflation", "cpi", "pce", "employment", "unemployment", "jobs",
    "nonfarm", "payroll", "earnings", "revenue", "profit", "eps", "guidance",
    "stock", "equities", "s&p", "nasdaq", "dow", "yield", "bond", "treasury",
    "oil", "crude", "energy", "gas", "dollar", "usd", "eur", "forex", "currency",
    "housing", "mortgage", "retail sales", "consumer", "pmi", "manufacturing",
    "ipo", "merger", "acquisition", "dividend", "buyback", "quarterly",
}

_SYSTEM_PROMPT = """\
You are a prediction market analyst. Your job is to determine whether a news headline \
makes a specific market question more likely to resolve YES (+1), less likely (-1), or \
has no clear impact (0).

Important: do NOT just score the sentiment of the headline. Think about how the news \
actually affects the probability of the market resolving YES. Counterintuitive effects \
matter — for example, a negative headline about a controversial political figure can \
*increase* their chances in a primary because it rallies their base.

Respond ONLY with valid JSON in this exact format (no other text):
{"signal": <1, -1, or 0>, "reasoning": "<one sentence explanation>"}
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY environment variable is not set.")
        _client = Groq(api_key=api_key)
    return _client


def is_financial_market(market_question: str) -> bool:
    """
    Fast keyword-based check to determine if a market is financial/macro in nature.
    No API call — runs in microseconds.
    """
    q_lower = market_question.lower()
    return any(kw in q_lower for kw in _FINANCIAL_KEYWORDS)


def get_llm_signal(headline: str, market_question: str) -> dict:
    """
    Ask Llama 3.3 70B (via Groq) whether a headline makes the market question
    more or less likely to resolve YES.

    Returns:
        {"signal": int, "reasoning": str, "source": "llm"}
        signal: +1 (YES more likely), -1 (NO more likely), 0 (unclear)

    Falls back to signal=0 if the API call fails or response cannot be parsed.
    """
    user_prompt = (
        f'Headline: "{headline}"\n'
        f'Market question: "{market_question}"\n\n'
        f"Does this headline make YES more likely (+1), NO more likely (-1), or is the impact unclear (0)?"
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()

        # Parse JSON — try direct parse first, then regex fallback
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{[^}]+\}', raw)
            if match:
                parsed = json.loads(match.group())
            else:
                raise ValueError(f"No JSON found in response: {raw!r}")

        signal = int(parsed.get("signal", 0))
        if signal not in (-1, 0, 1):
            signal = 0

        return {
            "signal": signal,
            "reasoning": parsed.get("reasoning", ""),
            "source": "llm",
        }

    except Exception as e:
        return {"signal": 0, "reasoning": f"LLM error: {e}", "source": "llm_error"}


def resolve_signal(headline: str, market_question: str, finbert_signal: int) -> dict:
    """
    Main entry point. Routes to the appropriate signal source based on market type.

    - Financial/macro markets: return FinBERT signal (fast, no API call)
    - Political, sports, and all other markets: call LLM for context-aware direction

    Returns:
        {
            "signal":    int,   # +1 / 0 / -1
            "reasoning": str,
            "source":    str,   # "finbert" or "llm" or "llm_error"
        }
    """
    if is_financial_market(market_question):
        label = {1: "positive", -1: "negative", 0: "neutral"}.get(finbert_signal, "neutral")
        return {
            "signal": finbert_signal,
            "reasoning": f"Financial market — using FinBERT signal ({label})",
            "source": "finbert",
        }

    return get_llm_signal(headline, market_question)


# ---------------------------------------------------------------------------
# Quick test / demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import time

    test_cases = [
        # Political — LLM should handle
        (
            "Trump indicted on 4 counts",
            "Will Trump win the 2024 Republican primary?",
            -1,
        ),
        # Financial — FinBERT signal used directly
        (
            "Fed raises interest rates by 50 basis points",
            "Will the Fed raise rates at the March 2024 meeting?",
            -1,
        ),
        # Sports — LLM
        (
            "LeBron James ruled out for the rest of the playoffs with knee injury",
            "Will the Lakers win the 2024 NBA championship?",
            -1,
        ),
    ]

    for headline, market_question, finbert in test_cases:
        print(f"\nHeadline:        {headline}")
        print(f"Market question: {market_question}")
        print(f"FinBERT signal:  {finbert}")
        t0 = time.perf_counter()
        result = resolve_signal(headline, market_question, finbert)
        elapsed = time.perf_counter() - t0
        print(f"→ signal={result['signal']:+d}  source={result['source']}  ({elapsed:.2f}s)")
        print(f"  reason: {result['reasoning']}")
