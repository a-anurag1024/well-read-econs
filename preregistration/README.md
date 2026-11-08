# Preregistration

Four plans, one per run. Each was written to a dated file before the run it governs and states
the decision rules in advance. They are published here as written, with working notes removed and
internal labels renamed ("Gate 1" became "run 1", and so on).

| File | Governs | Data |
|---|---|---|
| [run1-plan.md](run1-plan.md) | 13 OpenAI models, four tasks | `data/run1_openai.jsonl` |
| [run2-plan.md](run2-plan.md) | 3 Anthropic models, plus OpenAI re-run on revised items | `data/run2_*.jsonl` |
| [run3-framing-plan.md](run3-framing-plan.md) | framing robustness (position and label format) | `data/run3_*.jsonl` |
| [run4-prompting-plan.md](run4-prompting-plan.md) | one-line instructions | `data/run4_prompting.jsonl` |

Item sets are frozen in [`items/`](../items) with SHA-256 hashes in `MANIFEST.json`
(`python -m wre.freeze --check` verifies them).

## What this is, and what it is not
- **Not an external registration.** The plans were not submitted to a registry such as OSF or
  AsPredicted. The dates inside them are the author's record; this repository cannot prove when
  they were written.
- **Amendments are labelled.** Each plan lists changes made after it was written and says whether
  each was made *before any data* or *after results were seen*. Changes made after results were
  seen only add validity checks or disclose a deviation; none changed a pre-registered verdict.
- **Spend caps were part of the plans.** Where a cap was exceeded (calls in flight finish after a
  cap is reached) the run's results file says by how much.
- **Verdicts are mechanical.** Each plan's verdict is computed by code (`wre.report`, `wre.gate2`,
  `wre.robust`, `wre.part2`); `python analysis/reproduce.py` regenerates all of them.
