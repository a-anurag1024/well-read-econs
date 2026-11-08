"""Run the benchmark against model APIs, with hard spend guards.

    python -m wre.runner dry    --lineup gate1
    python -m wre.runner stage0 --lineup gate1 --yes --out runs/stage0.jsonl
    python -m wre.runner run    --lineup gate1 --yes --cap 1.5 --out runs/gate1.jsonl

Nothing is sent without --yes. Keys are read from the environment (OPENAI_API_KEY,
ANTHROPIC_API_KEY); a .env file is loaded if python-dotenv is installed. Output is JSON lines,
resumable: completed (model, item, rep) triples are skipped on re-run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .models import LINEUPS, REGISTRY, ModelSpec
from .tasks import PERSONAS, TASKS, Item, build_all

MAX_OUT = 3000
_lock = threading.Lock()


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path.cwd() / ".env")
    except ImportError:
        pass


def est_tokens(text: str) -> float:
    return len(text) / 4 + 12


# ------------------------------------------------------------------- API calls

class Clients:
    def __init__(self) -> None:
        self._c: dict[str, object] = {}
        self.effort_used: dict[str, str | None] = {}

    def get(self, provider: str):
        if provider not in self._c:
            if provider == "openai":
                import openai
                self._c[provider] = openai.OpenAI()
            else:
                import anthropic
                self._c[provider] = anthropic.Anthropic()
        return self._c[provider]


def _is_param_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(w in msg for w in ("reasoning", "effort", "unsupported", "invalid_value",
                                  "max_tokens", "max_completion_tokens", "temperature"))


def call_model(clients: Clients, spec: ModelSpec, prompt: str) -> dict:
    t0 = time.time()
    out = {"text": "", "in_tok": 0, "out_tok": 0, "reasoning_tok": None, "stop": None,
           "err": None, "effort_used": None}
    try:
        if spec.api == "chat":
            c = clients.get("openai")
            try:
                r = c.chat.completions.create(model=spec.api_id, max_completion_tokens=MAX_OUT,
                                              messages=[{"role": "user", "content": prompt}])
            except Exception as e:
                if not _is_param_error(e):
                    raise
                r = c.chat.completions.create(model=spec.api_id, max_tokens=MAX_OUT,
                                              messages=[{"role": "user", "content": prompt}])
            out["text"] = r.choices[0].message.content or ""
            out["in_tok"], out["out_tok"] = r.usage.prompt_tokens, r.usage.completion_tokens
            out["stop"] = r.choices[0].finish_reason
        elif spec.api == "responses":
            c = clients.get("openai")
            efforts = spec.efforts
            if spec.key in clients.effort_used:
                efforts = [clients.effort_used[spec.key]]
            last = None
            for eff in efforts:
                try:
                    r = c.responses.create(model=spec.api_id, input=prompt,
                                           reasoning={"effort": eff}, max_output_tokens=MAX_OUT)
                    clients.effort_used[spec.key] = eff
                    out["effort_used"] = eff
                    break
                except Exception as e:
                    last = e
                    if not _is_param_error(e):
                        raise
            else:
                raise last  # type: ignore[misc]
            out["text"] = r.output_text or ""
            u = r.usage
            out["in_tok"], out["out_tok"] = u.input_tokens, u.output_tokens
            det = getattr(u, "output_tokens_details", None)
            out["reasoning_tok"] = getattr(det, "reasoning_tokens", None)
            inc = getattr(r, "incomplete_details", None)
            out["stop"] = getattr(inc, "reason", None) or r.status
        else:  # anthropic
            c = clients.get("anthropic")
            kw = {"model": spec.api_id, "max_tokens": MAX_OUT,
                  "messages": [{"role": "user", "content": prompt}]}
            eff = spec.efforts[0] if spec.efforts else None
            if eff:
                kw["extra_body"] = {"output_config": {"effort": eff}}
                out["effort_used"] = eff
            r = c.messages.create(**kw)
            out["text"] = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            out["in_tok"], out["out_tok"] = r.usage.input_tokens, r.usage.output_tokens
            out["stop"] = r.stop_reason
    except Exception as e:  # noqa: BLE001 - recorded in the output row, never crashes the run
        out["err"] = f"{type(e).__name__}: {str(e)[:240]}"
    out["latency"] = round(time.time() - t0, 2)
    p = spec.price
    out["cost"] = out["in_tok"] * p[0] / 1e6 + out["out_tok"] * p[1] / 1e6
    return out


# ------------------------------------------------------------------- jobs

def jobs_for(spec: ModelSpec, items: list[Item], reps: int | None = None) -> list[tuple[str, Item, int]]:
    n = reps if reps is not None else spec.reps
    return [(spec.key, it, r) for it in items for r in range(n)]


def done_keys(path: Path) -> set[tuple[str, str, int]]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not r.get("err"):
            keys.add((r["model"], r["id"], r["rep"]))
    return keys


def run_jobs(jobs, clients: Clients, path: Path, global_cap: float, spent0: float = 0.0,
             workers: int = 6, call=call_model) -> tuple[float, dict[str, float], int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    spent = {"t": spent0}
    per: dict[str, float] = {}
    skipped = {"n": 0}
    f = path.open("a", encoding="utf-8")

    def work(job):
        mk, it, rep = job
        spec = REGISTRY[mk]
        with _lock:
            if spent["t"] >= global_cap or per.get(mk, 0.0) >= spec.cap:
                skipped["n"] += 1
                return
        res = call(clients, spec, it.prompt)
        task = TASKS[it.task]
        res.update(model=mk, id=it.id, task=it.task, version=it.version, condition=it.condition,
                   item_key=it.item_key, rep=rep, order=spec.order, tier=spec.tier, meta=it.meta)
        res["parsed"] = None if res["err"] else task.parse(res["text"], it)
        with _lock:
            spent["t"] += res["cost"]
            per[mk] = per.get(mk, 0.0) + res["cost"]
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            f.flush()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, jobs))
    f.close()
    return spent["t"], per, skipped["n"]


def check_keys(models: list[str]) -> list[str]:
    missing = []
    for prov, var in (("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")):
        if any(REGISTRY[m].provider == prov for m in models) and not os.environ.get(var):
            missing.append(var)
    return missing


def main(argv: list[str] | None = None) -> None:
    _load_env()
    ap = argparse.ArgumentParser(prog="wre.runner")
    ap.add_argument("cmd", choices=["dry", "stage0", "run"])
    ap.add_argument("--lineup", default="gate1", choices=list(LINEUPS))
    ap.add_argument("--models", nargs="*", help="override the lineup")
    ap.add_argument("--yes", action="store_true", help="required to spend money")
    ap.add_argument("--cap", type=float, default=1.5, help="global USD cap for `run`")
    ap.add_argument("--out", default="runs/results.jsonl")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tasks", nargs="*", choices=list(TASKS), help="restrict to these tasks")
    ap.add_argument("--suite", default="main", choices=["main", "framing_v2", "part2"])
    ap.add_argument("--personas", nargs="*", choices=list(PERSONAS), help="instructions for the part2 suite")
    ap.add_argument("--reps-for", nargs="*", default=[], metavar="MODEL=N",
                    help="answers per prompt for specific models (overrides --max-reps)")
    ap.add_argument("--max-reps", type=int, default=None, help="cap answers per prompt for every model")
    ap.add_argument("--out-tokens", type=float, default=None, help="assumed output tokens/call for dry")
    a = ap.parse_args(argv)
    models = a.models or LINEUPS[a.lineup]
    items = build_all(a.seed, a.tasks, a.suite, a.personas)
    out = Path(a.out)
    reps_for = {k: int(v) for k, v in (kv.split("=") for kv in a.reps_for)}

    def reps_of(spec: ModelSpec) -> int:
        if spec.key in reps_for:
            return reps_for[spec.key]
        return min(spec.reps, a.max_reps) if a.max_reps else spec.reps

    if a.cmd == "dry":
        tin = sum(est_tokens(i.prompt) for i in items)
        print(f"prompts per answer: {len(items)}   est. input tokens per answer: {tin:.0f}")
        tot = 0.0
        for m in models:
            s = REGISTRY[m]
            r = reps_of(s)
            n = len(items) * r
            outt = a.out_tokens if a.out_tokens is not None else (400 if s.efforts and s.tier == "frontier" else 25)
            cost = (tin * r * s.price[0] + n * outt * s.price[1]) / 1e6
            tot += cost
            print(f"{m:18s} reps {r:2d} calls {n:5d}  est ${cost:6.3f}  cap ${s.cap:.2f}  out/call {outt:.0f}  {s.note}")
        print(f"{'TOTAL':18s} est ${tot:.3f}")
        return

    if not a.yes:
        sys.exit("refusing to call APIs without --yes (this spends real money).")
    miss = check_keys(models)
    if miss:
        sys.exit("missing keys: " + ", ".join(miss))
    clients = Clients()

    if a.cmd == "stage0":
        groups = dict.fromkeys((i.task, i.meta.get("persona")) for i in items)
        pick = [next(i for i in items if (i.task, i.meta.get("persona")) == g and i.version == "fresh")
                for g in groups]
        jobs = [(m, it, 0) for m in models for it in (pick if a.suite == "part2" else pick[:3])]
        spent, per, _ = run_jobs(jobs, clients, out, global_cap=0.50)
        print(f"stage0 spent ~${spent:.4f}")
        rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        for m in models:
            rs = [r for r in rows if r["model"] == m]
            if not rs:
                continue
            ok = [r for r in rs if not r["err"]]
            mo = sum(r["out_tok"] for r in ok) / max(1, len(ok))
            print(f"{m:18s} ok {len(ok)}/{len(rs)}  mean out tok {mo:6.1f}  effort {ok[0]['effort_used'] if ok else None}"
                  f"  stop {sorted({str(r['stop']) for r in ok})}  err {rs[0]['err'] if not ok else ''}")
        return

    done = done_keys(out)
    spent = 0.0
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            try:
                spent += json.loads(line)["cost"]
            except (json.JSONDecodeError, KeyError):
                pass
    for m in models:
        spec = REGISTRY[m]
        jobs = [j for j in jobs_for(spec, items, reps_of(spec)) if (j[0], j[1].id, j[2]) not in done]
        print(f"{m}: {len(jobs)} calls, cap ${spec.cap:.2f}")
        spent, per, skipped = run_jobs(jobs, clients, out, a.cap, spent)
        print(f"   total spent ${spent:.4f}; this model ${per.get(m, 0):.4f}; skipped by cap {skipped}")
    print("done")


if __name__ == "__main__":
    main()
