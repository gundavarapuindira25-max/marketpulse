"""
Deterministic hallucination guard for the market narrator.

Rather than trusting the prompt instruction alone ("only use the given
numbers"), this extracts every number the model's narration actually states
and checks each one against the real numbers it was given — order book
prices/sizes and recent candle OHLCV values. If the narration states a
number that isn't actually in the source data, it's treated as a
hallucination and the caller should reject that narration rather than
broadcast it.

Known limitation: standalone incidental numbers (e.g. "the 2nd time") would
still get flagged, since this only checks whether a number matches
something real — it can't tell *why* the model said a number. Hyphenated
units ("1-minute", "24-hour") are explicitly excluded since those come up
constantly in this prompt's own vocabulary and aren't market-data claims.
This is a heuristic guard, not a proof of correctness — verified against
false positives during testing, but not exhaustively.
"""

import re

# Excludes numbers in hyphenated compounds like "1-minute" or "24-hour" —
# those are units of measure, not market-data claims, and would otherwise
# be false-flagged as ungrounded.
_NUMBER_RE = re.compile(r"\$?(-?\d[\d,]*\.?\d*)(?!-[a-zA-Z])")


def extract_numbers(text: str) -> list[float]:
    numbers = []
    for match in _NUMBER_RE.finditer(text):
        raw = match.group(1).replace(",", "")
        if raw in ("", "-", "."):
            continue
        try:
            numbers.append(float(raw))
        except ValueError:
            continue
    return numbers


def source_numbers(order_book: dict, candles: list[dict]) -> set[float]:
    values = set()
    for key in ("last_price", "best_bid", "best_ask", "spread", "mid_price"):
        v = order_book.get(key)
        if v is not None:
            values.add(round(float(v), 6))
    for level in order_book.get("bids", []) + order_book.get("asks", []):
        values.add(round(float(level["price"]), 6))
        values.add(round(float(level["size"]), 6))
    for candle in candles:
        for key in ("open", "high", "low", "close", "volume"):
            v = candle.get(key)
            if v is not None:
                values.add(round(float(v), 6))
    return values


def _is_grounded_number(n: float, source: set[float]) -> bool:
    tolerance = max(0.01, abs(n) * 0.001)  # 0.1% relative, 1-cent floor
    return any(abs(n - s) <= tolerance for s in source)


def check_grounded(narration: str, order_book: dict, candles: list[dict]) -> tuple[bool, list[float]]:
    """Returns (is_grounded, offending_numbers) — offending_numbers is empty
    when every number in the narration matches something in the source data."""
    source = source_numbers(order_book, candles)
    offending = [n for n in extract_numbers(narration) if not _is_grounded_number(n, source)]
    return (len(offending) == 0, offending)
