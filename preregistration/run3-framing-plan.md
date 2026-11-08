# Run 3 plan (framing robustness check), fixed before any run 3 data

Written 2026-11-01, after run 2. Not edited after data were seen; the one change is listed under the pre-run amendment.

## Why
The headline contrast from runs 1 and 2 (Sol and Astra show no framing effect; Sonnet 5.5 and Opus 5.5 show effects larger than human; Haiku letter-biased) rests on one prompt format in which the certain option is listed first in only 25% of fresh items. This check asks whether it survives balanced positions and a different label format.

## Design (`wre.tasks.framing_v2`, `items/framing_v2.jsonl`)
- The same 12 fresh scenarios and numbers as in run 1 framing (equal expected value in both frames), plus the canonical Asian-disease item.
- Two label formats: **A/B plans** ("Plan A / Plan B", answer a letter) and **1/2 options** ("Option 1 / Option 2", answer a number). Each scenario appears in both formats.
- **Position balanced:** in each format the certain option is listed first in exactly 6 of 12 scenarios; across the two formats each scenario has the certain option in each position once. Both frames of a scenario share the position, as before.
- Canonical item: gain and loss frames, certain option first and second (4 prompts), A/B format.
- 52 prompts per answer. The item key for bootstrap clustering is the scenario (both formats together).

## Models and sampling
All 16 models of runs 1 and 2, same effort settings (6 small and 5 mid-priced OpenAI, 4 Sonnet, 3 Opus, 3 Sol, 2 Astra, 6 Haiku answers per prompt before the amendment below). Provider-default sampling. Global cap $0.90; per-model caps as in `models.py`.

## Outcomes
- Fresh-item framing d (log-odds estimator, hi = gain frame) pooled over formats and per format, with 90% CI resampling scenarios; P(choose certain option) under each frame; share of answers choosing the first-listed option; letter or position bias (at least 95% of answers on one label or one position).
- Human reference: d = 0.71 (certain option chosen 0.655 in the gain frame, 0.345 in the loss frame).

## Pre-registered claims and how they are judged
- **R1 Econ pattern replicates** for gpt-6.1-sol and gpt-6-astra if, for each, pooled d < 0.15 AND P(certain) >= 0.90 in both frames.
- **R2 Exaggeration replicates** for claude-sonnet-5.5 and claude-opus-5.5 if, for each, pooled d >= 1.0 and d >= 1.0 in each of the two formats separately.
- **R3 Format robustness** per model: |d(A/B) - d(1/2)| <= 0.6 means format-robust; otherwise the model is flagged format-sensitive and its run 1 and 2 value is not to be quoted as a clean model property.
- **R4 Position or letter bias:** a model with at least 95% of answers on one label or one position in either format is flagged; its framing d is excluded from interpretation (as for Haiku in run 2).
- **Verdict.** HEADLINE FIRM if R1 holds for both Sol and Astra and R2 holds for both Claude models. HEADLINE PARTIAL if R1 holds but R2 fails for one or both (Claude exaggeration reported as format-dependent). HEADLINE NOT SUPPORTED if R1 fails for either (the Econ pattern was a formatting artifact). Informational only: Spearman correlation of the 16 models' d between runs 1 and 2 and this run.
- No other analyses are gates. Anything else is labelled exploratory.

## Guardrails
- Effect sizes describe these items, one prompt style per format, and low reasoning effort for reasoning-capable models.
- If a model's answers are unparseable (under 90%), the cell is invalid and reported, not repaired by re-wording for that vendor only.
- One run only. No re-runs with altered items if the verdict is unwelcome.

## Pre-run amendment A1 (2026-11-01, BEFORE any run 3 data)
The dry-run cost with the full answers per prompt of runs 1 and 2 was about $0.9 to $1.0, about twice the roughly $0.5 first estimated (the first estimate did not account for this set being twice as large as the old framing set: 52 prompts instead of 26). To stay near the estimate, every model answers at most 3 times per prompt (`--max-reps 3`): Haiku, Sonnet, Opus and all mid and small OpenAI models 3, Sol 3, Astra 2. With 12 scenarios per format this keeps the item-level design intact; per-prompt sampling noise is larger than in run 2, so per-model CIs are wider. Spend limits: OpenAI run capped at $0.40, Anthropic run at $0.50 (total $0.90). Verdict rules unchanged.
