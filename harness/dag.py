"""Adjustment sets from dagitty (R), so family B keys are computed, not hand-written."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

R_SCRIPT = Path(__file__).with_name("dagitty_sets.R")
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def adjustment_sets(edges: list[list[str]], exposure: str, outcome: str,
                    unmeasured: list[str] | None = None) -> dict[str, list[list[str]]]:
    """Return {"minimal": [...], "valid": [...]} for the total effect of exposure on outcome.

    Each set is a sorted list of variable names. An empty set means no adjustment is needed.
    An empty list of sets means no set of measured variables is sufficient.
    """
    unmeasured = list(unmeasured or [])
    names = {v for e in edges for v in e} | {exposure, outcome} | set(unmeasured)
    bad = sorted(n for n in names if not NAME.match(n))
    if bad:
        raise ValueError(f"variable names must be letters, digits and underscores: {bad}")

    with tempfile.TemporaryDirectory() as tmp:
        spec, out = Path(tmp) / "spec.json", Path(tmp) / "sets.json"
        spec.write_text(json.dumps({"edges": edges, "exposure": exposure, "outcome": outcome,
                                    "unmeasured": unmeasured}), encoding="utf-8")
        done = subprocess.run(["Rscript", str(R_SCRIPT), str(spec), str(out)],
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError(f"dagitty failed: {done.stderr.strip()}")
        result = json.loads(out.read_text(encoding="utf-8"))
    # dagitty's type="all" lists sets that contain latent variables, so drop those here.
    # Whether a set is sufficient does not depend on what is measured, so the filter is exact.
    hidden = set(unmeasured)
    return {kind: sorted(sorted(s) for s in result[kind] if not hidden & set(s))
            for kind in ("minimal", "valid")}
