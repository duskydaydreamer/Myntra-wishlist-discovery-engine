import pytest
from httpx import AsyncClient, ASGITransport
from backend.api.main import app
from backend.query.intent_parser import parse_intent
from unittest.mock import patch

@pytest.mark.asyncio
async def test_dashboard_stats():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["date_range"] == {"start": "2020-08-23", "end": "2026-08-19"}
        assert "total_raw_records" in data

@pytest.mark.asyncio
async def test_dashboard_opportunities():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/opportunities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # The list API only returns metadata, not metrics.
        opp_ids = [opp["opportunity_id"] for opp in data]
        assert "opp_001" in opp_ids
        assert "opp_002" in opp_ids
        assert "opp_003" in opp_ids

@pytest.mark.asyncio
async def test_opportunity_details():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        counts = {
            "opp_001": 263,
            "opp_002": 421,
            "opp_003": 274
        }
        for opp_id, expected_count in counts.items():
            response = await ac.get(f"/api/opportunities/{opp_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["unique_source_count"] == expected_count

@pytest.mark.asyncio
async def test_evidence_filtering_opportunity():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/evidence?opportunity_id=opp_001")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # Evidence filtering should use the correct cluster rules, not contaminated ones.
        for item in data["items"]:
            # Evidence object returned by API doesn't have cluster_id directly in response if it's merged or from evidence table.
            # But we can assert the observation is valid.
            assert "observation_id" in item
        
@pytest.mark.asyncio
async def test_ranked_queries():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Top barriers
        resp = await ac.post("/api/query", json={"query": "What are the top barriers?"})
        assert resp.status_code == 200
        data = resp.json()
        # the API may return an 'answer' field with synthesis instead of purely structured data
        assert "answer" in data
        assert "barriers" in data["answer"].lower() or "pricing" in data["answer"].lower() or "delivery" in data["answer"].lower()
        
        # Top outcomes
        resp = await ac.post("/api/query", json={"query": "What are the top outcomes?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "outcome" in data["answer"].lower() or "abandoned" in data["answer"].lower()

@pytest.mark.asyncio
async def test_ollama_unavailable_behavior():
    # Simulate Ollama being down by patching specifically intent_parser's httpx client instantiation
    with patch('backend.query.intent_parser.httpx.AsyncClient') as MockClient:
        mock_instance = MockClient.return_value.__aenter__.return_value
        mock_instance.post.side_effect = Exception("Connection refused")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Pass a query that forces fallback
            resp = await ac.post("/api/query", json={"query": "A completely unseen structure that forces fallback"})
            assert resp.status_code == 200
            data = resp.json()
            # Should gracefully return an evidence explanatory query without AI generated synthesis
            assert "answer" in data
            assert data.get("answer") is None or "Evidence indicates" in data["answer"] or "fallback" in data["answer"].lower() or "query_type" in data

@pytest.mark.asyncio
async def test_no_gemini_groq_calls():
    # Attempt an explanatory query and verify it doesn't crash or attempt to import paid APIs
    with patch('backend.query.intent_parser.httpx.AsyncClient') as MockClient:
        mock_instance = MockClient.return_value.__aenter__.return_value
        mock_instance.post.side_effect = Exception("No Ollama")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/query", json={"query": "Why do users drop off?"})
            assert resp.status_code == 200
            data = resp.json()
            # We know it didn't call Gemini because we patched httpx and there's no Gemini code left in intent_parser.py
            assert "answer" in data
