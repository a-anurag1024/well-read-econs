"""End-to-end test of runner, report and Gate 1 with a fake model (no API, no money)."""
import hashlib
import json
import random

from wre import report, runner
from wre.models import REGISTRY, ModelSpec
from wre.tasks import build_all


def _fake_call_factory(strength_by_model):
    def call(clients, spec, prompt):
        rng = random.Random(int(hashlib.sha256((spec.key + prompt).encode()).hexdigest()[:8], 16))
        it = next(i for i in build_all(0) if i.prompt == prompt)
        k = strength_by_model[spec.key]
        hi = it.condition == "hi"
        if it.task == "framing":
            p = 0.5 + (0.3 * k if hi else -0.3 * k)
            sure = it.meta["sure"]; other = "B" if sure == "A" else "A"
            text = sure if rng.random() < p else other
        elif it.task == "forbid":
            p = 0.4 + (0.25 * k if hi else -0.25 * k) * 1.0
            yes = rng.random() < (1 - p if it.meta["wording"] == "allow" else p)
            text = "Yes" if yes else "No"
        elif it.task == "sunkcost":
            text = str(min(9, max(1, round(rng.gauss(7 + (0.6 * k if hi else 0), 1.5)))))
        else:
            truth = it.meta["truth"]
            text = "more\n" + str(round(truth * (1 + (0.9 * k) * (1 if hi else -0.5) * rng.random() + rng.random() * 0.1)))
        return {"text": text, "in_tok": 100, "out_tok": 10, "reasoning_tok": None, "stop": "stop",
                "err": None, "effort_used": None, "latency": 0.0, "cost": 0.0005}
    return call


def _register(tmp_models):
    for key, order, tier in tmp_models:
        REGISTRY[key] = ModelSpec(key, "openai", key, "chat", (1.0, 1.0), order, tier, [], 4, 1.0)


def test_pipeline_and_gate1(tmp_path):
    strengths = {"t-old": 1.0, "t-mid": 0.6, "t-new": 0.3, "t-top": 0.0, "t-top2": 0.0}
    _register([("t-old", 1, "small"), ("t-mid", 2, "mid"), ("t-new", 3, "mid"),
               ("t-top", 4, "frontier"), ("t-top2", 5, "frontier")])
    path = tmp_path / "r.jsonl"
    items = build_all(0)
    done = runner.done_keys(path)
    assert done == set()
    spent = 0.0
    for m in strengths:
        jobs = runner.jobs_for(REGISTRY[m], items)
        spent, _per, skipped = runner.run_jobs(jobs, runner.Clients(), path, 100.0, spent,
                                              call=_fake_call_factory(strengths))
        assert skipped == 0
    recs = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(recs) == 5 * len(items) * 4
    # resume: nothing left to do
    assert all((m, i.id, r) in runner.done_keys(path) for m in strengths for i in items for r in range(4))
    res = report.summarize(recs, n_boot=200)
    assert res["t-old"]["framing"]["fresh"] > res["t-top"]["framing"]["fresh"] + 0.5
    assert abs(res["t-top"]["framing"]["fresh"]) < 0.6
    g = report.gate1(res)
    assert g["G1b_pass"] and g["G1a_invalid"] == []
    assert "Human reference" in report.render(res)


def test_cap_stops_spending(tmp_path):
    _register([("t-cap", 1, "small")])
    REGISTRY["t-cap"].cap = 0.01
    items = build_all(0)
    _spent, per, skipped = runner.run_jobs(runner.jobs_for(REGISTRY["t-cap"], items), runner.Clients(),
                                          tmp_path / "c.jsonl", 100.0, call=_fake_call_factory({"t-cap": 0.5}))
    # in-flight calls (6 workers) can finish after the cap trips: bound = cap + workers * cost/call
    assert per["t-cap"] <= 0.01 + 6 * 0.0005 + 1e-9 and skipped > 0


def test_cli_refuses_without_yes(capsys):
    import pytest
    with pytest.raises(SystemExit) as e:
        runner.main(["run", "--lineup", "gate1"])
    assert "refusing" in str(e.value)


def test_dry_run_prints_costs(capsys):
    runner.main(["dry", "--lineup", "gate1"])
    out = capsys.readouterr().out
    assert "TOTAL" in out and "gpt-6-astra" in out


def test_spearman():
    assert report.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0


def test_diagnostics():
    from wre import diagnostics as d
    recs = [{"model": "m", "task": "framing", "version": "fresh", "err": None, "parsed": 1.0, "text": "B"}] * 20
    s = d.letter_shares(recs, "m")
    assert s["B"] == 1.0 and d.letter_biased(s)
    mixed = recs[:10] + [{**recs[0], "text": "A"}] * 10
    assert not d.letter_biased(d.letter_shares(mixed, "m"))
    f = []
    for cond, txt in (("hi", "Yes"), ("lo", "Yes")):
        f += [{"model": "m", "task": "forbid", "version": "fresh", "condition": cond, "err": None,
               "parsed": 0.0, "text": txt}] * 10
    y = d.yes_bias(f, "m")
    assert abs(y["acquiescence"] - 1.0) < 1e-9 and y["unparsed"] == 0.0
