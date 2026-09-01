import asyncio
from httpx import AsyncClient, ASGITransport
from backend.api.main import app

async def test_dashboard():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        endpoints = [
            "/api/dashboard/stats",
            "/api/dashboard/opportunities",
            "/api/dashboard/themes",
            "/api/dashboard/clusters"
        ]
        
        for ep in endpoints:
            response = await ac.get(ep)
            print(f"--- {ep} ---")
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"Items: {len(data)}")
                    if data and ep == "/api/dashboard/opportunities":
                        for opp in data:
                            print(f"  Title: {opp.get('title')}")
                            print(f"  Denom: {opp.get('denominator')}")
                            print(f"  Quotes: {len(opp.get('representative_quotes', []))}")
                else:
                    print(f"Stats raw: {data.get('total_raw_records')}, canonical: {data.get('canonical_observations')}")

asyncio.run(test_dashboard())
