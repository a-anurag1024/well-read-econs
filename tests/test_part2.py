from wre.part2 import analyze, anchor_status, band, framing_cell, verdict
from wre.tasks import PERSONAS, build_all


def test_part2_suite_shape():
    items = build_all(0, suite="part2")
    assert len(items) == 3 * (48 + 24)
    assert len({i.id for i in items}) == len(items)
    assert all(i.version == "fresh" and i.meta["persona"] in PERSONAS for i in items)
    one = build_all(0, suite="part2", personas=["gut"])
    assert len(one) == 72 and all(i.prompt.startswith(PERSONAS["gut"]) for i in one)
    base = {i.id.split("@")[0]: i for i in one}
    typical = [i for i in build_all(0, suite="part2", personas=["typical"])]
    assert all(i.item_key == base[i.id.split("@")[0]].item_key for i in typical)


def test_bands():
    assert band(-0.5) == "reversed" and band(0.0) == "Econ" and band(0.2) == "weak"
    assert (
        band(0.71) == "human-sized"
        and band(2.1) == "exaggerated"
        and band(0.7, valid=False) == "invalid"
    )


def test_anchor_status_and_verdict():
    def cells(b1, b2):
        return {"typical": {"band": b1}, "gut": {"band": b2}}

    assert anchor_status(cells("human-sized", "human-sized")) == "calibrated"
    assert anchor_status(cells("human-sized", "Econ")) == "partly"
    assert anchor_status(cells("Econ", "weak")) == "immovable"
    assert anchor_status(cells("exaggerated", "exaggerated")) == "still exaggerated"
    assert anchor_status(cells("exaggerated", "Econ")) == "mixed"
    assert verdict({"a": "calibrated", "b": "calibrated"}) == "PROMPTING CALIBRATES"
    assert verdict({"a": "calibrated", "b": "immovable"}) == "PROMPTING CALIBRATES SOME"
    assert verdict({"a": "partly", "b": "immovable"}) == "PROMPTING DOES NOT CALIBRATE"


def _rec(
    model, item_key, cond, parsed, persona=None, task="framing", fmt="ab", sure_first=True, text="A"
):
    return {
        "model": model,
        "task": task,
        "version": "fresh",
        "id": f"{item_key}-{cond}",
        "item_key": item_key,
        "condition": cond,
        "parsed": parsed,
        "err": None,
        "out_tok": 5,
        "text": text,
        "meta": {"persona": persona, "fmt": fmt, "sure_first": sure_first},
    }


def test_framing_cell_detects_position_bias_and_invalid():
    recs = [_rec("m", f"s{i}", c, 1.0, sure_first=True) for i in range(6) for c in ("hi", "lo")]
    cell = framing_cell(recs, n_boot=50)
    assert cell["biased"] and not cell["valid"] and cell["band"] == "invalid"
    mixed = [
        _rec("m", f"s{i}", "hi", 1.0 if i % 2 else 0.0, sure_first=i % 2 == 0, text="AB"[i % 2])
        for i in range(8)
    ]
    assert framing_cell(mixed, n_boot=50)["parse"] == 1.0


def test_analyze_end_to_end_on_synthetic_records():
    def gen(model, persona, p_gain, p_loss, task="framing"):
        out = []
        for i in range(12):
            for cond, p in (("hi", p_gain), ("lo", p_loss)):
                chose_sure = (i * 7 + (cond == "lo") * 3) % 10 < p * 10
                fmt = "ab" if i % 2 == 0 else "n"
                sure_first = i % 4 < 2
                label = ("A" if sure_first else "B") if chose_sure else ("B" if sure_first else "A")
                out.append(
                    _rec(
                        model,
                        f"s{i}",
                        cond,
                        1.0 if chose_sure else 0.0,
                        persona,
                        "framing",
                        fmt,
                        sure_first,
                        text=label if fmt == "ab" else ("1" if label == "A" else "2"),
                    )
                )
        return out

    models = ["gpt-6.1-sol", "gpt-6-astra", "claude-sonnet-5.5", "claude-opus-5.5"]
    results, base = [], []
    for m in models:
        base += gen(m, None, 1.0, 1.0)
        for p in ("typical", "gut"):
            results += gen(m, p, 0.7, 0.3)
        results += gen(m, "rational", 1.0, 1.0)
    out = analyze(results, base, [], n_boot=50)
    assert out["verdict"] == "PROMPTING CALIBRATES"
    assert set(out["C1"].values()) == {"calibrated"}
    assert out["C2_overshoot"] == []
