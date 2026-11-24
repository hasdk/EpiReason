import json

from harness.canary import GUID, ROOT, files


def test_every_public_item_file_carries_the_canary():
    paths = files()
    assert paths, "no item files found"
    missing = [str(p.relative_to(ROOT)) for p in paths if GUID not in p.read_text(encoding="utf-8")]
    assert missing == []


def test_published_results_and_sheet_carry_the_canary():
    for rel in ("results/full_v1.jsonl", "grading/hand_sheet_r1.json", "README.md",
                "analysis/results.md", "analysis/transcripts.md"):
        path = ROOT / rel
        if path.exists():
            assert GUID in path.read_text(encoding="utf-8"), rel


def test_results_header_is_skipped_by_the_loader():
    from analysis.analyse import load
    rows = load()
    assert rows and all("canary" not in r for r in rows)
