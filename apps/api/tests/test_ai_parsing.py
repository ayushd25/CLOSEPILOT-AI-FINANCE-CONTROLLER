import pytest

from app.ai.parsing import extract_json_object


def test_extract_plain_json():
    text = '{"case_id": "CASE_1", "conclusion": "MATCH_CONFIRMED"}'
    assert extract_json_object(text) == {
        "case_id": "CASE_1",
        "conclusion": "MATCH_CONFIRMED",
    }


def test_extract_from_markdown_fence():
    text = (
        "```json\n"
        '{"case_id": "CASE_1", "conclusion": "MATCH_CONFIRMED", "confidence": 0.9}\n'
        "```\n"
    )
    result = extract_json_object(text)
    assert result["conclusion"] == "MATCH_CONFIRMED"
    assert result["confidence"] == 0.9


def test_extract_from_prose_with_headings():
    text = (
        "# Investigation Report\n\n"
        "## Findings\n"
        "We observed an amount mismatch.\n\n"
        '{"case_id": "CASE_1", "proposed_action": "KEEP_EXCEPTION", "risk_level": "HIGH"}\n\n'
        "## Conclusion\n"
        "Evidence is conflicting."
    )
    result = extract_json_object(text)
    assert result["proposed_action"] == "KEEP_EXCEPTION"
    assert result["risk_level"] == "HIGH"


def test_extract_nested_objects_uses_outermost():
    text = (
        '{"case_id": "CASE_1", "nested": {"a": 1, "b": 2}, "conclusion": "NO_MATCH"}'
    )
    result = extract_json_object(text)
    assert result["case_id"] == "CASE_1"
    assert result["nested"] == {"a": 1, "b": 2}
    assert result["conclusion"] == "NO_MATCH"


def test_no_json_raises():
    with pytest.raises(ValueError):
        extract_json_object("no json here at all")