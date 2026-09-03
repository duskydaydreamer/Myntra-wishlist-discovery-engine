'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, ClusterStat, DatasetStats, DistributionResponse, OpportunityStat, ThemeStat } from '../../lib/api';
import StatsCards from '../../components/StatsCards';
import OpportunityCards from '../../components/OpportunityCards';
import { ThemeGrid, ClusterGrid } from '../../components/ThemeAndCluster';
import SourceDistribution from '../../components/SourceDistribution';
import DataJourney from '../../components/DataJourney';
import SignalSection from '../../components/SignalSection';

interface DashboardData {
  stats: DatasetStats;
  opportunities: OpportunityStat[];
  themes: ThemeStat[];
  clusters: ClusterStat[];
  barriers: DistributionResponse | null;
  wishlistMotivations: DistributionResponse | null;
  purchaseIntents: DistributionResponse | null;
  uncertainties: DistributionResponse | null;
  informationNeeds: DistributionResponse | null;
  workarounds: DistributionResponse | null;
  journeyStages: DistributionResponse | null;
  decisionOutcomes: DistributionResponse | null;
}

function DashboardSkeleton() {
  return (
    <div className="page-shell" aria-label="Loading Discovery Pulse" aria-busy="true">
      <div className="skeleton h-3 w-32 rounded" />
      <div className="skeleton mt-4 h-11 w-72 max-w-full rounded-lg" />
      <div className="skeleton mt-3 h-5 w-[34rem] max-w-full rounded" />
      <div className="mt-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map(item => <div key={item} className="skeleton h-32 rounded-2xl" />)}
      </div>
      <div className="skeleton mt-14 h-7 w-56 rounded" />
      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        {[0, 1, 2].map(item => <div key={item} className="skeleton h-[30rem] rounded-[18px]" />)}
      </div>
    </div>
  );
}

export default function DashboardClient() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [stats, opportunities, themes, clusters, barriers, wishlistMotivations, purchaseIntents, uncertainties, informationNeeds, workarounds, journeyStages, decisionOutcomes] = await Promise.all([
        api.stats(), api.opportunities(), api.themes(), api.clusters(),
        api.barriers().catch(() => null), api.wishlistMotivations().catch(() => null),
        api.purchaseIntents().catch(() => null), api.uncertainties().catch(() => null),
        api.informationNeeds().catch(() => null), api.workarounds().catch(() => null),
        api.journeyStages().catch(() => null),
        api.decisionOutcomes().catch(() => null),
      ]);
      setData({ stats, opportunities, themes, clusters, barriers, wishlistMotivations, purchaseIntents, uncertainties, informationNeeds, workarounds, journeyStages, decisionOutcomes });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The dashboard data could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { queueMicrotask(() => { void loadData(); }); }, [loadData]);

  if (loading) return <DashboardSkeleton />;

  if (error) {
    return (
      <div className="page-shell page-shell--narrow">
        <div className="state-card surface mt-12">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-[#fbebea] text-[#9d3d3d]" aria-hidden="true">!</span>
          <h1 className="text-xl font-semibold text-[#17201d]">Discovery Pulse is unavailable</h1>
          <p className="max-w-md text-sm leading-6 text-[#69756f]">{error}</p>
          <button type="button" onClick={() => void loadData()} className="btn-secondary mt-2">Retry</button>
        </div>
      </div>
    );
  }

  if (!data) {
    return <div className="page-shell"><div className="state-card surface"><h1 className="text-xl font-semibold">No dashboard data available</h1><p className="text-sm text-[#69756f]">The dataset returned no dashboard information.</p></div></div>;
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <span className="eyebrow">Myntra / Wishlist Intelligence</span>
          <h1 className="page-title">Discovery Pulse</h1>
          <p className="page-description">A focused view of public shopping feedback, purchase barriers, and areas that need a closer look.</p>
        </div>

      </header>

      <section className="surface mb-5 px-5 py-6 sm:px-7 sm:py-7" aria-labelledby="mission-heading">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <span className="eyebrow mb-2">What we want to understand</span>
            <h2 id="mission-heading" className="max-w-3xl text-xl font-bold leading-7 tracking-[-0.025em] text-[var(--ink)] sm:text-[1.55rem]">Understand where wishlist intent loses momentum before purchase.</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">Follow the strongest customer evidence to understand recurring patterns without assuming what caused them.</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <span className="badge badge--canonical px-3 py-2">Customer evidence</span>
            <span className="badge badge--derived px-3 py-2">What the evidence suggests</span>
          </div>
        </div>
      </section>

      <StatsCards stats={data.stats} />

      <section className="mb-16" aria-labelledby="pattern-heading">
        <div className="section-header">
          <div>
            <span className="eyebrow">Customer feedback</span>
            <h2 id="pattern-heading" className="section-title">What customers repeatedly talk about</h2>
            <p className="section-description">See the shopping topics customers mention most often and the experiences that appear repeatedly in similar comments.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ThemeGrid themes={data.themes} />
          <ClusterGrid clusters={data.clusters} />
        </div>
      </section>

      <SignalSection {...data} />
      <SourceDistribution analyzed={data.stats.source_distribution_analyzed} raw={data.stats.source_distribution_raw} />
      <DataJourney stats={data.stats} />
      <OpportunityCards opportunities={data.opportunities} />
    </div>
  );
}
