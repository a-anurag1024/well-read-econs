# Limitations

**What the results are.** Effect sizes for specific items, one prompt style per format, low reasoning effort for reasoning-capable models, and one snapshot of each model on 2026-11-01.

**What they are not.**
- Not a ranking of vendors or models, and not evidence about why a model behaves as it does. A vendor may be more Econ-like because of choices not visible here.
- Not evidence that a model "has" preferences or biases. A model that matches the human effect on one task need not match it on another, and matching an average effect size says nothing about matching the distribution of human answers.
- Exaggeration (an effect larger than the human one) is not "more human".
- A zero effect means no detectable effect at this sample size, not proof of rationality. Two models (`gpt-6.1-sol`, `gpt-6-astra`) choose the certain option every time, so their intervals are degenerate.

**Design limits**
- 12 scenarios per task, written for this project. Per-model intervals are wide, and model-by-task claims rest on one set of items.
- 1 to 6 answers per prompt, fewer for expensive models. Run 4 has one answer per prompt (two for `gpt-6.1-sol`), so cells near a band edge are not precise.
- The human reference values come from one multi-lab replication using different vignettes. For anchoring the model items use different quantities from Many Labs, so the comparison with 1.9 is rough; for allowed/forbidden the model topics are not the Many Labs topic, so the human value is only a rough guide.
- Canonical items paraphrase the published tasks and may not match the original wording; no headline result depends on them.
- The framing effect is measured only with a certain-versus-risky choice at equal expected value; the sunk-cost task is a rating of attendance, not a behavior.
- Only OpenAI and Anthropic models; no open-weight models, no other vendors. Model identifiers are aliases, not dated snapshots.
- Higher reasoning effort or other sampling settings could change results; this was not tested.
- Test awareness (a model recognizing a famous task) was not measured, so the results cannot separate reasoning from recognition of the canonical wording. The fresh items reduce but do not remove that possibility.

**Process limits**
- The preregistration is not in an external registry. The plans are dated records written before each run; this repository cannot prove when they were written.
- Some checks were added after results were seen (response-style diagnostics, disclosed in `preregistration/run2-plan.md`); none changed a pre-registered verdict. The anchoring analysis keeps items with identical answers in both conditions at zero effect; this was changed after the first look at the run 1 data (it had dropped them, which inflated the effect) and the stop/continue verdict was unchanged.
- In runs 3 and 4 a spending cap is checked between calls, so calls in flight finished after it was reached; run 3 overshot its $0.90 cap by $0.025.
