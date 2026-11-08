# Run 1 plan (OpenAI lineup), fixed before any run 1 data

Written 2026-11-01. Not edited after data were seen; changes are listed under "Pre-run amendments".

## What runs
- Tasks: framing, sunk cost, anchoring, allowed/forbidden. 100 prompts per answer (a canonical pair plus 12 fresh pairs for framing, sunk cost and allowed/forbidden; 12 fresh pairs for anchoring), from `items/main_run1.jsonl`.
- Models: see the amended lineup below.
- Answers per prompt: 6 for non-frontier models, 3 for gpt-6.1-sol, 2 for gpt-6-astra. Provider-default sampling; reasoning effort set to the lowest setting the API accepts, recorded per row.
- The order of release used for the trend rule is the author's ordinal judgement (`ModelSpec.order`), not a vendor number.
- A stage-0 check first: 3 prompts per model, to measure tokens and detect unsupported parameters. After it, the cost projection is recomputed with measured output tokens and per-model caps are checked.

## Spend limits
Global cap $1.50. Per-model caps in `src/wre/models.py` ($0.10 to $0.45). The runner stops a model when its cap is reached; a stopped model is reported as partial and excluded from the rules unless it has at least 60% of its planned answers. If the projected cost after stage 0 exceeds the global cap, answers per prompt for the expensive models are reduced (not the item set) and the change is logged before running.

## Effects
Cohen's d (hi minus lo condition) from `wre.effects`: log-odds estimator for binary tasks (framing, allowed/forbidden), standardized mean difference for sunk cost, rank-transformed within item for anchoring. 90% bootstrap intervals resampling items. Human references: `wre.human_reference` (Many Labs 1 and its supplement).

## Rules
- **G1a Validity.** A (model, task) cell is valid if at least 90% of answers parse and fewer than 5% are truncated. Invalid cells are excluded from G1b and G1c and reported. If more than 25% of cells are invalid, prompts or parsers are fixed and the affected models rerun before applying G1b and G1c (one repair round, within the cap).
- **G1b Variation.** The spread of fresh-item d across valid models (max minus min) is at least 0.4 in at least two tasks. Otherwise the benchmark does not separate models.
- **G1c Something to explain.** At least one of:
  - (i) a frontier model (gpt-6.1-sol or gpt-6-astra) has fresh d of at least +0.30 with the 90% interval excluding 0 on some task; or
  - (ii) a clear generation trend: on some task, Spearman correlation of release order with fresh d is at most -0.5 across at least 5 valid models, and the oldest valid model has fresh d of at least +0.30 with the interval excluding 0.
- **Verdict.** Continue to run 2 only if G1a is clean, G1b passes and G1c passes. If G1b fails: stop and write up (the benchmark does not discriminate). If G1b passes but G1c fails: the data show a flat world of Econs or noise; pause and decide whether to write up the generations curve as is or stop.
- Nothing else is a gate. Extra analyses (canonical vs fresh gap, Econ-ness index) are descriptive and exploratory.

## Interpretation guardrails (stated in advance)
- Index values for anchoring are rough: the anchors used here differ from Many Labs'.
- Model effects larger than the human effect are exaggeration, not "more human".
- A zero effect is "no detectable effect at this power", not proof of rationality.
- Nothing about vendors other than OpenAI is claimed from run 1.
- Recognition of the test is not measured in run 1.

## Pre-run amendments (2026-11-01, made after the stage-0 check and BEFORE any run 1 data)
Stage 0 (3 prompts per model, $0.008 total) found that `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo` and `o4-mini` are deprecated (HTTP 404) although the models endpoint lists them. Changes to the lineup, all made without seeing any benchmark data:
- Removed gpt-3.5-turbo. The oldest callable model is gpt-4o, so the generations curve spans 2024 to 2026, not 2023 to 2026.
- Added gpt-5.1 and gpt-5.2 (both respond; they fill the gap between gpt-5 and gpt-5.4-mini). The lineup is 13 models: gpt-4o, gpt-4o-mini, gpt-4.1-mini, gpt-4.1, gpt-5-nano, gpt-5-mini, gpt-5.1, gpt-5.2, gpt-5.4-mini, gpt-5.6-luna, gpt-6-luna, gpt-6.1-sol, gpt-6-astra.
- Answers per prompt: 6 for small models; 5 for gpt-4o, gpt-4.1, gpt-5.1, gpt-5.2; 3 for Sol; 2 for Astra (the four mid-priced models reduced from 6 to 5 to stay inside the cap).
- Measured output was 2 to 20 tokens per call for every model, including Astra at low effort, so the placeholder of 400 tokens for frontier models was dropped from the projection. Projected cost with measured tokens: about $1.15 (cap $1.50). Prices for gpt-4o, gpt-4.1, gpt-5.1, gpt-5.2 come from third-party aggregators that agree with each other; gpt-6-luna from one third-party summary.
- Reasoning effort per model (first accepted by the API, recorded per row): gpt-5-nano and gpt-5-mini minimal; gpt-5.1, gpt-5.2, gpt-5.4-mini, gpt-5.6-luna and gpt-6-luna none; gpt-6.1-sol and gpt-6-astra low.
The rules G1a to G1c, the global cap and the verdict logic are unchanged.
