import pytest
from unittest.mock import patch, MagicMock
from backend.ingestion.connectors.youtube import YouTubeAPIIngester

@patch('backend.ingestion.connectors.youtube.build')
@patch('backend.ingestion.connectors.youtube.os.getenv')
def test_youtube_adapter(mock_getenv, mock_build):
    mock_getenv.return_value = "fake_key"
    mock_youtube = MagicMock()
    mock_build.return_value = mock_youtube
    
    # Mock search
    mock_search_request = MagicMock()
    mock_search_request.execute.return_value = {
        "items": [
            {
                "id": {"videoId": "v1"},
                "snippet": {"title": "Myntra Haul"}
            }
        ]
    }
    mock_youtube.search().list.return_value = mock_search_request
    
    # Mock comments
    mock_comment_request = MagicMock()
    mock_comment_request.execute.return_value = {
        "items": [
            {
                "id": "c1",
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": "Nice clothes from Myntra",
                            "authorChannelId": {"value": "u1"},
                            "publishedAt": "2023-01-01T10:00:00Z"
                        }
                    }
                },
                "replies": {
                    "comments": [
                        {
                            "snippet": {
                                "textOriginal": "I agree",
                                "authorChannelId": {"value": "u2"},
                                "publishedAt": "2023-01-01T11:00:00Z"
                            }
                        }
                    ]
                }
            }
        ]
    }
    mock_youtube.commentThreads().list.return_value = mock_comment_request
    
    adapter = YouTubeAPIIngester(search_queries=["Myntra haul"])
    records = adapter.fetch_records()
    
    # Top level + reply = 2 comments
    assert len(records) == 2
    assert records[0].raw_text == "Nice clothes from Myntra"
    assert records[0].video_id == "v1"
    assert records[0].video_title == "Myntra Haul"
    assert records[0].evidence_type == "myntra_specific"
    
    assert records[1].raw_text == "I agree"
    assert records[1].parent_post_id == "c1"
    assert records[1].evidence_type == "category_level"
