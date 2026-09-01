import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from backend.store.database import Phase4OpportunityArea

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///data/discovery_pulse.db")
    async with AsyncSession(engine) as session:
        result = await session.execute(select(Phase4OpportunityArea))
        opps = result.scalars().all()
        print(f"Total: {len(opps)}")
        for o in opps:
            print(f"- {o.title} | {o.purchase_metric_relevance}")

asyncio.run(main())
