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


def _build_payload(order_book: dict, candles: list[dict], product_id: str) -> str:
    """Compact JSON snapshot — top few book levels + recent candles only,
    to keep the prompt small for a call that repeats every cycle."""
    payload = {
        "product": product_id,
        "last_price": order_book.get("last_price"),
        "last_trade_side": order_book.get("last_trade_side"),
        "best_bid": order_book.get("best_bid"),
        "best_ask": order_book.get("best_ask"),
        "spread": order_book.get("spread"),
        "mid_price": order_book.get("mid_price"),
        "top_bids": order_book.get("bids", [])[:5],
        "top_asks": order_book.get("asks", [])[:5],
        "recent_candles": candles[-10:],
    }
    return json.dumps(payload)


async def generate_narration(
    client: ollama.AsyncClient,
    order_book: dict,
    candles: list[dict],
    product_id: str,
) -> Optional[str]:
    """Returns a short narration string, or None if generation failed —
    callers should just skip broadcasting that cycle on None rather than
    treating it as fatal (e.g. Ollama not running yet)."""
    try:
        response = await client.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_payload(order_book, candles, product_id)},
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
    return text.strip() if text else None
