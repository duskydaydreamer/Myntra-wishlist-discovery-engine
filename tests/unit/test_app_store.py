import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from backend.ingestion.connectors.app_store import AppStoreAdapter

@patch('backend.ingestion.connectors.app_store.time.sleep')
@patch('backend.ingestion.connectors.app_store.requests.get')
def test_app_store_adapter(mock_get, _mock_sleep):
    recent_date = datetime.now() - timedelta(days=5)
    old_date = datetime.now() - timedelta(weeks=13)
    
    response = MagicMock(status_code=200)
    response.json.return_value = {"feed": {"entry": [
        {
            "id": {"label": "recent"}, "updated": {"label": recent_date.isoformat()},
            "content": {"label": "Great UX"}, "title": {"label": "Good"},
            "im:rating": {"label": "5"},
        },
        {
            "id": {"label": "old"}, "updated": {"label": old_date.isoformat()},
            "content": {"label": "Bad app"}, "title": {"label": "Terrible"},
            "im:rating": {"label": "1"},
        },
    ]}}
    empty_response = MagicMock(status_code=200)
    empty_response.json.return_value = {"feed": {"entry": []}}
    mock_get.side_effect = [response, empty_response]
    
    adapter = AppStoreAdapter(window_weeks=12)
    records = adapter.fetch_records()
    
    assert len(records) == 1
    assert records[0].raw_text == "Great UX"
    assert records[0].title == "Good"
    assert records[0].rating == 5.0
    
    assert mock_get.call_count == 2
