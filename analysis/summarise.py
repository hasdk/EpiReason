"""Summarise a folder of EpiReason run logs as a Markdown report.

    uv run python -m analysis.summarise logs/full_v1 analysis/summary.md

Descriptive only: rates and means per model, with the number of responses behind each.
No intervals and no model ranking; see analysis/power_hint_results.md for why.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log


def _model_name(name: str) -> str:
    """One name per model whatever the route: openrouter/anthropic/claude-haiku-5.5 -> anthropic/claude-haiku-5-5."""
    if name.startswith("openrouter/"):
        name = name.removeprefix("openrouter/")
        if name.startswith("anthropic/"):
            name = name.replace(".", "-")
    return name


def _rows(log_dir: str) -> list[dict]:
    rows = []
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info)
        if log.status != "success":
            continue
        for sample in log.samples or []:
            if not sample.scores:
                continue
            score = next(iter(sample.scores.values()))
            meta, smeta = sample.metadata or {}, score.metadata or {}
            rows.append({
                "model": _model_name(log.eval.model), "family": meta.get("family"), "scenario": meta.get("scenario"),
                "version": meta.get("version"), "level": meta.get("level"), "topic": meta.get("topic"),
                "generator": meta.get("generator_model") or "author", "value": score.value,
                "criteria": smeta.get("criteria") or {}, "smeta": smeta,
            })
    return rows


def _rate(flags: list) -> str:
    known = [f for f in flags if f is not None]
    if not known:
        return "n/a"
    return f"{100 * sum(known) / len(known):.0f}% ({sum(known)}/{len(known)})"


def _mean(values: list) -> str:
    good = [v for v in values if isinstance(v, (int, float)) and v == v]
    return f"{sum(good) / len(good):.2f}" if good else "n/a"


def _table(header: list[str], body: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header),
            *["| " + " | ".join(r) + " |" for r in body], ""]


def report(log_dir: str) -> str:
    rows = _rows(log_dir)
    models = sorted({r["model"] for r in rows})
    a = [r for r in rows if r["family"] == "A"]
    out = ["# EpiReason results", "",
           f"Source: `{log_dir}`. {len(rows)} scored responses from {len(models)} model(s).",
           "Rates are shown as percent (count/total). Small counts: read as a demonstration, not a ranking.", ""]

    out += ["## Family A: study critique", "",
            "Detection = the `detect` criterion met on the flawed version. False alarm = the `false_alarm` "
            "criterion met on the fixed version: the model says the fixed flaw is still there. Overcritical = the "
            "`overcritical` criterion met on the fixed version: the model calls a different problem a major threat. "
            "Overclaim = the `overclaim` criterion met on the flawed version.", ""]
    body = []
    for m in models:
        for level in ("neutral", "direct"):
            cell = [r for r in a if r["model"] == m and r["level"] == level]
            flawed = [r for r in cell if r["version"] == "flawed"]
            fixed = [r for r in cell if r["version"] == "fixed"]
            body.append([m, level,
                         _rate([r["criteria"].get("detect") for r in flawed]),
                         _rate([r["criteria"].get("overclaim") for r in flawed]),
                         _rate([r["criteria"].get("false_alarm") for r in fixed]),
                         _rate([r["criteria"].get("overcritical") for r in fixed]),
                         _rate([r["criteria"].get("no_major_flaw") for r in fixed]),
                         _mean([r["value"] for r in flawed]), _mean([r["value"] for r in fixed])])
    out += _table(["Model", "Hint level", "Detection", "Overclaim", "False alarm", "Overcritical", "Recognises sound design",
                   "Mean score, flawed", "Mean score, fixed"], body)

    out += ["### Detection at the neutral level, by scenario", ""]
    scenarios = sorted({(r["scenario"], r["topic"], r["generator"]) for r in a})
    body = []
    for sc, topic, gen in scenarios:
        line = [sc, topic, gen]
        for m in models:
            for version, key in (("flawed", "detect"), ("fixed", "false_alarm")):
                cell = [r["criteria"].get(key) for r in a
                        if r["model"] == m and r["scenario"] == sc and r["level"] == "neutral" and r["version"] == version]
                line.append(_rate(cell))
        body.append(line)
    header = ["Scenario", "Threat", "Vignette drafted by"]
    for m in models:
        header += [f"{m}: detection", f"{m}: false alarm"]
    out += _table(header, body)

    out += ["### Mean normalised score by who drafted the vignette (flawed and fixed, both levels)", ""]
    gens = sorted({r["generator"] for r in a})
    body = [[g, str(len({r["scenario"] for r in a if r["generator"] == g})),
             *[_mean([r["value"] for r in a if r["generator"] == g and r["model"] == m]) for m in models]] for g in gens]
    out += _table(["Vignette drafted by", "Scenarios", *models], body)

    for family, title, key in (("B", "Family B: adjustment sets", "minimal"), ("C", "Family C: calculations", "correct")):
        fam = [r for r in rows if r["family"] == family]
        if not fam:
            continue
        out += [f"## {title}", ""]
        by = defaultdict(list)
        for r in fam:
            flag = r["smeta"].get(key)
            by[(r["model"], r["version"] if family == "B" else "all")].append(
                bool(flag) if flag is not None else (r["value"] == 1))
        versions = sorted({v for _, v in by})
        body = [[m, *[_rate(by.get((m, v), [])) for v in versions]] for m in models]
        out += _table(["Model", *versions], body)
    return "\n".join(out)


if __name__ == "__main__":
    log_dir, target = sys.argv[1], sys.argv[2]
    Path(target).write_text(report(log_dir), encoding="utf-8", newline="\n")
    print(f"report written to {target}")
