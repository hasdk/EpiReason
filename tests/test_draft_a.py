from harness.draft_a import (GENERATOR_FIELDS, REQUIRED_SPEC_FIELDS, SECTIONS, build_prompt,
                             parse_draft, validate_spec)


def _spec() -> dict:
    spec = {f: f"text for {f}" for f in REQUIRED_SPEC_FIELDS}
    spec["scenario"] = "A-S99"
    return spec


def test_complete_spec_is_valid():
    assert validate_spec(_spec()) == []


def test_empty_and_unknown_fields_are_reported():
    spec = _spec()
    spec["flaw"] = ""
    spec["surprise"] = "x"
    errors = validate_spec(spec)
    assert any("flaw" in e for e in errors) and any("surprise" in e for e in errors)


def test_prompt_shows_design_fields_but_not_reference_or_difficulty():
    spec = _spec()
    spec["key_reference"] = "SECRET-REFERENCE"
    spec["difficulty_guess"] = "SECRET-DIFFICULTY"
    spec["distractor"] = "a harmless detail"
    prompt = build_prompt(spec)
    assert "SECRET-REFERENCE" not in prompt and "SECRET-DIFFICULTY" not in prompt
    assert "a harmless detail" in prompt and "text for mechanism" in prompt
    assert "key_reference" not in GENERATOR_FIELDS


def test_parse_draft_splits_sections():
    reply = ("## FLAWED\nWe studied A.\n\n## FIXED\nWe studied B.\n\n## CHANGE LOG\n- one\n\n"
             "## CANDIDATE KEY (UNVERIFIED)\nKey.\n\n## QUERIES\nnone\n")
    sections = parse_draft(reply)
    assert list(sections) == list(SECTIONS)
    assert sections["FLAWED"] == "We studied A." and sections["FIXED"] == "We studied B."
    assert sections["QUERIES"] == "none"


def test_parse_draft_reports_missing_sections_as_empty():
    assert parse_draft("## FLAWED\nonly this")["FIXED"] == ""
