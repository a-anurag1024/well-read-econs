# Run 2 plan (Anthropic lineup, plus OpenAI re-run on revised items), fixed before any run 2 data

Written 2026-11-01, after run 1 and after a stage-0 check on the Anthropic models. Not edited after run 2 data were seen; changes are listed under the amendments.

## What changed since run 1 (item revisions "v1.1", made before collecting any new data)
1. **Allowed/forbidden:** run 1 topics were at floor (11 of 13 models answered 0% restrictive in both wordings). The new fresh items are 12 mid-controversy practices phrased "the law should allow/forbid ...", plus the unchanged democracy-speech canonical item. "Restrictive" means the practice is not permitted ("No" to allow, "Yes" to forbid). The human effect for the new topics is not verified; the human reference remains the Many Labs democracy-speech item, so indexes for this task are rough.
2. **Sunk cost:** the free condition now reads "The ticket was free: you got it in a promotional giveaway" (v1: "a free gift", which adds a social-obligation cue). The paid wording and the canonical items are unchanged.
Item ids for changed fresh items carry "-v11". Framing and anchoring items are identical to run 1. Items: `items/main.jsonl`.

## Runs (two, each with its own results file and spend cap)
- **Run A, Anthropic (all four tasks, 100 prompts per answer):** claude-haiku-4.5 (6 answers per prompt, no thinking), claude-sonnet-5.5 (4, effort low), claude-opus-5.5 (3, effort low; thinking cannot be disabled). Provider-default sampling. Global cap $1.20; per-model caps $0.20 / $0.40 / $0.60. Stage 0 measured 3.7 to 40.7 output tokens per call.
- **Run B, OpenAI re-run (allowed/forbidden and sunk cost only):** the 13 run 1 models on the v1.1 items, same answers per prompt and effort settings as run 1. Global cap $0.60.
- Release order for Anthropic models: haiku-4.5 = 14, sonnet-5.5 = 15, opus-5.5 = 16 (author's judgement). They are a separate vendor series; no cross-vendor release-order claims are made.

## Pre-registered checks (descriptive; no later paid stage is conditional on them except where stated)
- **G2a Validity:** as in run 1 (parse at least 90%, truncated under 5% per cell). If an Anthropic cell fails because of formatting, one repair round (within caps), logged.
- **G2b Does allowed/forbidden now discriminate?** The v1.1 task counts as discriminating if, among all 16 models, at least 8 have P(restrictive) between 0.05 and 0.95 in at least one wording. If not: the task is demoted to a supplementary result and not used in headline claims.
- **G2c Is the sunk-cost signal wording-driven?** Compare frontier models (gpt-6.1-sol, gpt-6-astra, claude-opus-5.5) before and after the wording fix. If their fresh d falls below 0.15 or its 90% CI includes 0 after the fix, report the earlier signal as a wording artifact. If it stays at +0.15 or above with the interval excluding 0, report it as paid-vs-free sensitivity (not "sunk-cost bias").
- **G2d Frontier framing across vendors:** report whether claude-opus-5.5 and claude-sonnet-5.5 show a framing effect (fresh d with 90% CI), next to Sol and Astra.
- **The prompting experiment (run 4) is not gated by G2b to G2d.** It is gated only by the rule that at least one frontier model has Econ-ness index below 0.5 on at least one task. That was already met on framing in run 1 (Sol and Astra, index 0.0).

## Interpretation guardrails (as in run 1, plus)
- Differences between vendors are reported, never ranked as better or worse; a vendor can be more Econ-like because of design choices not visible here.
- Anthropic results come from low-effort settings (Opus, Sonnet) and the default setting (Haiku). How results change at higher effort is unknown.
- Each task family has a fixed small set of templates; all effects describe these items only.

## Post-run amendment A1 (2026-11-01, made BEFORE any run 2 result was examined; only run logs and costs had been read)
Run A: Opus 5.5 reached its $0.60 per-model cap after 268 of 306 planned calls, because its thinking tokens at low effort averaged about 100 output tokens per call, not the 40 seen in stage 0 (cost per call about 2.4 times the estimate). The 38 skipped calls were all in the allowed/forbidden task (14 of 26 item-conditions covered). To complete the planned answers, the Opus cap was raised to $0.75 (expected extra cost about $0.10) and the same command resumed. No other rule changed; the total budget for run 2 ($2.50) is unaffected.

## Post-run amendment A2 (2026-11-01, made AFTER run 2 results were seen; disclosed as post hoc)
Reading the run 2 effect sizes showed that a zero or reversed effect can be a response-style artifact, so two diagnostics were added (`wre.diagnostics`) and applied to ALL models, not only the ones that looked odd:
- **Letter bias (framing):** a model whose answers are at least 95% one letter has a framing effect of zero by construction. Applied result: claude-haiku-4.5 answered "B" on 100% of framing prompts; its framing result is excluded from interpretation. No other model is flagged. (Sol and Astra answer "A" on 25%, which equals the share of items where the certain option is "A" in this item set: they pick the certain option, not a letter.)
- **Acquiescence (allowed/forbidden):** P(yes|allow) + P(yes|forbid) - 1; 0 means consistent, positive means yes-bias, negative means no-bias. Also the share of unparseable answers (refusals).
These checks were not in the pre-registered rules. They only add validity flags; they did not change any verdict. The Opus allowed/forbidden cell was already invalid under G2a (parse 46%); the unparsed answers are refusals to give a personal verdict, not formatting errors, so no repair round was run.
An item-set imbalance was noticed: in the framing items the certain option appears first ("A") in only 25% of fresh items (3 of 12, by seed). Effects are unaffected within an item (both frames share the position) but position effects are not balanced. Run 3 tests this.
