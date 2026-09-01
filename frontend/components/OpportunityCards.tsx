import { OpportunityStat } from "../lib/api";
import { displayEvidenceQuote } from "../lib/plainLanguage";
import { useState } from "react";
import Link from "next/link";

export default function OpportunityCards({ opportunities }: { opportunities: OpportunityStat[] }) {
  if (!opportunities?.length) return null;

  return (
    <section className="mb-16 mt-16" aria-labelledby="opportunity-heading">
      <div className="section-header">
        <div>
          <span className="eyebrow">Where a closer look can help</span>
          <h2 id="opportunity-heading" className="section-title text-[1.55rem]">Priority areas to investigate</h2>
          <p className="section-description max-w-2xl">Issue-specific evidence that may affect purchase confidence. Positive and mixed-experience clusters are excluded from these totals.</p>
        </div>
        <span className="text-xs font-medium text-[var(--muted)]">{opportunities.length} areas · ordered by reviewed evidence</span>
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        {opportunities.map((opp, index) => <OpportunityCard key={opp.opportunity_id} opp={opp} index={index} />)}
      </div>
    </section>
  );
}

function OpportunityCard({ opp, index }: { opp: OpportunityStat; index: number }) {
  const [activeQuote, setActiveQuote] = useState(0);
  const quote = opp.representative_quotes?.[activeQuote];

  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-[18px] border border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow-sm)] transition duration-200 hover:-translate-y-0.5 hover:border-[var(--line-strong)] hover:shadow-[var(--shadow-md)]">
      <span className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-[#ff3f6c] via-[#ff7a65] to-[#bc8cff] opacity-80" aria-hidden="true" />
      <Link href={`/dashboard/opportunities/${opp.opportunity_id}`} className="absolute inset-0 z-0 rounded-[18px]" aria-label={`Open opportunity: ${opp.title}`} />
      <div className="relative z-10 flex flex-1 flex-col p-5 pointer-events-none sm:p-6">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8d9692]">Area {String(index + 1).padStart(2, '0')}</span>
          <div className="mt-2"><span className="badge badge--evidence !font-medium">Recurring issue</span></div>
        </div>

        <h3 className="mt-6 text-[1.12rem] font-semibold leading-[1.4] tracking-[-0.025em] text-[var(--ink)] transition-colors group-hover:text-[#ff5d82] xl:min-h-[4.7rem]">{opp.title}</h3>

        <div className="mt-6 border-l-2 border-[#4a806f] pl-4 xl:min-h-[5.625rem]">
          <span className="text-[10px] font-bold uppercase tracking-[0.13em] text-[var(--muted)]">What shoppers appear to need</span>
          <p className="mt-1.5 text-[13px] font-medium leading-5 text-[var(--ink-soft)]">{opp.supporting_unmet_needs?.[0] || "No unmet need specified."}</p>
        </div>

        {quote && (
          <div className="mt-6 border-t border-[var(--line)] pt-5">
            <div className="flex items-start justify-between gap-3 xl:min-h-[1.875rem]">
              <span className="text-[10px] font-bold uppercase tracking-[0.13em] text-[var(--muted)]">Representative evidence</span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--canonical)]">{quote.source?.replaceAll('_', ' ') || 'Unknown source'}</span>
            </div>
            <blockquote className="quote-text mt-3 line-clamp-3 min-h-[4.9rem] text-[14px]">“{displayEvidenceQuote(quote.quote)}”</blockquote>
            {opp.representative_quotes.length > 1 && (
              <div className="pointer-events-auto relative z-20 mt-3 flex gap-1.5" aria-label="Representative evidence selector">
                {opp.representative_quotes.map((_, quoteIndex) => (
                  <button
                    type="button"
                    key={quoteIndex}
                    onClick={() => setActiveQuote(quoteIndex)}
                    className={`h-2 rounded-full transition-all ${quoteIndex === activeQuote ? 'w-5 bg-[#ff3f6c]' : 'w-2 bg-[var(--line-strong)] hover:bg-[var(--faint)]'}`}
                    aria-label={`View quote ${quoteIndex + 1}`}
                    aria-pressed={quoteIndex === activeQuote}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        <div className="mt-auto flex flex-col items-start gap-3 pt-7">
          <span className="text-[11px] font-medium text-[var(--muted)]">{opp.unique_source_count.toLocaleString()} supporting feedback records</span>
          <span className="text-[12px] font-semibold text-[var(--canonical)] transition-transform group-hover:translate-x-0.5">View supporting evidence →</span>
        </div>
      </div>
    </article>
  );
}
