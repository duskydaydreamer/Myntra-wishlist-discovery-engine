'use client';

import React, { useEffect, useState } from 'react';
import { api, ApiError, EvidenceRecord, QueryResponse } from '@/lib/api';
import { displayEvidenceQuote, patternGroupLabel, plainResearchLanguage } from '@/lib/plainLanguage';
import Link from 'next/link';

const STARTER_QUESTIONS = [
  'What are the top barriers?',
  'What sizing uncertainties do shoppers report?',
  'What evidence supports pricing trust concerns?',
  'What delivery or return friction do users describe?',
  'What barriers prevent high-intent users from purchasing?',
  'What information do shoppers look for before buying on Myntra?',
];

const pretty = (value: string) => plainResearchLanguage(value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase()));

const questionTypeLabel = (value: string) => {
  if (value === 'count_filter') return 'Count matching feedback';
  if (value === 'ranked_barriers') return 'Rank barriers in the full dataset';
  if (value === 'focused_evidence') return 'Examine one issue across the dataset';
  if (value === 'ranked_information_needs') return 'Rank stated information needs';
  if (value.startsWith('ranked_')) return 'Rank matching signals in the full dataset';
  return 'Explain what the evidence shows';
};

function searchMethodLabel(value: string) {
  if (value === 'deterministic') return 'Exact data match';
  if (value === 'filtered_semantic') return 'Filters plus meaning-based search';
  if (value === 'semantic_only') return 'Meaning-based search';
  if (value === 'filtered_keyword') return 'Filters plus keyword matching';
  if (value === 'keyword_only') return 'Keyword matching';
  return pretty(value);
}

function QueryLoading() {
  return (
    <div className="surface p-5 sm:p-7" aria-label="Synthesizing evidence" aria-busy="true">
      <div className="flex items-center gap-3"><span className="relative flex h-3 w-3"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#6f9b8f] opacity-50"/><span className="relative h-3 w-3 rounded-full bg-[#285e52]"/></span><span className="text-sm font-semibold text-[#34423c]">Investigating the customer evidence</span></div>
      <p className="mt-2 text-xs leading-5 text-[#69756f]">Understanding the question, finding relevant evidence, and grounding the response.</p>
      <div className="mt-6 space-y-3"><div className="skeleton h-5 w-3/4 rounded"/><div className="skeleton h-5 w-full rounded"/><div className="skeleton h-5 w-5/6 rounded"/><div className="skeleton mt-5 h-28 rounded-xl"/></div>
    </div>
  );
}

export default function QueryClient() {
  const [queryInput, setQueryInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [expandedEvidence, setExpandedEvidence] = useState<Set<string>>(new Set());

  useEffect(() => {
    try {
      const stored = localStorage.getItem('myntra_query_history');
      if (stored) queueMicrotask(() => setHistory(JSON.parse(stored).slice(0, 10)));
    } catch { queueMicrotask(() => setHistory([])); }
  }, []);

  const saveHistory = (question: string) => {
    const next = [question, ...history.filter(item => item !== question)].slice(0, 10);
    setHistory(next);
    try { localStorage.setItem('myntra_query_history', JSON.stringify(next)); } catch { /* local storage is optional */ }
  };

  const submitQuery = async (question: string) => {
    const trimmed = question.trim();
    if (trimmed.length < 5) { setError('Enter a question with at least five characters.'); return; }
    setQueryInput(trimmed); setIsSubmitting(true); setError(null); setResponse(null); setExpandedEvidence(new Set());
    try {
      const result = await api.query({ query: trimmed });
      setResponse(result); saveHistory(trimmed);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) setError('The query limit was reached. Wait a moment, then try again.');
        else if (err.status === 503) setError('The analysis service is temporarily unavailable. Your saved evidence remains unchanged.');
        else setError(`The investigation could not be completed. ${err.message}`);
      } else setError('The investigation could not be completed. Please try again.');
    } finally { setIsSubmitting(false); }
  };

  const toggleEvidence = (id: string) => setExpandedEvidence(previous => {
    const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next;
  });

  return (
    <div className="page-shell max-w-[1380px]">
      <header className="page-header">
        <div>
          <span className="eyebrow">Explore customer feedback</span>
          <h1 className="page-title">Query Interface</h1>
          <p className="page-description">Ask a question, see how it was understood, and inspect the customer evidence behind the answer. This workspace does not generate product solutions.</p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_260px]">
        <main className="min-w-0">
          <section className="surface p-4 sm:p-6" aria-labelledby="composer-heading">
            <div className="flex items-start gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#e7f1ed] text-[#285e52]" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5"><circle cx="10.5" cy="10.5" r="5.5"/><path d="m15 15 4 4" strokeLinecap="round"/></svg></span>
              <div><h2 id="composer-heading" className="text-base font-semibold text-[#17201d]">Ask a question</h2><p className="mt-1 text-xs leading-5 text-[#69756f]">Questions are interpreted against the existing public-evidence dataset.</p></div>
            </div>
            <div className="mt-5 flex flex-col gap-2 sm:flex-row">
              <input type="text" value={queryInput} onChange={event => setQueryInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !isSubmitting) void submitQuery(queryInput); }} placeholder="What sizing uncertainties do shoppers report?" className="field min-h-[50px] flex-1 px-4 text-[15px]" disabled={isSubmitting} aria-label="Research question" />
              <button type="button" onClick={() => void submitQuery(queryInput)} disabled={isSubmitting} className="btn-primary min-h-[50px] px-6">{isSubmitting ? 'Investigating…' : 'Investigate'}</button>
            </div>
            {error && <div role="alert" className="mt-3 flex items-start gap-2 rounded-xl border border-[#edc8c5] bg-[#fbebea] p-3 text-sm leading-5 text-[#853737]"><span aria-hidden="true">!</span><span>{error}</span></div>}
          </section>

          {!response && !isSubmitting && (
            <section className="mt-8" aria-labelledby="starter-heading">
              <div className="section-header mb-4"><div><span className="eyebrow">Investigation prompts</span><h2 id="starter-heading" className="section-title">Start with a broad question</h2><p className="section-description">These prompts show the kinds of behavior, friction, and context the available feedback can investigate.</p></div></div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {STARTER_QUESTIONS.map((question, index) => (
                  <button key={question} type="button" onClick={() => void submitQuery(question)} className={`surface group flex min-h-[88px] items-center justify-between gap-4 p-4 text-left transition hover:-translate-y-0.5 hover:border-[#afc2b9] hover:shadow-[var(--shadow-md)] ${STARTER_QUESTIONS.length % 2 === 1 && index === STARTER_QUESTIONS.length - 1 ? 'md:col-span-2' : ''}`}>
                    <span><span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9692]">Prompt {String(index + 1).padStart(2, '0')}</span><span className="mt-1.5 block text-sm font-semibold leading-5 text-[#34423c]">{question}</span></span>
                    <span className="shrink-0 text-[#719084] transition-transform group-hover:translate-x-0.5" aria-hidden="true">→</span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {isSubmitting && <div className="mt-6"><QueryLoading /></div>}
          {response && !isSubmitting && <div className="mt-6"><ResearchResponse response={response} expandedEvidence={expandedEvidence} onToggle={toggleEvidence} /></div>}
        </main>

        <aside className="min-w-0" aria-label="Query history">
          <div className="surface overflow-hidden xl:sticky xl:top-5">
            <div className="border-b border-[var(--line)] px-4 py-3.5"><span className="eyebrow mb-1">Local activity</span><h2 className="text-sm font-semibold text-[var(--ink)]">Query history</h2></div>
            {history.length === 0 ? <p className="p-4 text-xs leading-5 text-[var(--muted)]">No investigations yet. Questions you ask will appear here on this device.</p> : <ol className="divide-y divide-[var(--line)]">{history.map((item, index) => {
              const isCurrent = response?.query === item;
              return <li key={`${item}-${index}`}><button type="button" onClick={() => void submitQuery(item)} aria-current={isCurrent ? 'true' : undefined} className={`group flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left text-xs font-medium leading-5 transition focus-visible:outline-none ${isCurrent ? 'bg-[var(--surface-raised)] text-[var(--brand)] shadow-[inset_3px_0_0_#ff3f6c]' : 'text-[var(--ink-soft)] hover:bg-[var(--surface-muted)] hover:text-[var(--ink)]'}`}><span>{item}</span><span className={`shrink-0 transition-transform group-hover:translate-x-0.5 ${isCurrent ? 'text-[var(--brand)]' : 'text-[var(--faint)]'}`} aria-hidden="true">→</span></button></li>;
            })}</ol>}
            <p className="border-t border-[var(--line)] bg-[var(--canvas-subtle)] px-4 py-3 text-[10px] leading-4 text-[var(--faint)]">Stored locally on this device.</p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function ResearchResponse({ response, expandedEvidence, onToggle }: { response: QueryResponse; expandedEvidence: Set<string>; onToggle: (id: string) => void }) {
  const activeFilters = Object.entries(response.applied_filters).filter(([, values]) => values?.length);
  const percentage = response.denominator != null && response.denominator > 0 && response.numerator != null
    ? Math.round(response.numerator / response.denominator * 100)
    : null;
  return (
    <article className="space-y-5" aria-label="Evidence-backed response">
      <section className="surface overflow-hidden">
        <div className="border-b border-[#e1e6e3] bg-[#f8f9f7] px-5 py-4 sm:px-6">
          <span className="eyebrow mb-1">Grounded answer</span>
          <h2 className="text-base font-semibold leading-6 text-[#17201d]">{response.query}</h2>
        </div>
        <div className="p-5 sm:p-6">
          {response.evidence_count === 0 && response.retrieval_mode !== 'deterministic' ? (
            <div className="state-card min-h-[14rem] p-4"><span className="grid h-10 w-10 place-items-center rounded-full bg-[#edf2ef] text-[#60716a]">∅</span><h3 className="text-base font-semibold">No supporting evidence found</h3><p className="max-w-md text-sm leading-6 text-[#69756f]">No customer evidence matched this question. Rephrase it or investigate a broader topic.</p></div>
          ) : (
            <>
              {response.numerator != null && response.denominator != null && (
                <div className="mb-6 grid grid-cols-1 gap-4 rounded-xl border border-[#c7d9d1] bg-[#edf5f1] p-4 sm:grid-cols-[auto_1fr] sm:items-center sm:p-5">
                  <div><span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-[#55786d]">Dataset-scoped metric</span><div className="mt-2 flex items-baseline gap-2"><strong className="text-3xl font-semibold tracking-[-0.04em] text-[#174a40]">{response.numerator.toLocaleString()}</strong><span className="text-sm text-[#60716a]">of {response.denominator.toLocaleString()}</span>{percentage !== null && <span className="rounded-md bg-white px-2 py-1 text-sm font-semibold text-[#285e52]">{percentage}%</span>}</div></div>
                  <dl className="text-xs leading-5 text-[#53615b]"><div><dt className="inline font-semibold">What was counted · </dt><dd className="inline">{plainResearchLanguage(response.denominator_definition || 'Relevant evidence records')}</dd></div>{response.denominator_scope && <div><dt className="inline font-semibold">Included data · </dt><dd className="inline">{plainResearchLanguage(response.denominator_scope)}</dd></div>}</dl>
                </div>
              )}
              <AnswerContent answer={response.answer} />
            </>
          )}
        </div>
      </section>

      <details className="surface overflow-hidden">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 marker:hidden sm:px-6"><span><span className="eyebrow mb-1">Interpretation details</span><strong className="text-sm font-semibold text-[#34423c]">How this query was handled</strong></span><span className="text-[#69756f]" aria-hidden="true">+</span></summary>
        <div className="border-t border-[#e1e6e3] bg-[#f8f9f7] px-5 py-5 sm:px-6">
          <dl className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
            <Meta label="Question type" value={questionTypeLabel(response.query_type)} /><Meta label="Search method" value={searchMethodLabel(response.retrieval_mode)} /><Meta label="Evidence found" value={`${response.evidence_count.toLocaleString()} records`} /><Meta label="Source channels" value={response.unique_source_count.toLocaleString()} />
          </dl>
          {activeFilters.length > 0 && <div className="mt-5 border-t border-[#e1e6e3] pt-4"><span className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#7b8580]">Active filters</span><div className="mt-2 flex flex-wrap gap-2">{activeFilters.map(([key, values]) => <span key={key} className="badge normal-case tracking-normal">{pretty(key)} · {values.map(pretty).join(', ')}</span>)}</div></div>}
          {response.retrieval_mode === 'semantic_only' && <p className="mt-4 rounded-lg border border-[#e4d3a9] bg-[#fbf4e4] p-3 text-xs leading-5 text-[#765116]">No exact filter matched strongly, so the search included feedback with similar meaning. Similar wording does not prove that a finding is true.</p>}
        </div>
      </details>

      {response.evidence.length > 0 && (
        <section aria-labelledby="supporting-evidence-heading">
          <div className="section-header mb-4"><div><span className="eyebrow">Traceability</span><h2 id="supporting-evidence-heading" className="section-title">Customer evidence behind this answer</h2><p className="section-description">Open any record to inspect the exact quote and its shopping context.</p></div></div>
          <div className="space-y-3">{response.evidence.map(evidence => <QueryEvidenceCard key={evidence.observation_id} evidence={evidence} expanded={expandedEvidence.has(evidence.observation_id)} onToggle={() => onToggle(evidence.observation_id)} />)}</div>
        </section>
      )}

      <aside className="flex items-start gap-2.5 rounded-xl border border-[#dfe5e1] bg-[#f0f3f1] px-4 py-3 text-xs leading-5 text-[#60716a]" aria-label="Dataset scope caveat"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="mt-0.5 h-4 w-4 shrink-0"><circle cx="12" cy="12" r="9"/><path d="M12 10.5v5M12 7.5h.01" strokeLinecap="round"/></svg><p><strong className="font-semibold text-[#43504b]">What this data can tell us · </strong>{plainResearchLanguage(response.dataset_scope_caveat)}</p></aside>
    </article>
  );
}

function AnswerContent({ answer }: { answer: string }) {
  const lines = plainResearchLanguage(answer).split('\n').filter(line => line.trim().length > 0);
  return <div className="space-y-3">{lines.map((line, index) => {
    const trimmed = line.trim();
    const kind = trimmed.startsWith('📌') ? 'said' : trimmed.startsWith('🔍') ? 'behavior' : trimmed.startsWith('💡') ? 'need' : null;
    if (kind) {
      const labels = { said: 'What users said', behavior: 'Observed or inferred behavior', need: 'Possible unmet need' };
      return <div key={index} className={`rounded-xl border p-4 ${kind === 'said' ? 'border-[#bddbce] bg-[#f2f8f5]' : kind === 'behavior' ? 'border-[#d9e1dc] bg-[#f8f9f7]' : 'border-[#d8ccde] bg-[#f5f1f6]'}`}><span className="block text-[10px] font-bold uppercase tracking-[0.11em] text-[#69756f]">{labels[kind]}</span><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#34423c]">{renderInline(trimmed.replace(/^[📌🔍💡]\s*/, ''))}</p></div>;
    }
    if (/^#{1,3}\s/.test(trimmed)) return <h3 key={index} className="pt-2 text-base font-semibold text-[#25302c]">{renderInline(trimmed.replace(/^#{1,3}\s+/, ''))}</h3>;
    if (/^[-*]\s/.test(trimmed)) return <p key={index} className="relative pl-5 text-[15px] leading-7 text-[#34423c] before:absolute before:left-1 before:top-0 before:content-['•']">{renderInline(trimmed.replace(/^[-*]\s+/, ''))}</p>;
    if (/^>\s?/.test(trimmed)) return <blockquote key={index} className="quote-text border-l-2 border-[#75a999] pl-4 text-[15px]">{renderInline(trimmed.replace(/^>\s?/, ''))}</blockquote>;
    return <p key={index} className="whitespace-pre-wrap text-[15px] leading-7 text-[#34423c]">{renderInline(trimmed)}</p>;
  })}</div>;
}

function renderInline(text: string) {
  return text.split('**').map((part, index) => index % 2 === 1 ? <strong key={index} className="font-semibold text-[#25302c]">{part}</strong> : part);
}

function Meta({ label, value }: { label: string; value: string }) { return <div><dt className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#8d9692]">{label}</dt><dd className="mt-1 font-medium text-[#43504b]">{value}</dd></div>; }

function QueryEvidenceCard({ evidence, expanded, onToggle }: { evidence: EvidenceRecord; expanded: boolean; onToggle: () => void }) {
  return (
    <article className={`surface overflow-hidden transition ${expanded ? 'border-[#4a806f]' : ''}`}>
      <button type="button" onClick={onToggle} aria-expanded={expanded} className="group flex w-full cursor-pointer items-start justify-between gap-4 p-4 text-left transition hover:bg-[var(--surface-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#6f9b8f] sm:p-5">
        <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><span className="badge badge--canonical">Customer evidence</span><span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">{pretty(evidence.source || 'Unknown source')}</span>{evidence.primary_barrier && <span className="text-[10px] text-[var(--faint)]">Barrier · {pretty(evidence.primary_barrier)}</span>}</div><blockquote className="quote-text mt-3 line-clamp-2 text-[15px]">“{displayEvidenceQuote(evidence.evidence_quote)}”</blockquote></div>
        <span className="mt-1 flex shrink-0 items-center gap-2 text-[10px] font-semibold text-[var(--canonical)]"><span className="hidden sm:inline">{expanded ? 'Hide details' : 'View details'}</span><span className={`grid h-8 w-8 place-items-center rounded-full bg-[var(--surface-muted)] text-[var(--muted)] transition-transform group-hover:bg-[var(--surface-raised)] ${expanded ? 'rotate-180' : ''}`} aria-hidden="true"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4" strokeLinecap="round" strokeLinejoin="round"><path d="m6 8 4 4 4-4" /></svg></span></span>
      </button>
      {expanded && <div className="border-t border-[var(--line)] bg-[var(--canvas-subtle)] p-4 sm:p-5"><div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><div><span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[var(--faint)]">Record details</span><p className="mt-2 break-all font-mono text-[11px] leading-5 text-[var(--muted)]">Observation · {evidence.observation_id}<br/>Source · {evidence.source_record_id || 'Not available'}</p></div><div><span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[var(--faint)]">Research context</span><p className="mt-2 text-xs leading-5 text-[var(--muted)]">Theme · {evidence.theme_context || 'Not assigned'}<br/>Feedback pattern · {evidence.cluster_context ? patternGroupLabel(evidence.cluster_context, evidence.cluster_context) : 'Not assigned'}</p></div></div><blockquote className="quote-text mt-5 rounded-xl border border-[var(--line)] bg-[var(--surface-muted)] p-4 text-[15px]">“{displayEvidenceQuote(evidence.evidence_quote)}”</blockquote><div className="mt-4 flex flex-wrap gap-2"><Link href={`/evidence?observation_id=${evidence.observation_id}`} className="btn-secondary min-h-9 px-3 py-2 text-xs">Open in Evidence Explorer</Link>{evidence.source_url && <a href={evidence.source_url} target="_blank" rel="noopener noreferrer" className="btn-quiet min-h-9 px-3 py-2 text-xs">View source ↗</a>}</div></div>}
    </article>
  );
}
