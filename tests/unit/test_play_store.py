import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from backend.ingestion.connectors.play_store import PlayStoreAdapter

@patch('backend.ingestion.connectors.play_store.reviews')
def test_play_store_adapter(mock_reviews):
    recent_date = datetime.now() - timedelta(days=5)
    old_date = datetime.now() - timedelta(weeks=13)
    
    # Mock return values for reviews(): result, continuation_token
    mock_reviews.side_effect = [
        # First batch
        (
            [
                {"reviewId": "r1", "at": recent_date, "content": "Good app", "score": 5, "userName": "Alice"},
                {"reviewId": "r2", "at": old_date, "content": "Old review", "score": 3, "userName": "Bob"}
            ],
            "token1"
        )
    ]
    
    adapter = PlayStoreAdapter(window_weeks=12)
    records = adapter.fetch_records()
    
    assert len(records) == 1
    assert records[0].raw_record_id == "play_store_r1"
    assert records[0].raw_text == "Good app"
    assert records[0].rating == 5.0
    
    # Assert userName was stripped before storing in some way
    # (Since it doesn't even make it into the schema, we can't test it directly on the schema object easily,
    # but we can verify it's not present).
    assert not hasattr(records[0], "userName")
