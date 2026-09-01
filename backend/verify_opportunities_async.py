import asyncio
import json
from httpx import AsyncClient, ASGITransport
from backend.api.main import app

async def run_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("Fetching list of opportunities...")
        list_resp = await client.get("/api/dashboard/opportunities")
        
        if list_resp.status_code != 200:
            print(f"FAILED: /api/dashboard/opportunities returned {list_resp.status_code}")
            return
            
        opportunities = list_resp.json()
        print(f"Found {len(opportunities)} opportunities.")
        
        for opp in opportunities:
            opp_id = opp["opportunity_id"]
            print(f"\n--- Testing Opportunity: {opp_id} ---")
            
            detail_resp = await client.get(f"/api/opportunities/{opp_id}")
            if detail_resp.status_code != 200:
                print(f"FAILED: /api/opportunities/{opp_id} returned {detail_resp.status_code}")
                continue
                
            data = detail_resp.json()
            print(f"Title: {data['title']}")
            print(f"Metric Relevance: {data['purchase_metric_relevance']}")
            print(f"Denominator: {data['denominator']} - {data.get('denominator_definition')}")
            print(f"Dataset Percentage: {data['dataset_percentage']}%")
            print(f"Unique Source Count: {data['unique_source_count']}")
            print(f"Source Distribution: {data.get('source_distribution')}")
            
            print("\nSupporting Needs:")
            for need in data.get("supporting_needs", []):
                print(f"  - Need: {need.get('unmet_need')}")
                print(f"    Root Cause: {need.get('root_cause')}")
                print(f"    Clusters: {need.get('supporting_clusters')}")
                
            print("\nSupporting Observations (first 2):")
            for obs in data.get("supporting_observations", [])[:2]:
                print(f"  - Quote: {obs.get('evidence_quote')[:50]}...")
                print(f"    Source: {obs.get('source')} | URL: {obs.get('source_url')}")
                
            if "raw_text" in data or any("raw_text" in obs for obs in data.get("supporting_observations", [])):
                print("FAILED: raw_text found in output!")
                
        # Test Not Found State
        nf_resp = await client.get("/api/opportunities/non_existent_id")
        print(f"\nNot Found State Test: Status Code {nf_resp.status_code}")
        if nf_resp.status_code == 404:
            print("PASS: 404 correctly returned for missing ID")

if __name__ == "__main__":
    asyncio.run(run_tests())
