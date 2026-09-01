import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from backend.ingestion.connectors.reddit import RedditThreadIngester

@patch('backend.ingestion.connectors.reddit.time.sleep')
@patch('backend.ingestion.connectors.reddit.feedparser.parse')
@patch('backend.ingestion.connectors.reddit.requests.get')
def test_reddit_adapter(mock_get, mock_parse, _mock_sleep):
    response = MagicMock(status_code=200, content=b"rss")
    mock_get.return_value = response

    post = MagicMock()
    post.id = "sub1"
    post.title = "Post title"
    post.summary = "<p>Post body</p>"
    post.get.side_effect = lambda key, default='': "2026-08-01T10:00:00+00:00" if key == "updated" else default
    comment = MagicMock()
    comment.id = "c1"
    comment.title = ""
    comment.summary = "<p>Comment 1</p>"
    comment.get.side_effect = lambda key, default='': "2026-08-01T10:05:00+00:00" if key == "updated" else default
    mock_parse.return_value.entries = [post, comment]
    
    adapter = RedditThreadIngester(thread_urls=["http://fake.url"])
    records = adapter.fetch_records()
    
    assert len(records) == 2
    
    assert records[0].source_type == "post"
    assert records[0].raw_text == "Post body"
    
    assert records[1].source_type == "comment"
    assert records[1].raw_text == "Comment 1"
    assert records[1].source_url == "http://fake.url"
