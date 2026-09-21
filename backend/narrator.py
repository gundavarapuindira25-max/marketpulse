"""
MarketPulse — LLM market narrator.

Periodically turns the current order book + recent candle history into a
short, plain-English summary via a local Ollama model. Grounded strictly in
the numbers it's given (no speculation, no financial advice) so it can't
hallucinate prices that don't match what's on screen.

Runs against Ollama (http://localhost:11434 by default) — no API key, no
per-call cost. Requires `ollama serve` running locally with MODEL pulled
(see backend/.env.example).
"""

import json
import logging
import os
from typing import Optional

import ollama

from validation import check_grounded

logger = logging.getLogger("narrator")

MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SYSTEM_PROMPT = """You are a market narrator for a live BTC-USD trading dashboard.

You will be given a JSON snapshot of the current order book and the most recent
1-minute OHLCV candles. Write ONE short paragraph (1-3 sentences, under 50 words)
describing what's happening right now, for someone glancing at the screen.

Rules:
- Only state facts that follow directly from the given numbers. Never invent a
  price, level, or trend that isn't supported by the data.
- No trading advice, no predictions, no "you should buy/sell".
- Plain, concrete language — mention specific price levels or the spread when
  relevant, rather than vague words like "volatile".
- If the data is too sparse to say anything meaningful, say so briefly instead
  of padding with filler.
- Output only the paragraph itself — no preamble, no markdown, no quotes."""


def _build_context(order_book: dict, candles: list[dict], product_id: str) -> dict:
    """Compact snapshot — top few book levels + recent candles only, to keep
    the prompt small for a call that repeats every cycle. This is also what
    the grounding check validates against, so it must contain exactly what
    the model was actually shown — nothing more, nothing less."""
    return {
        "product": product_id,
        "last_price": order_book.get("last_price"),
        "last_trade_side": order_book.get("last_trade_side"),
        "best_bid": order_book.get("best_bid"),
        "best_ask": order_book.get("best_ask"),
        "spread": order_book.get("spread"),
        "mid_price": order_book.get("mid_price"),
        "bids": order_book.get("bids", [])[:5],
        "asks": order_book.get("asks", [])[:5],
        "recent_candles": candles[-10:],
    }


async def generate_narration(
    client: ollama.AsyncClient,
    order_book: dict,
    candles: list[dict],
    product_id: str,
) -> Optional[str]:
    """Returns a short narration string, or None if generation failed, was
    unreachable, or failed the grounding check — callers should just skip
    broadcasting that cycle on None rather than treating it as fatal."""
    context = _build_context(order_book, candles, product_id)
    try:
        response = await client.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context)},
            ],
            options={"temperature": 0.3, "num_predict": 150},
        )
    except ollama.ResponseError as e:
        # e.g. model not pulled yet
        logger.warning("[narrator] Ollama response error (%s): %s", e.status_code, e.error)
        return None
    except ollama.RequestError as e:
        logger.warning("[narrator] Ollama request error: %s", e.error)
        return None
    except Exception as e:
        # covers connection failures when the Ollama server isn't running
        logger.warning("[narrator] Ollama unreachable: %s", e)
        return None

    text = response.message.content
    if not text:
        return None
    text = text.strip()

    grounded, offending = check_grounded(text, context, context["recent_candles"])
    if not grounded:
        logger.warning("[narrator] rejected ungrounded narration (numbers not in source data: %s): %r", offending, text)
        return None

    return text
