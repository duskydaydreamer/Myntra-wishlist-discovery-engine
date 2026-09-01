'use client';

import React, { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { api, EvidenceListResponse, ObservationDetailResponse, ObservationResponse } from '@/lib/api';
import { displayEvidenceQuote, hasPrivacyMask, opportunityAreaLabel, patternGroupLabel, plainResearchLanguage } from '@/lib/plainLanguage';

const phase4Filters = [
  ['predefined_theme', 'Research theme'], ['cluster_id', 'Feedback pattern'], ['opportunity_id', 'Opportunity area'],
] as const;
const phase3Filters = [
  ['source', 'Source'], ['wishlist_intent', 'Wishlist intent'], ['purchase_intent', 'Purchase intent'],
  ['primary_barrier', 'Primary barrier'], ['journey_stage', 'Journey stage'], ['decision_outcome', 'Decision outcome'],
] as const;

type FilterKey = typeof phase4Filters[number][0] | typeof phase3Filters[number][0];
type ActiveFilters = Record<FilterKey, string>;

const isUnstated = (value: string | null | undefined) => !value || /^(unknown|unclear|none|null|not[_ ]classified)$/i.test(value.trim());
const pretty = (value: string | null | undefined) => isUnstated(value) ? 'Not enough information' : plainResearchLanguage(value!.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase()));

function purchaseIntentLabel(value: string | null | undefined) {
  if (isUnstated(value)) return 'Buying intent not stated';
  if (value!.toLowerCase() === 'high') return 'Strong buying signal';
  if (value!.toLowerCase() === 'medium') return 'Some buying signal';
  if (value!.toLowerCase() === 'low') return 'Weak buying signal';
  return `Buying signal · ${pretty(value)}`;
}

function wishlistIntentLabel(value: string | null | undefined) {
  if (isUnstated(value)) return 'Wishlist intent not stated';
  return pretty(value);
}

function SourceLabel({ source }: { source: string | null | undefined }) {
  const label = pretty(source).replace('Youtube', 'YouTube');

  return (
    <span className="min-w-0 break-words text-xs font-medium leading-4 text-[#53615b]">{label}</span>
  );
}

function filterOptionLabel(key: FilterKey, value: string, clusterLabels: Record<string, string>, opportunityLabels: Record<string, string>) {
  if (key === 'cluster_id') return clusterLabels[value] || patternGroupLabel(value);
  if (key === 'opportunity_id') return opportunityAreaLabel(value, opportunityLabels[value]);
  if (key === 'purchase_intent') return purchaseIntentLabel(value);
  if (key === 'wishlist_intent') return wishlistIntentLabel(value);
  return pretty(value);
}

function FilterPanel({ options, clusterLabels, opportunityLabels, active, onChange, onClear }: {
  options: Record<string, string[]>;
  clusterLabels: Record<string, string>;
  opportunityLabels: Record<string, string>;
  active: ActiveFilters;
  onChange: (key: FilterKey, value: string) => void;
  onClear: () => void;
}) {
  const count = Object.values(active).filter(Boolean).length;
  const fields = (items: readonly (readonly [FilterKey, string])[]) => items.map(([key, label]) => (
    <label key={key} className="block">
      <span className="mb-1.5 block text-[11px] font-semibold text-[#53615b]">{label}</span>
      <select className={`field research-filter ${active[key] ? 'research-filter--active' : ''}`} value={active[key]} onChange={event => onChange(key, event.target.value)} aria-label={label}>
        <option value="">All {label.toLowerCase()}s</option>
        {(options[key] || []).map(option => <option key={option} value={option}>{filterOptionLabel(key, option, clusterLabels, opportunityLabels)}</option>)}
      </select>
    </label>
  ));

  return (
    <div className="surface overflow-hidden">
      <div className="flex items-center justify-between border-b border-[#e5e9e6] px-4 py-3.5">
        <div><h2 className="text-sm font-semibold text-[#25302c]">Filters</h2><p className="mt-0.5 text-[10px] text-[#7b8580]">{count ? `${count} active` : 'All evidence'}</p></div>
        {count > 0 && <button type="button" onClick={onClear} className="text-xs font-semibold text-[#285e52] hover:underline">Clear all</button>}
      </div>
      <div className="space-y-7 p-4">
        <fieldset>
          <legend className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.13em] text-[#6e5a7e]"><span className="h-2 w-2 rounded-sm bg-[#b9a8c3]" />Research links</legend>
          <div className="space-y-4">{fields(phase4Filters)}</div>
        </fieldset>
        <fieldset className="border-t border-[#e5e9e6] pt-6">
          <legend className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.13em] text-[#23735f]"><span className="h-2 w-2 rounded-sm bg-[#75a999]" />Customer evidence</legend>
          <div className="space-y-4">{fields(phase3Filters)}</div>
        </fieldset>
      </div>
    </div>
  );
}

function EvidenceCard({ observation, selected, onSelect }: { observation: ObservationResponse; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" onClick={onSelect} aria-pressed={selected} className={`surface w-full p-4 text-left transition ${selected ? 'border-[#75a999] ring-2 ring-[#dcebe5]' : 'hover:border-[#afc2b9] hover:shadow-[var(--shadow-md)]'}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="badge badge--canonical">Customer evidence</span>
        <SourceLabel source={observation.source} />
      </div>
      <blockquote className="quote-text mt-4 text-[15px]">“{displayEvidenceQuote(observation.evidence_quote)}”</blockquote>
      <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-[#e5e9e6] pt-3 text-xs">
        <div><dt className="text-[10px] uppercase tracking-[0.08em] text-[#8d9692]">What got in the way</dt><dd className="mt-1 font-medium text-[#43504b]">{pretty(observation.primary_barrier)}</dd></div>
        <div><dt className="text-[10px] uppercase tracking-[0.08em] text-[#8d9692]">Buying signal</dt><dd className="mt-1 font-medium text-[#43504b]">{purchaseIntentLabel(observation.purchase_intent)}</dd></div>
      </dl>
    </button>
  );
}

function EvidenceSkeleton() {
  return <div className="space-y-3 p-4" aria-label="Loading evidence" aria-busy="true">{[0,1,2,3,4,5].map(item => <div key={item} className="skeleton h-16 rounded-xl" />)}</div>;
}

function EvidenceExplorer() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evidenceData, setEvidenceData] = useState<EvidenceListResponse | null>(null);
  const [filterOptions, setFilterOptions] = useState<Record<string, string[]>>({});
  const [clusterLabels, setClusterLabels] = useState<Record<string, string>>({});
  const [opportunityLabels, setOpportunityLabels] = useState<Record<string, string>>({});
  const [selectedObsId, setSelectedObsId] = useState<string | null>(null);
  const [obsDetail, setObsDetail] = useState<ObservationDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '');
  const [filtersOpen, setFiltersOpen] = useState(false);

  const page = Math.max(parseInt(searchParams.get('page') || '1', 10) || 1, 1);
  const size = Math.max(parseInt(searchParams.get('size') || '20', 10) || 20, 1);
  const search = searchParams.get('search') || '';
  const observationIdFromUrl = searchParams.get('observation_id');
  const activeFilters = useMemo<ActiveFilters>(() => ({
    source: searchParams.get('source') || '', wishlist_intent: searchParams.get('wishlist_intent') || '',
    purchase_intent: searchParams.get('purchase_intent') || '', primary_barrier: searchParams.get('primary_barrier') || '',
    journey_stage: searchParams.get('journey_stage') || '', decision_outcome: searchParams.get('decision_outcome') || '',
    predefined_theme: searchParams.get('predefined_theme') || '', cluster_id: searchParams.get('cluster_id') || '',
    opportunity_id: searchParams.get('opportunity_id') || '',
  }), [searchParams]);
  const activeCount = Object.values(activeFilters).filter(Boolean).length;

  const updateParams = useCallback((updates: Record<string, string | number>) => {
    const current = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value === '' || (value === 1 && key === 'page')) current.delete(key);
      else current.set(key, String(value));
    }
    const query = current.toString();
    router.push(query ? `/evidence?${query}` : '/evidence');
  }, [router, searchParams]);

  const clearFilters = useCallback(() => {
    const updates: Record<string, string | number> = { page: 1 };
    Object.keys(activeFilters).forEach(key => { updates[key] = ''; });
    updateParams(updates);
  }, [activeFilters, updateParams]);

  useEffect(() => {
    api.filterOptions().then(setFilterOptions).catch(() => setFilterOptions({}));
    api.clusters()
      .then(clusters => setClusterLabels(Object.fromEntries(clusters.map(cluster => [cluster.cluster_id, patternGroupLabel(cluster.cluster_id, cluster.canonical_label)]))))
      .catch(() => setClusterLabels({}));
    api.opportunities()
      .then(opportunities => setOpportunityLabels(Object.fromEntries(opportunities.map(opportunity => [opportunity.opportunity_id, opportunity.title]))))
      .catch(() => setOpportunityLabels({}));
  }, []);

  const fetchEvidence = useCallback(async () => {
    setLoading(true); setError(null);
    try { setEvidenceData(await api.evidence({ page, size, search, ...activeFilters })); }
    catch (err) { setError(err instanceof Error ? err.message : 'Evidence could not be loaded.'); }
    finally { setLoading(false); }
  }, [page, size, search, activeFilters]);

  useEffect(() => { queueMicrotask(() => { void fetchEvidence(); }); }, [fetchEvidence]);

  useEffect(() => {
    const handler = window.setTimeout(() => {
      if (searchTerm !== search && (searchTerm.length >= 3 || searchTerm.length === 0)) updateParams({ search: searchTerm, page: 1 });
    }, 450);
    return () => window.clearTimeout(handler);
  }, [searchTerm, search, updateParams]);

  const loadDetail = useCallback(async (id: string) => {
    setSelectedObsId(id); setObsDetail(null); setDetailError(null); setDetailLoading(true);
    try { setObsDetail(await api.evidenceDetail(id)); }
    catch (err) { setDetailError(err instanceof Error ? err.message : 'This evidence record could not be loaded.'); }
    finally { setDetailLoading(false); }
  }, []);

  useEffect(() => {
    if (observationIdFromUrl && observationIdFromUrl !== selectedObsId) queueMicrotask(() => { void loadDetail(observationIdFromUrl); });
  }, [observationIdFromUrl, selectedObsId, loadDetail]);

  const closeDetail = useCallback(() => {
    setSelectedObsId(null); setObsDetail(null); setDetailError(null);
    if (observationIdFromUrl) updateParams({ observation_id: '' });
  }, [observationIdFromUrl, updateParams]);

  useEffect(() => {
    if (!selectedObsId) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && closeDetail();
    window.addEventListener('keydown', onKey);
    return () => { document.body.style.overflow = previous; window.removeEventListener('keydown', onKey); };
  }, [selectedObsId, closeDetail]);

  const handleFilterChange = (key: FilterKey, value: string) => updateParams({ [key]: value, page: 1 });
  return (
    <div className="page-shell max-w-[1600px]">
      <header className="page-header">
        <div>
          <span className="eyebrow">Customer feedback library</span>
          <h1 className="page-title">Evidence Explorer</h1>
          <p className="page-description">Read what customers said first, then inspect the shopping context and analysis linked to each record.</p>
        </div>
        <div className="w-full sm:w-auto">
          <div className="relative min-w-0 sm:w-[320px]">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-[#7b8580]"><circle cx="10.5" cy="10.5" r="5.5"/><path d="m15 15 4 4" strokeLinecap="round"/></svg>
            <input type="search" placeholder="Search evidence quotes" aria-label="Search evidence quotes" className="field field-with-icon" value={searchTerm} onChange={event => setSearchTerm(event.target.value)} />
          </div>
        </div>
      </header>

      <div className="mb-4 min-[1350px]:hidden">
        <button type="button" onClick={() => setFiltersOpen(open => !open)} className="btn-secondary evidence-filter-toggle w-full justify-between" aria-expanded={filtersOpen}>
          <span>Filters {activeCount > 0 && <span className="ml-1 rounded-full bg-[#e7f1ed] px-2 py-0.5 text-[11px] text-[#285e52]">{activeCount}</span>}</span>
          <span aria-hidden="true">{filtersOpen ? '−' : '+'}</span>
        </button>
      </div>

      <div className="grid min-w-0 grid-cols-1 gap-5 min-[1350px]:grid-cols-[250px_minmax(0,1fr)]">
        <aside aria-label="Evidence filters" className={`${filtersOpen ? 'block' : 'hidden'} min-[1350px]:block`}>
          <div className="min-[1350px]:sticky min-[1350px]:top-5"><FilterPanel options={filterOptions} clusterLabels={clusterLabels} opportunityLabels={opportunityLabels} active={activeFilters} onChange={handleFilterChange} onClear={clearFilters} /></div>
        </aside>

        <section className="surface min-w-0 overflow-hidden" aria-label="Evidence records">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e1e6e3] bg-[#f8f9f7] px-4 py-3 sm:px-5">
            <div><h2 className="text-sm font-semibold text-[#25302c]">Customer evidence</h2><p className="mt-0.5 text-[11px] text-[#69756f]">{evidenceData ? `${evidenceData.total.toLocaleString()} matching records · clearer, more complete quotes shown first` : 'Loading feedback'}</p></div>
            {activeCount > 0 && <span className="badge">{activeCount} active filter{activeCount === 1 ? '' : 's'}</span>}
          </div>

          {error ? (
            <div className="state-card">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-[#fbebea] text-[#9d3d3d]" aria-hidden="true">!</span>
              <h3 className="text-base font-semibold text-[#17201d]">Evidence could not be loaded</h3>
              <p className="max-w-md text-sm leading-6 text-[#69756f]">{error}</p>
              <button type="button" onClick={() => void fetchEvidence()} className="btn-secondary">Retry</button>
            </div>
          ) : loading ? <EvidenceSkeleton /> : !evidenceData?.items.length ? (
            <div className="state-card">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-[#edf2ef] text-[#60716a]" aria-hidden="true">∅</span>
              <h3 className="text-base font-semibold text-[#17201d]">No matching evidence</h3>
              <p className="max-w-md text-sm leading-6 text-[#69756f]">Try a broader phrase or clear the active filters. No answer will be inferred without supporting customer evidence.</p>
              {(activeCount > 0 || search) && <button type="button" onClick={() => { setSearchTerm(''); clearFilters(); }} className="btn-secondary">Clear filters</button>}
            </div>
          ) : (
            <>
              <div className="hidden min-w-0 overflow-hidden xl:block">
                <table className="w-full table-fixed text-left text-sm">
                  <thead className="border-b border-[#dfe5e1] bg-white text-[10px] font-bold uppercase tracking-[0.1em] text-[#7b8580]">
                    <tr><th className="w-[42%] whitespace-normal px-5 py-3 leading-4">What the customer wrote</th><th className="w-[13%] whitespace-normal px-3 py-3 leading-4">Source</th><th className="w-[21%] whitespace-normal px-3 py-3 leading-4">Issue and buying signal</th><th className="w-[24%] whitespace-normal px-3 py-3 leading-4">Where they were in the journey</th></tr>
                  </thead>
                  <tbody className="divide-y divide-[#e7ebe8]">
                    {evidenceData.items.map(observation => (
                      <tr key={observation.observation_id} tabIndex={0} aria-selected={selectedObsId === observation.observation_id} onClick={() => void loadDetail(observation.observation_id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); void loadDetail(observation.observation_id); } }} className={`cursor-pointer align-top outline-none transition hover:bg-[var(--surface-muted)] focus-visible:bg-[var(--surface-muted)] ${selectedObsId === observation.observation_id ? 'bg-[var(--surface-raised)]' : ''}`}>
                        <td className="px-5 py-4"><p className="line-clamp-3 whitespace-normal font-serif text-[14px] leading-6 text-[#25302c]">“{displayEvidenceQuote(observation.evidence_quote)}”</p></td>
                        <td className="min-w-0 px-3 py-4"><SourceLabel source={observation.source} /></td>
                        <td className="min-w-0 px-3 py-4"><p className="break-words text-xs font-medium text-[#43504b]">{pretty(observation.primary_barrier)}</p><p className="mt-1 break-words text-[11px] text-[#7b8580]">{purchaseIntentLabel(observation.purchase_intent)}</p></td>
                        <td className="min-w-0 px-3 py-4"><p className="break-words text-xs font-medium text-[#43504b]">{pretty(observation.journey_stage)}</p><p className="mt-1 break-words text-[11px] text-[#7b8580]">Result · {pretty(observation.decision_outcome)}</p></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="space-y-3 bg-[#f8f9f7] p-3 xl:hidden">
                {evidenceData.items.map(observation => <EvidenceCard key={observation.observation_id} observation={observation} selected={selectedObsId === observation.observation_id} onSelect={() => void loadDetail(observation.observation_id)} />)}
              </div>
              <div className="flex flex-col gap-3 border-t border-[#e1e6e3] bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
                <p className="text-xs text-[#69756f]">Showing <strong className="font-semibold text-[#43504b]">{(page - 1) * size + 1}–{Math.min(page * size, evidenceData.total)}</strong> of {evidenceData.total.toLocaleString()}</p>
                <div className="grid grid-cols-2 gap-2"><button type="button" disabled={page === 1} onClick={() => updateParams({ page: page - 1 })} className="btn-secondary min-h-9 px-3 py-2">Previous</button><button type="button" disabled={page * size >= evidenceData.total} onClick={() => updateParams({ page: page + 1 })} className="btn-secondary min-h-9 px-3 py-2">Next</button></div>
              </div>
            </>
          )}
        </section>
      </div>

      {selectedObsId && (
        <div className="fixed inset-0 z-[60] flex justify-end" role="presentation">
          <button type="button" className="absolute inset-0 cursor-default bg-[#14231f]/35 backdrop-blur-[2px]" onClick={closeDetail} aria-label="Close evidence detail" />
          <aside role="dialog" aria-modal="true" aria-labelledby="evidence-detail-title" className="relative z-10 flex h-full w-full max-w-[680px] flex-col overflow-hidden bg-[#f8f9f7] shadow-2xl">
            <header className="flex min-h-[68px] items-center justify-between gap-4 border-b border-[#dfe5e1] bg-white px-5 sm:px-7">
              <div><span className="eyebrow mb-1">Record inspection</span><h2 id="evidence-detail-title" className="text-base font-semibold text-[#17201d]">Evidence Detail</h2></div>
              <button type="button" onClick={closeDetail} className="grid h-11 w-11 place-items-center rounded-xl text-[#69756f] hover:bg-[#edf0ee]" aria-label="Close evidence detail"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5"><path strokeLinecap="round" d="m6 6 12 12M18 6 6 18"/></svg></button>
            </header>
            <div className="flex-1 overflow-y-auto px-5 py-6 sm:px-7 sm:py-8">
              {detailLoading ? <div className="space-y-5" aria-busy="true"><div className="rounded-xl border border-[var(--line-strong)] bg-[var(--surface-raised)] p-4"><h3 className="text-sm font-semibold text-[var(--ink)]">Loading evidence details…</h3><p className="mt-1 text-xs text-[var(--muted)]">Retrieving the customer quote and its linked analysis.</p></div><div className="skeleton h-44 rounded-2xl"/><div className="grid grid-cols-2 gap-3">{[0,1,2,3].map(i=><div key={i} className="skeleton h-20 rounded-xl"/>)}</div><div className="skeleton h-48 rounded-2xl"/></div> : detailError ? (
                <div className="state-card surface"><span className="grid h-10 w-10 place-items-center rounded-full bg-[#fbebea] text-[#9d3d3d]">!</span><h3 className="text-base font-semibold">Evidence detail unavailable</h3><p className="max-w-sm text-sm leading-6 text-[#69756f]">{detailError}</p><button type="button" onClick={() => void loadDetail(selectedObsId)} className="btn-secondary">Retry</button></div>
              ) : obsDetail ? <EvidenceDetail detail={obsDetail} clusterLabels={clusterLabels} opportunityLabels={opportunityLabels} /> : null}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function EvidenceDetail({ detail, clusterLabels, opportunityLabels }: { detail: ObservationDetailResponse; clusterLabels: Record<string, string>; opportunityLabels: Record<string, string> }) {
  const canonicalFields = [
    ['Source', pretty(detail.source)], ['Journey stage', pretty(detail.journey_stage)], ['Decision outcome', pretty(detail.decision_outcome)],
    ['What got in the way', pretty(detail.primary_barrier)], ['Buying signal', purchaseIntentLabel(detail.purchase_intent)], ['Wishlist signal', wishlistIntentLabel(detail.wishlist_intent)],
  ];
  return (
    <div className="space-y-8">
      <section aria-labelledby="canonical-heading">
        <div className="flex items-center justify-between gap-3"><div><span className="badge badge--canonical">Customer evidence</span><h3 id="canonical-heading" className="sr-only">Customer evidence</h3></div><span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#7b8580]">Source-backed record</span></div>
        <div className="mt-4 rounded-2xl border border-[#bfd9cf] bg-white p-5 shadow-[var(--shadow-sm)] sm:p-6"><blockquote className="quote-text text-[1.12rem] sm:text-[1.22rem]">“{displayEvidenceQuote(detail.evidence_quote)}”</blockquote>{hasPrivacyMask(detail.evidence_quote) && <p className="mt-4 border-t border-[#30243b] pt-3 text-[10px] leading-4 text-[#766b7d]">[…] marks text hidden by automated privacy protection. Multilingual or product words may occasionally be hidden by mistake.</p>}</div>
        <dl className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-[#dfe5e1] bg-[#dfe5e1] sm:grid-cols-3">
          {canonicalFields.map(([label, value]) => <div key={label} className="min-w-0 bg-white p-3.5"><dt className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#8d9692]">{label}</dt><dd className="mt-1 truncate text-xs font-medium text-[#43504b]" title={value}>{value}</dd></div>)}
        </dl>
        <div className="mt-3 flex flex-col justify-between gap-2 text-[11px] text-[#7b8580] sm:flex-row sm:items-center"><span className="min-w-0 truncate font-mono" title={detail.source_record_id}>Source record · {detail.source_record_id}</span>{detail.source_url && <a href={detail.source_url} target="_blank" rel="noopener noreferrer" className="shrink-0 font-semibold text-[#285e52] hover:underline">View original source ↗</a>}</div>
      </section>

      <section aria-labelledby="derived-heading" className="rounded-2xl border border-[#ded5e3] bg-[#f5f1f6] p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><span className="badge badge--derived">What the evidence suggests</span><h3 id="derived-heading" className="mt-3 text-sm font-semibold text-[#3e3346]">How this quote was organized</h3></div>{detail.ai_confidence !== null && <span className="text-[10px] leading-4 text-[#786c80]">Automated match score {detail.ai_confidence.toFixed(2)}<br/><em>directional only</em></span>}</div>
        <p className="mt-2 text-xs leading-5 text-[#786c80]">These labels were added by the analysis. They are not part of the customer’s words and should be treated as guidance, not proven fact.</p>
        <div className="mt-5 space-y-5 border-t border-[#ded5e3] pt-5">
          <TagGroup label="Related themes" values={detail.predefined_themes} />
          <TagGroup label="Patterns found in feedback" values={detail.emergent_clusters} formatValue={value => clusterLabels[value] || patternGroupLabel(value)} />
          <TagGroup label="Related opportunity areas" values={detail.opportunity_ids} formatValue={value => opportunityAreaLabel(value, opportunityLabels[value])} />
        </div>
      </section>
    </div>
  );
}

function TagGroup({ label, values, formatValue = pretty }: { label: string; values?: string[]; formatValue?: (value: string) => string }) {
  return <div><h4 className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#786c80]">{label}</h4><div className="mt-2 flex flex-wrap gap-2">{values?.length ? values.map(value => <span key={value} className="rounded-md border border-[#d7ccdc] bg-white px-2.5 py-1.5 text-xs font-medium text-[#5e4c69]">{formatValue(value)}</span>) : <span className="text-xs text-[#8a7f91]">No related label assigned.</span>}</div></div>;
}

export default function EvidenceClient() {
  return <Suspense fallback={<div className="page-shell"><EvidenceSkeleton /></div>}><EvidenceExplorer /></Suspense>;
}
