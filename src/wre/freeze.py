"""Write and verify the frozen item sets (items/*.jsonl and items/MANIFEST.json).

    python -m wre.freeze --write     # regenerate items/ from code (seed 0)
    python -m wre.freeze --check     # fail if items/ differs from what the code generates

Every prompt sent to a model in this repository's data comes from one of these sets. The manifest
holds a SHA-256 hash per file and one hash over all of them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .tasks import anchoring, build_all, forbid, framing, sunkcost
from .tasks.base import Item

ITEMS_DIR = Path(__file__).resolve().parents[2] / "items"
SEED = 0


def item_sets(seed: int = SEED) -> dict[str, list[Item]]:
    """name -> items. `main_run1` reproduces the first run's wording; `main` is the final wording."""
    run1 = (
        framing.build(seed)
        + sunkcost.build(seed, "v1")
        + anchoring.build(seed)
        + forbid.build(seed, "v1")
    )
    return {
        "main_run1": run1,
        "main": build_all(seed),
        "framing_v2": build_all(seed, suite="framing_v2"),
        "prompting": build_all(seed, suite="part2"),
    }


def serialize(items: list[Item]) -> str:
    lines = [json.dumps(asdict(it), ensure_ascii=False, sort_keys=True) for it in items]
    return "\n".join(lines) + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_manifest(seed: int = SEED) -> tuple[dict[str, str], dict]:
    files = {f"{name}.jsonl": serialize(items) for name, items in item_sets(seed).items()}
    entries = {
        fn: {"sha256": digest(text), "items": text.count("\n")} for fn, text in sorted(files.items())
    }
    overall = digest("".join(f"{fn}:{e['sha256']}\n" for fn, e in entries.items()))
    return files, {"seed": seed, "files": entries, "sha256_all": overall}


def write(directory: Path = ITEMS_DIR) -> None:
    files, manifest = build_manifest()
    directory.mkdir(parents=True, exist_ok=True)
    for fn, text in files.items():
        (directory / fn).write_text(text, encoding="utf-8", newline="\n")
    (directory / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def check(directory: Path = ITEMS_DIR) -> list[str]:
    """Differences between items/ on disk and the code's output; empty means identical."""
    files, manifest = build_manifest()
    problems = []
    for fn, text in files.items():
        path = directory / fn
        if not path.exists():
            problems.append(f"missing {fn}")
        elif digest(path.read_bytes().decode("utf-8").replace("\r\n", "\n")) != digest(text):
            problems.append(f"{fn} differs from generated items")
    man = directory / "MANIFEST.json"
    if not man.exists() or json.loads(man.read_text(encoding="utf-8")) != manifest:
        problems.append("MANIFEST.json missing or differs")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wre.freeze")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.write:
        write()
        print(f"wrote {ITEMS_DIR}")
        return 0
    problems = check()
    print("\n".join(problems) if problems else "items match the code")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
