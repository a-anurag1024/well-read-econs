# Run 4 plan (what do one-line instructions do?), fixed before any run 4 data

Written 2026-11-01, after run 3 (verdict HEADLINE FIRM). Not edited after data were seen; the one change is listed as a pre-run amendment at the bottom.

## Question
Runs 1 to 3 found that models differ in how Econ-like they are on the framing task: Sol and Astra show no effect (d = 0.00, 0.01), Sonnet 5.5 and Opus 5.5 show effects about three times the human size (d about +2.1; human d = 0.71). If you use a model as a synthetic respondent, can a short instruction move it to human size, and does it overshoot into caricature?

## What is varied
One instruction line is put in front of the otherwise unchanged prompt. Fixed wording, no per-vendor edits:

| tag | text placed before the prompt |
|---|---|
| `typical` | "You are a typical adult taking part in an online survey. Answer the way you would honestly answer, as an ordinary person, not as an expert." |
| `gut` | "Go with your first gut feeling. Do not calculate or analyze anything; answer quickly and intuitively." |
| `rational` | "Answer as a perfectly rational economic decision-maker would." |
| `none` (baseline) | nothing; taken from the existing runs, see below |

`typical` and `gut` are the "human" prompts; they say nothing about framing, sunk costs or any bias, so they do not name the effect. `rational` is the opposite-direction control. Two human wordings are used so that a result cannot rest on one phrasing.

Left out to stay inside the budget: random sociodemographic personas, few-shot human answers, and an explicit "be biased" upper bound.

## Tasks and items
- **Framing (primary):** the 48 fresh prompts of `framing_v2` (12 scenarios x two label formats x gain/loss; certain option first in half of each format). The four canonical-item prompts are not used.
- **Sunk cost (secondary, descriptive):** the 24 fresh `v1.1` prompts (12 events x paid/free), 1 to 9 rating. The two canonical prompts are not used.
- Same seed (0) as the baseline runs, so item ids and wording are identical to baseline except for the added line. Items: `items/prompting.jsonl`.

## Models
Anchors (the verdict uses only these): `gpt-6.1-sol`, `gpt-6-astra`, `claude-sonnet-5.5`, `claude-opus-5.5`.
Also run, reported but not in the verdict: `gpt-4o`, `gpt-4.1` (both exaggerate at baseline), `gpt-5-mini` (baseline close to human). Haiku 4.5 and the four format-sensitive models are excluded (run 3 flags).
Effort settings as in runs 1 to 3 (low for reasoning-capable models), provider default sampling.

## Baseline (no new calls)
Reused from earlier runs on the same items: framing fresh prompts from `data/run3_framing_openai.jsonl` and `run3_framing_anthropic.jsonl`; sunk cost `v1.1` from `data/run2_openai.jsonl` and `run2_anthropic.jsonl`. Caveat stated in advance: baseline and persona runs come from the same calendar day for OpenAI and Anthropic aliases, but answers per prompt differ, and model aliases may be updated by the vendor; differences are therefore between runs, not between interleaved calls. One scenario is missing from the Astra framing baseline (11 of 12); each cell is analysed on the items it has.

## Sampling and spend
2 answers per prompt for every model except `gpt-6-astra` (1). 72 prompts x 3 instructions per model. Global cap **$2.00**, `--yes` required, per-model caps as in `models.py`. A stage-0 check (one prompt per task and instruction per model, a few cents) runs first to confirm the instruction does not break parsing. One run only: no re-runs with altered wording or items if the verdict is unwelcome.

## Measures
- Framing: Cohen's d (log-odds estimator, gain frame = hi) per model and instruction, pooled over formats, 90% CI by resampling scenarios (item-level cluster bootstrap); P(certain option) in each frame; share of answers choosing the first-listed option; parse rate.
- Sunk cost: pooled-SD d of paid minus free rating, same CI method.
- Human reference: framing d = 0.71, sunk cost d = 0.27 (Many Labs 1, this package's estimator; `src/wre/human_reference.py`).

## Bands (applied to the point estimate)
Framing d: **reversed** < -0.15; **Econ** -0.15 to 0.15; **weak** 0.15 to 0.36; **human-sized** 0.36 to 1.42 (within a factor of two of 0.71); **exaggerated** > 1.42.
Sunk cost d: human-sized band 0.14 to 0.54 (a factor of two around 0.27); reported only.

## Validity
- A cell (model x instruction) is **invalid** if fewer than 90% of answers parse, or if at least 95% of answers in either label format are on one label or one position (the run 3 bias rule). Invalid cells are reported and count as "not human-sized" in the verdict. They are not repaired by re-wording.
- Mean output tokens and the share of answers with text beyond the answer are reported per cell.

## Pre-registered claims and how each is judged
- **C1 Calibration (anchors, framing).** An anchor is *calibrated by prompting* if its framing d is human-sized under **both** `typical` and `gut` and both cells are valid. It is *partly* calibrated if human-sized under exactly one. Otherwise: *immovable* (not human-sized and below 0.36 under both), *still exaggerated* (above 1.42 under both), or *mixed*.
- **C2 Overshoot.** Any model whose baseline d is at or below 1.42 and whose d under `typical` or `gut` is above 1.42 is flagged as overshooting (caricature). Reported for all seven models.
- **C3 Steering to Econ.** For the five models with baseline d at or above 0.36 (all except Sol and Astra), `rational` steers to Econ if framing d is below 0.15. Count and list.
- **C4 Wording check.** For every model, whether `typical` and `gut` fall in the same band. Disagreement means the result depends on wording and is stated as such.
- **Verdict (anchors only).** PROMPTING CALIBRATES if all four anchors are calibrated. PROMPTING CALIBRATES SOME if one to three are, with the others named and classified. PROMPTING DOES NOT CALIBRATE if none is.
- **Sunk cost (descriptive, no gate).** d per instruction against human 0.27; whether the sign of the change from baseline matches the sign of the framing change, per model and instruction.
- Anything else (plots, per-item breakdowns, token use) is exploratory and labelled so.

## Guardrails
- Results describe these items, one-line instructions, low reasoning effort, and OpenAI and Anthropic models on 2026-11-01. They do not show that models "have" human preferences, or that a calibrated d means the model behaves like people on other tasks.
- A model moving into the human-sized band is a statement about one effect size on twelve scenarios, with wide intervals; do not read it as a precise match.
- Report nulls: an instruction that changes nothing is a result.

## Pre-run amendment A1 (2026-11-01, BEFORE any run 4 data)
The sampling line above ("2 answers per prompt, Astra 1") was written before pricing it with measured per-call costs from the earlier runs (per 1,000 calls on similar prompts: Opus about $2.5 to $3.0, Astra about $1.7, Sonnet about $0.5 to $0.9, Sol about $0.4, gpt-4o about $0.26, gpt-4.1 about $0.21, gpt-5-mini about $0.06; the added instruction lengthens the input by about 30%). At 2 answers per prompt the plan would cost about $3, above the $2.00 cap. Changed before any data: **1 answer per prompt for every model except `gpt-6.1-sol` (2)**, which gives about $1.7 expected. Because the unit of analysis is the scenario (12 per format) and the human-sized band is a factor of two wide, one answer per prompt is enough to classify most cells, but intervals will be wide and cells near a band edge will be reported as such. The per-model cap for `gpt-6-astra` rises from $0.40 to $0.55 so that it can finish at 1 answer per prompt (216 calls). The global cap stays $2.00 and all rules and bands are unchanged.
