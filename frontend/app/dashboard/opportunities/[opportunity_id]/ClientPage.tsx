'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { displayEvidenceQuote, patternGroupLabel, plainResearchLanguage } from '@/lib/plainLanguage';
import { api, ApiError, KnowledgeGraphNeed, KnowledgeGraphOpportunity, OpportunityDetailStat } from '../../../../lib/api';

const pretty = (value: string) => plainResearchLanguage(value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase()));

function relevanceClass(relevance: string) {
  switch (relevance.toUpperCase()) {
    case 'DIRECT': return 'badge--direct';
    case 'CONTEXTUAL': return 'badge--contextual';
    default: return 'badge--unclear';
  }
}

function relevanceExplanation(relevance: string) {
  if (relevance.toUpperCase() === 'DIRECT') return 'Customers explicitly mention this behavior in the evidence. This does not prove the opportunity caused it.';
  if (relevance.toUpperCase() === 'CONTEXTUAL') return 'Customer evidence provides related context, but does not explicitly mention this behavior.';
  return 'The available customer evidence does not show a clear relationship to this behavior.';
}

function relevanceLabel(relevance: string) {
  if (relevance.toUpperCase() === 'DIRECT') return 'Explicit customer signal';
  if (relevance.toUpperCase() === 'CONTEXTUAL') return 'Related customer context';
  return 'No clear customer signal';
}

function OpportunitySkeleton() {
  return <div className="page-shell page-shell--narrow" aria-busy="true" aria-label="Loading opportunity"><div className="skeleton h-5 w-44 rounded"/><div className="skeleton mt-8 h-[28rem] rounded-[20px]"/><div className="skeleton mt-8 h-8 w-60 rounded"/><div className="skeleton mt-4 h-80 rounded-[20px]"/></div>;
}

export default function OpportunityClient() {
  const params = useParams();
  const opportunityId = params.opportunity_id as string;
  const [data, setData] = useState<OpportunityDetailStat | null>(null);
  const [graphOpportunity, setGraphOpportunity] = useState<KnowledgeGraphOpportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllEvidence, setShowAllEvidence] = useState(false);

  const loadData = useCallback(async () => {
    if (!opportunityId) return;
    setLoading(true); setError(null);
    try {
      const [detail, graph] = await Promise.all([
        api.opportunityDetail(opportunityId),
        api.knowledgeGraph().catch(() => ({ opportunities: [] })),
      ]);
      setData(detail);
      setGraphOpportunity(graph.opportunities.find(opportunity => opportunity.id === opportunityId) || null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setError('No matching opportunity was found in this analysis snapshot.');
      else setError(err instanceof Error ? err.message : 'This opportunity could not be loaded.');
    }
    finally { setLoading(false); }
  }, [opportunityId]);

  useEffect(() => { queueMicrotask(() => { void loadData(); }); }, [loadData]);

  const needs = useMemo<KnowledgeGraphNeed[]>(() => {
    if (graphOpportunity?.unmet_needs?.length) return graphOpportunity.unmet_needs;
    return (data?.supporting_needs || []).map(need => ({ unmet_need: need, observation_count: 0, associated_barriers: [], associated_intents: [], clusters: [] }));
  }, [graphOpportunity, data]);

  if (loading) return <OpportunitySkeleton />;

  if (error || !data) {
    return (
      <div className="page-shell page-shell--narrow">
        <Link href="/dashboard" className="btn-quiet mb-6 px-0">← Back to Discovery Pulse</Link>
        <div className="state-card surface"><span className="grid h-10 w-10 place-items-center rounded-full bg-[#fbebea] text-[#9d3d3d]">!</span><h1 className="text-xl font-semibold">Opportunity not available</h1><p className="max-w-md text-sm leading-6 text-[#69756f]">{error || 'No matching opportunity was found in this analysis snapshot.'}</p><button type="button" onClick={() => void loadData()} className="btn-secondary">Retry</button></div>
      </div>
    );
  }

  const visibleEvidence = showAllEvidence ? data.supporting_observations : data.supporting_observations.slice(0, 6);
  const sourceEntries = Object.entries(data.source_distribution || {}).sort((a, b) => b[1] - a[1]);
  const dominantSource = sourceEntries[0];
  const totalSourceEvidence = sourceEntries.reduce((sum, [, count]) => sum + count, 0);
  const dominantPct = dominantSource && totalSourceEvidence ? dominantSource[1] / totalSourceEvidence * 100 : 0;

  return (
    <div className="page-shell page-shell--narrow">
      <nav aria-label="Breadcrumb" className="mb-6"><Link href="/dashboard" className="inline-flex min-h-10 items-center text-sm font-semibold text-[#285e52] hover:underline">← Discovery Pulse</Link></nav>

      <article className="surface overflow-hidden rounded-[20px]">
        <div className="p-5 sm:p-8 lg:p-10">
          <span className="eyebrow">Opportunity evidence brief</span>
          <h1 className="max-w-4xl text-[1.75rem] font-semibold leading-[1.14] tracking-[-0.04em] text-[#17201d] sm:text-[2.55rem]">{data.title}</h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-[#60716a]">A summary of recurring needs and contributing patterns, grounded in the customer evidence below.</p>

          <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <MetricRelevance label="Purchase behavior" value={data.purchase_metric_relevance} />
            <MetricRelevance label="Wishlist behavior" value={data.wishlist_metric_relevance} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-px border-t border-[#dfe5e1] bg-[#dfe5e1] lg:grid-cols-4">
          <Stat label="Share of reviewed data" value={`${data.dataset_percentage}%`} detail={`of ${data.denominator.toLocaleString()} ${plainResearchLanguage(data.denominator_definition.toLowerCase())}`} />
          <Stat label="Evidence records" value={data.unique_source_count.toLocaleString()} detail="customer records linked" />
          <Stat label="Source channels" value={sourceEntries.length.toString()} detail={sourceEntries.map(([source]) => pretty(source)).join(' · ')} />
          <div className="bg-[#f8f9f7] p-4 sm:p-5"><span className="text-[9px] font-bold uppercase tracking-[0.11em] text-[#8d9692]">Source mix</span><div className="mt-3 flex h-2 overflow-hidden rounded-full bg-[#e7ebe8]">{sourceEntries.map(([source, count], index) => <span key={source} title={`${pretty(source)}: ${count}`} style={{ width: `${totalSourceEvidence ? count / totalSourceEvidence * 100 : 0}%`, background: ['#285e52','#5f8b7f','#8ca89f','#bdcbc6'][index % 4] }} />)}</div><p className="mt-2 truncate text-[10px] text-[#69756f]">{dominantSource ? `${pretty(dominantSource[0])} · ${dominantPct.toFixed(0)}%` : 'No source data'}</p></div>
        </div>
      </article>

      {dominantPct > 80 && <aside className="mt-4 flex items-start gap-2 rounded-xl border border-[#e4d3a9] bg-[#fbf4e4] p-3.5 text-xs leading-5 text-[#765116]"><span aria-hidden="true">△</span><p><strong>Source concentration · </strong>{dominantPct.toFixed(0)}% of linked evidence comes from {pretty(dominantSource[0])}. Interpret the finding with that channel skew in mind.</p></aside>}

      <section className="mt-12" aria-labelledby="derived-analysis-heading">
        <div className="section-header">
          <div><span className="badge badge--derived">What the evidence suggests</span><h2 id="derived-analysis-heading" className="section-title mt-3">What may be driving this opportunity</h2><p className="section-description max-w-2xl">Possible unmet needs and contributing factors are interpretations of the evidence. They show patterns, not proven causes.</p></div>
        </div>
        {needs.length ? <div className="space-y-4">{needs.map((need, index) => <NeedCard key={`${need.unmet_need}-${index}`} need={need} index={index} />)}</div> : <div className="state-card surface min-h-[12rem]"><h3 className="text-base font-semibold">No interpretation available</h3><p className="text-sm text-[#69756f]">Customer evidence remains available below.</p></div>}
      </section>

      <section className="mt-14" aria-labelledby="canonical-evidence-heading">
        <div className="section-header">
          <div><span className="badge badge--canonical">Customer evidence</span><h2 id="canonical-evidence-heading" className="section-title mt-3">What users actually said</h2><p className="section-description">Exact customer quotes are visually separated from the summary above.</p></div>
          <Link href={`/evidence?opportunity_id=${opportunityId}`} className="btn-secondary shrink-0">Inspect all in Evidence Explorer ↗</Link>
        </div>
        {visibleEvidence.length ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {visibleEvidence.map(observation => (
              <article key={observation.observation_id} className="surface flex flex-col border-l-[3px] border-l-[#75a999] p-5 sm:p-6">
                <blockquote className="quote-text flex-1 text-[1.02rem]">“{displayEvidenceQuote(observation.evidence_quote)}”</blockquote>
                <div className="mt-5 flex items-center justify-between gap-3 border-t border-[#e5e9e6] pt-3"><span className="text-[10px] font-semibold uppercase tracking-[0.09em] text-[#69756f]">{pretty(observation.source || 'Unknown source')}</span>{observation.source_url && <a href={observation.source_url} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-[#285e52] hover:underline">View source ↗</a>}</div>
              </article>
            ))}
          </div>
        ) : <div className="state-card surface min-h-[12rem]"><h3 className="text-base font-semibold">No customer quotes available</h3><p className="text-sm text-[#69756f]">This opportunity has no linked evidence records in the current response.</p></div>}
        {data.supporting_observations.length > 6 && <div className="mt-6 flex justify-center"><button type="button" onClick={() => setShowAllEvidence(show => !show)} className="btn-secondary">{showAllEvidence ? 'Show representative set' : `Show all ${data.supporting_observations.length} quotes`}</button></div>}
      </section>
    </div>
  );
}

function MetricRelevance({ label, value }: { label: string; value: string }) {
  return <div className="surface-muted p-4"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#7b8580]">{label}</span><span className={`badge ${relevanceClass(value)}`}>{relevanceLabel(value)}</span></div><p className="mt-3 text-[11px] leading-5 text-[#69756f]">{relevanceExplanation(value)}</p></div>;
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="min-w-0 bg-[#f8f9f7] p-4 sm:p-5"><span className="text-[9px] font-bold uppercase tracking-[0.11em] text-[#8d9692]">{label}</span><strong className="mt-2 block text-2xl font-semibold tracking-[-0.035em] text-[#25302c]">{value}</strong><span className="mt-1 block truncate text-[10px] leading-4 text-[#69756f]" title={detail}>{detail}</span></div>;
}

function NeedCard({ need, index }: { need: KnowledgeGraphNeed; index: number }) {
  const rootCauses = Array.from(new Set(need.clusters.map(cluster => cluster.primary_root_cause).filter((value): value is string => Boolean(value))));
  return (
    <article className="surface overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-[42px_minmax(0,1fr)]">
        <div className="hidden border-r border-[#ded5e3] bg-[#f5f1f6] pt-5 text-center text-[10px] font-bold text-[#786c80] lg:block">{String(index + 1).padStart(2, '0')}</div>
        <div className="p-5 sm:p-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div><span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#6e5a7e]">What shoppers may need</span><h3 className="mt-2 text-[1.05rem] font-semibold leading-6 text-[#302739]">{need.unmet_need}</h3>{need.observation_count > 0 && <p className="mt-3 text-xs text-[#786c80]">{need.observation_count.toLocaleString()} observations in the related feedback pattern</p>}</div>
            <div className="border-t border-[#e5e0e8] pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0"><span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#6e5a7e]">Possible contributing factors</span>{rootCauses.length ? <ul className="mt-2 space-y-2">{rootCauses.map(cause => <li key={cause} className="text-sm leading-6 text-[#5e5265]">{cause}</li>)}</ul> : <p className="mt-2 text-sm leading-6 text-[#8a7f91]">No contributing factor is linked in the current analysis.</p>}</div>
          </div>
          {(need.clusters.length > 0 || need.associated_barriers.length > 0) && <div className="mt-6 border-t border-[#e5e9e6] pt-4"><span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#7b8580]">Related themes and feedback patterns</span><div className="mt-2 flex flex-wrap gap-2">{need.clusters.map(cluster => <span key={cluster.cluster_id} className="rounded-md border border-[#d8ccde] bg-[#f8f5f9] px-2.5 py-1.5 text-xs font-medium text-[#604b70]">{patternGroupLabel(cluster.cluster_id, cluster.canonical_label)}</span>)}{need.associated_barriers.map(barrier => <span key={barrier} className="rounded-md border border-[#dfe5e1] bg-[#f8f9f7] px-2.5 py-1.5 text-xs font-medium text-[#60716a]">Purchase barrier · {pretty(barrier)}</span>)}</div></div>}
        </div>
      </div>
    </article>
  );
}
