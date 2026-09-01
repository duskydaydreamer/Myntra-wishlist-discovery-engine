import pytest
from backend.ingestion.normalizer import normalize_record, NormalizerError

def test_valid_record():
    raw = {
        "raw_record_id": "test_1",
        "source": "play_store",
        "raw_text": "This is a valid review.",
        "evidence_type": "myntra_specific"
    }
    normalized = normalize_record(raw)
    assert normalized.raw_text == "This is a valid review."
    assert normalized.source == "play_store"

def test_missing_raw_text():
    raw = {
        "raw_record_id": "test_2",
        "source": "play_store",
    }
    with pytest.raises(NormalizerError, match="Record missing 'raw_text'"):
        normalize_record(raw)

def test_empty_raw_text():
    raw = {
        "raw_record_id": "test_3",
        "source": "play_store",
        "raw_text": "   "
    }
    with pytest.raises(NormalizerError, match="empty or whitespace"):
        normalize_record(raw)

def test_missing_required_fields():
    raw = {
        "raw_text": "Hello"
    }
    with pytest.raises(NormalizerError, match="Validation error"):
        normalize_record(raw)
