"""Model registry for the benchmark.

`order` is an approximate release ordering (1 = oldest) used only for the generations plot; it is
the author's judgement, not a vendor-published number. Prices are USD per million tokens
(input, output) and must be re-checked against the vendor pricing page before a paid run.
`efforts` lists reasoning-effort settings to try in order; the first the API accepts is used and
recorded. An empty list means a non-reasoning model.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelSpec:
    key: str
    provider: str            # "openai" | "anthropic"
    api_id: str
    api: str                 # "chat" | "responses" | "anthropic"
    price: tuple[float, float]
    order: int
    tier: str                # "small" | "mid" | "frontier"
    efforts: list[str] = field(default_factory=list)
    reps: int = 6            # answers per prompt
    cap: float = 0.15        # USD cap for this model in a run
    note: str = ""


def _o(key, api_id, api, price, order, tier, efforts=(), reps=6, cap=0.15, note=""):
    return ModelSpec(key, "openai", api_id, api, price, order, tier, list(efforts), reps, cap, note)


REGISTRY: dict[str, ModelSpec] = {m.key: m for m in [
    _o("gpt-4o", "gpt-4o", "chat", (2.50, 10.00), 1, "mid", reps=5, cap=0.20,
       note="oldest callable model; price third-party corroborated"),
    _o("gpt-4o-mini", "gpt-4o-mini", "chat", (0.15, 0.60), 2, "small", cap=0.10, note="price third-party corroborated"),
    _o("gpt-4.1-mini", "gpt-4.1-mini", "chat", (0.40, 1.60), 3, "small", cap=0.10),
    _o("gpt-4.1", "gpt-4.1", "chat", (2.00, 8.00), 4, "mid", reps=5, cap=0.20, note="price third-party corroborated"),
    _o("gpt-5-nano", "gpt-5-nano", "responses", (0.05, 0.40), 5, "small", ["minimal", "low"], cap=0.10),
    _o("gpt-5-mini", "gpt-5-mini", "responses", (0.25, 2.00), 6, "mid", ["minimal", "low"], cap=0.15),
    _o("gpt-5.1", "gpt-5.1", "responses", (1.25, 10.00), 7, "mid", ["none", "minimal", "low"], reps=5, cap=0.25,
       note="price third-party corroborated"),
    _o("gpt-5.2", "gpt-5.2", "responses", (1.75, 14.00), 8, "mid", ["none", "minimal", "low"], reps=5, cap=0.30,
       note="price third-party corroborated"),
    _o("gpt-5.4-mini", "gpt-5.4-mini", "responses", (0.75, 4.50), 9, "mid", ["none", "minimal", "low"], cap=0.20),
    _o("gpt-5.6-luna", "gpt-5.6-luna", "responses", (0.20, 1.20), 10, "small", ["none", "minimal", "low"], cap=0.10),
    _o("gpt-6-luna", "gpt-6-luna", "responses", (0.10, 0.50), 11, "small", ["none", "low"], cap=0.10,
       note="price from a third-party summary; verify"),
    _o("gpt-6.1-sol", "gpt-6.1-sol", "responses", (2.00, 10.00), 12, "frontier", ["low"], reps=3, cap=0.30),
    _o("gpt-6-astra", "gpt-6-astra", "responses", (10.00, 50.00), 13, "frontier", ["low"], reps=2, cap=0.55),
    # Anthropic: registered now, untested until a key is provided. Prices from the claude-api
    # skill cache (2026-09-25); re-verify.
    ModelSpec("claude-haiku-4.5", "anthropic", "claude-haiku-4-5", "anthropic", (1.00, 5.00), 14,
              "small", [], 6, 0.20, "untested"),
    ModelSpec("claude-sonnet-5.5", "anthropic", "claude-sonnet-5-5", "anthropic", (2.00, 10.00), 15,
              "mid", ["low"], 4, 0.40, "untested; omit thinking and set effort low"),
    ModelSpec("claude-opus-5.5", "anthropic", "claude-opus-5-5", "anthropic", (4.00, 20.00), 16,
              "frontier", ["low"], 3, 0.75, "thinking cannot be disabled; about 100 output tokens per call at low effort"),
]}

LINEUPS: dict[str, list[str]] = {
    "gate1": ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-5-nano", "gpt-5-mini",
              "gpt-5.1", "gpt-5.2", "gpt-5.4-mini", "gpt-5.6-luna", "gpt-6-luna", "gpt-6.1-sol", "gpt-6-astra"],
    "gate2": ["claude-haiku-4.5", "claude-sonnet-5.5", "claude-opus-5.5"],
}
