"""Smoke tests - basic checks that won't break the build."""

def test_metadata_is_valid_json():
    import json
    from pathlib import Path
    metadata = json.loads(Path("metadata.json").read_text())
    assert metadata["use_case_id"] == "24"
    assert len(metadata["agents"]) >= 2

def test_input_examples_exist():
    from pathlib import Path
    examples = list(Path("input_examples").glob("*.json"))
    assert len(examples) >= 3, "Hackathon requires 3 input examples"