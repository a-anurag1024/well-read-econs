# The project, explained plainly

This page explains every technical idea used in the repository, in the order you meet them, with
worked examples from the real data. If you only read one document besides the README, read this one.
Every number below can be checked against the files in `data/` and `analysis/results/`.

## 1. The question in one sentence
When you ask an AI model a question from behavioral economics, does it answer like a perfectly
rational agent (an **Econ**), like a typical person (a **Human**), or does it overshoot the human
pattern?

The words come from Richard Thaler's *Misbehaving*: Econs ignore things that shouldn't matter
(how a choice is worded, money already spent); Humans don't.

## 2. How one test works
Take the **framing** test. The same choice is described two ways:

> A wildfire is approaching a mountain town where 840 residents have not yet evacuated.
> *Gain wording:* "280 of the 840 residents will be evacuated safely" (sure) or "a one-in-three chance
> that all 840 residents will be evacuated safely, and a two-in-three chance that none will be" (gamble).
> *Loss wording:* "560 of the 840 residents will be left behind" (sure) or "a one-in-three chance that
> none of the residents will be left behind, and a two-in-three chance that all 840 will be" (gamble).

Both wordings describe the same outcomes with the same expected result. An Econ picks the same
option either way. People pick the sure option more often in the gain wording (65.5% of people) than in
the loss wording (34.5%). That difference is the **framing effect**.

Vocabulary used throughout:
- **Item / scenario:** one story (the wildfire, a factory closing, ...). I wrote 12 per test.
- **Condition:** which wording a question uses (here "gain" or "loss"; in the code "hi" and "lo", meaning
  the condition in which people score higher).
- **Answer / call:** one reply from a model to one prompt. Each prompt is asked several times, because
  models can answer differently each time.
- **Canonical vs fresh:** *canonical* = a paraphrase of the textbook version of the question (for
  example the "Asian disease" problem); *fresh* = a story I wrote with the same structure but different
  surface details. All headline results use fresh items.

## 3. The two ways of reporting an effect
### Percentage points (used in the README)
Count how often a model chose the sure option under each wording and subtract. Example (framing,
`data/run3_*`, fresh items, both label styles, 72 answers per wording):

| | gain wording | loss wording | swing |
|---|---|---|---|
| People (study) | 65.5% | 34.5% | 31 points |
| `claude-sonnet-5.5` | 71/72 = 99% | 36/72 = 50% | 49 points |
| `claude-opus-5.5` | 72/72 = 100% | 53/72 = 74% | 26 points |
| `gpt-6.1-sol` | 72/72 = 100% | 72/72 = 100% | 0 points |

### Cohen's d (used in the technical results)
**Cohen's d** puts an effect on a scale that doesn't depend on units, so a framing effect (percent
choosing an option), a sunk-cost effect (a 1-to-9 rating) and an anchoring effect (a number
estimate) can sit on one scale. Rough rule of thumb from Cohen: 0.2 small, 0.5 medium, 0.8 large.

For a yes/no outcome I use the **log-odds** version: take the odds of choosing the sure option under
each wording (odds = p / (1 - p)), divide one by the other (the *odds ratio*), take the natural log,
and multiply by sqrt(3)/pi (about 0.551).

Worked example for people: odds under gain wording = 0.655 / 0.345 = 1.90; under loss wording
0.345 / 0.655 = 0.53; odds ratio = 3.6; ln(3.6) = 1.28; times 0.551 = **0.71**.

For models the same formula is used with a **small correction** (add half an answer to every count) so
that 72 out of 72 doesn't produce infinity. That gives `claude-sonnet-5.5` d = 2.13, `claude-opus-5.5`
d = 2.19, `gpt-6.1-sol` d = 0.00.

### Why the two can disagree
Look at Opus: its swing in points (26) is *smaller* than people's (31), yet its d (2.19) is *larger*
than people's (0.71). That is not a mistake. Near 100%, a small drop in percentage (100% to 74%)
is a large change in odds, and d measures odds. So d exaggerates differences between models that sit
near always-yes or always-no.

That is why the README uses percentage points: they are easy to check and don't have this quirk. The
technical results keep d because it is the standard way to compare against published studies, and
because the sunk-cost and anchoring tasks can't be expressed as percentages. When a claim depends on
d near the ceiling, read it with this caveat.

## 4. How sure are we? (intervals)
Any number from a small sample would change a little if I had written different scenarios. To show
how much, I use a **bootstrap interval**: redraw 12 scenarios *with replacement* from the 12 I have
(so some repeat and some drop out), recompute the effect, repeat 2,000 times, and report the middle
90% of results. A narrow interval means the effect doesn't depend much on which scenarios were drawn.

Why resample scenarios and not individual answers? Because what I want to generalize to is "other
similar stories", not "more answers to the same story". This is the **item is the unit of
replication** rule. It makes intervals wider (and more honest) than treating all answers as independent.

A model that gives the same answer every time (Sol and Astra choose the sure option 100% of the time)
has an interval of exactly zero width. That reflects no variation in the data, not perfect certainty.

## 5. Checking it isn't a trick of formatting
A model could look like an Econ simply because it always answers "A", or because the sure option was
listed first. Three checks, all in `analysis/results/run3_framing_robustness.txt`:
- **Balanced positions:** the sure option is listed first in exactly half the questions.
- **Two label styles:** "Plan A / Plan B" and "Option 1 / Option 2". A model whose effect changes by
  more than 0.6 d between the two is marked **format-sensitive** (four OpenAI models).
- **Position bias:** a model that picks one position (or label) in at least 95% of answers is marked
  **biased** (Claude Haiku 4.5 picks the second-listed option 92% of the time, so its framing result
  means nothing).

An **invalid cell** is a (model, test) result that fails a check (fewer than 90% of answers could be read, or
at least 95% of answers on one label). Invalid cells are reported but never repaired or counted.

## 6. The other tests
- **Sunk cost:** rating (1 to 9) of how likely you are to go to an event in bad weather, when the ticket
  was paid for versus free. Econs ignore what was paid. People rate about 0.6 points higher when paid.
  Our model results show a *paid-versus-free sensitivity*, which is not the same as proving the
  sunk-cost fallacy (the paid wording also mentions a price, which could matter for other reasons).
- **Anchoring:** the model sees a high or low "anchor" number, then estimates a quantity. Estimates are
  converted to ranks within each question so that quantities of different sizes can be compared.
  Anchoring was weak in every model, and my quantities differ from the study's, so I don't lean on it.
- **Allowed vs forbidden:** "should X be allowed?" vs "should X be forbidden?". Models mostly differ in
  whether they say "yes" or "no" regardless of wording, which the **acquiescence index**
  (P(yes | allow) + P(yes | forbid) - 1) captures: 0 = consistent, positive = yes-bias, negative = no-bias.
  People score -0.17. This test therefore measures response style rather than the human wording effect.

## 7. The prompting experiment
I put one line before each question and checked whether the model's pattern moved toward the human one:
- **typical:** "You are a typical adult taking part in an online survey..."
- **gut:** "Go with your first gut feeling..."
- **rational:** "Answer as a perfectly rational economic decision-maker would."

The pre-registered rule defined a model as *calibrated* if its framing d landed in the **human-sized
band** (0.36 to 1.42, within a factor of two of the human 0.71) under both human-style lines. No model
did. Each cell had one or two answers per question, so these results are noisier than the main run.

## 8. Pre-registration (decision rules written in advance)
Before each run I wrote down, in a dated file in `preregistration/`, what I would measure and how I
would decide what the result means. The point is to stop myself reading a favorable story into the data
after the fact. Anything changed later is listed as an **amendment** and marked either *before any
data* (harmless) or *after seeing results* (disclosed, and only ever added checks). This is not an
official registry, so the dates cannot be independently verified.

## 9. The run settings
- **Reasoning effort:** some models can "think" before answering; I used the lowest setting for cost.
  Results could differ with more thinking.
- **Alias, not snapshot:** I recorded the model name I asked for (for example `gpt-6.1-sol`), not a
  dated version, so the same name could later behave differently.
- **Spend caps:** the runner refuses to start without an explicit flag and stops at a dollar limit.
  Calls already in flight finish after the limit, so a cap can be overshot slightly (run 3 by $0.025).

## 10. Where each idea lives in the code
| Idea | File |
|---|---|
| Effect sizes, bootstrap intervals | `src/wre/effects.py` |
| Human reference numbers and their source | `src/wre/human_reference.py` |
| The tests and fresh items | `src/wre/tasks/` |
| Position, label and yes-bias checks | `src/wre/diagnostics.py`, `src/wre/robust.py` |
| Prompting experiment and its rules | `src/wre/part2.py` |
| Calling models with spend caps | `src/wre/runner.py` |
| Every table | `analysis/reproduce.py` |
| Every plain-percentage chart | `analysis/simple_charts.py` |
