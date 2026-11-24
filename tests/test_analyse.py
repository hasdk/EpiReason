import csv
import json

import pytest

from analysis.analyse import agreement, load, load_hand_grades, report


def _write_key_and_grades(tmp_path, hand_values):
    key, grades = tmp_path / "key.csv", tmp_path / "grades.csv"
    with open(key, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["blind_id", "log", "sample_id", "epoch", "model", "item_id", "version", "level", "judge_criteria"])
        for i, scen in enumerate(["A-S01", "A-S02", "A-S03", "A-S04"]):
            w.writerow([f"G{i}", "x.eval", f"{scen}-fixed:direct", 1, "openai/gpt-5.4-mini", f"{scen}-fixed", "fixed",
                        "direct", json.dumps({"overcritical": i % 2 == 0, "false_alarm": False})])
    with open(grades, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["blind_id", "criterion", "met"])
        for i, v in enumerate(hand_values):
            w.writerow([f"G{i}", "overcritical", v])
            w.writerow([f"G{i}", "false_alarm", "false"])
        w.writerow(["G0", "not_a_criterion", "true"])      # no judge decision: dropped
    return key, grades


def test_hand_grades_missing_file_returns_none(tmp_path):
    assert load_hand_grades(tmp_path / "key.csv", tmp_path / "none.csv") is None


def test_hand_grades_join_the_judge_and_scenario(tmp_path):
    key, grades = _write_key_and_grades(tmp_path, ["true", "false", "true", "true"])
    d = load_hand_grades(key, grades)
    assert len(d) == 8
    first = next(x for x in d if x["blind_id"] == "G0" and x["criterion"] == "overcritical")
    assert first == {"blind_id": "G0", "model": "openai/gpt-5.4-mini", "scenario": "A-S01", "version": "fixed",
                     "level": "direct", "criterion": "overcritical", "hand": True, "judge": True}


def test_agreement_counts(tmp_path):
    key, grades = _write_key_and_grades(tmp_path, ["true", "false", "true", "true"])
    oc = [x for x in load_hand_grades(key, grades) if x["criterion"] == "overcritical"]
    g = agreement(oc)
    assert g["n"] == 4 and g["hand_met"] == 3 and g["judge_met"] == 2
    assert g["agree"][0] == pytest.approx(0.75)
    assert g["kappa"][0] == pytest.approx(0.5)


def test_report_runs_on_the_published_results():
    full, block = report(load(), None)
    assert "Pending" in block and "Hint effect" in full
    assert "| Claude Opus 5.5 |" in block
