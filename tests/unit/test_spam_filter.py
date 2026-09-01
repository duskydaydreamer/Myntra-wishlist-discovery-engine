import pytest
from backend.cleaning.spam_filter import SpamFilter

@pytest.mark.asyncio
async def test_heuristic_filter():
    sf = SpamFilter(min_length=10)

    is_spam, flags = await sf.filter_record("Too short")
    assert is_spam is True
    assert "content_free" in flags
    assert "heuristic_short" in flags

    is_spam, flags = await sf.filter_record("This is long enough to preserve meaningful feedback")
    assert is_spam is False
    assert flags == []


@pytest.mark.asyncio
async def test_empty_content_is_filtered():
    is_spam, flags = await SpamFilter().filter_record("   ")
    assert is_spam is True
    assert flags == ["content_free"]
