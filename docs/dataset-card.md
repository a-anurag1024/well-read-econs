# Dataset card

Model calls collected for the Econ Test, in `data/`. 15,658 rows, JSON lines, UTF-8.

| File | Rows | Run |
|---|---|---|
| `run1_openai.jsonl` | 6,700 | 13 OpenAI models, four tasks (first item wording) |
| `run2_openai.jsonl` | 3,484 | the same 13 models on revised sunk-cost and allowed/forbidden items |
| `run2_anthropic.jsonl` | 1,326 | 3 Anthropic models, four tasks (revised items) |
| `run3_framing_openai.jsonl` | 1,957 | framing robustness, OpenAI |
| `run3_framing_anthropic.jsonl` | 463 | framing robustness, Anthropic |
| `run4_prompting.jsonl` | 1,728 | one-line instructions, 7 models |

## Fields
`model` (registry key, see `src/wre/models.py`), `id` (item id, matches `items/`), `task`, `version` (`canonical` or `fresh`), `condition` (`hi` or `lo`), `item_key` (groups the two conditions of a scenario), `rep` (answer number for that prompt), `text` (the model's raw output), `parsed` (the scored answer or null if unparseable), `err` (API error string or null), `in_tok`, `out_tok`, `reasoning_tok`, `stop`, `effort_used` (reasoning effort actually accepted), `latency` (seconds), `cost` (USD, computed), `order` and `tier` (registry metadata), `meta` (item metadata such as label format, certain-option position and, in run 4, the instruction tag; absent in run 1).

Prompts are not stored in the rows; each is the prompt in `items/*.jsonl` with the same `id`.

## Collection
All calls on 2026-11-01, one request per answer, provider-default sampling. Settings per model (reasoning effort, answers per prompt) are in the registry and in each plan. Zero API errors in any file; rows with unparseable answers have `parsed = null`.

## Things to know before reusing it
- **Model versions are aliases.** Rows record the identifier requested (for example `gpt-6.1-sol`, `claude-opus-5.5`), not a dated snapshot, because the responses were not checked for a resolved version string. A vendor may later change what an alias returns.
- **`cost` is an estimate.** It is tokens times the per-million prices in `models.py`. Several prices came from third-party sources (noted in the registry) rather than a vendor price page.
- **Unequal sampling.** Answers per prompt differ by model and run (1 to 6). Incomplete cells are documented in the plans and results (for example `gpt-6-astra` and `claude-opus-5.5` in run 3).
- **Refusals and hedges** are kept as raw text with `parsed = null`; `claude-opus-5.5` gives no parseable answer on 54% of allowed/forbidden prompts.
- **Not a sample of people.** These are model outputs, not human data. The human reference values are in `src/wre/human_reference.py` with their source.

Licence: MIT (code) and the same terms for the data, which are model outputs on prompts written for this project. Model outputs may be subject to the providers' terms of use.
