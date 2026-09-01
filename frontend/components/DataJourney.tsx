import { DatasetStats } from "../lib/api";

export default function DataJourney({ stats }: { stats?: DatasetStats }) {
  const steps = [
    { number: '01', title: 'Collection', detail: 'Public app reviews and video or community conversations.', metric: stats?.total_raw_records, unit: 'raw records' },
    { number: '02', title: 'Cleaning and privacy', detail: 'Deduplication, spam removal, and personal identity masking.', metric: stats?.cleaned_records, unit: 'records retained' },
    { number: '03', title: 'Relevance classification', detail: 'Shopping-intent evidence isolated for downstream analysis.', metric: stats?.relevant_records, unit: 'relevant records' },
    { number: '04', title: 'Organized for analysis', detail: 'Relevant comments grouped by source, issue, buying signal, and journey stage.', metric: stats?.canonical_observations, unit: 'organized observations' },
  ];
  return (
    <details className="surface overflow-hidden group">
      <summary className="flex min-h-[78px] cursor-pointer list-none items-center justify-between gap-5 px-5 py-4 marker:hidden sm:px-6">
        <div>
          <span className="eyebrow mb-1">Methodology</span>
          <h2 className="text-[15px] font-semibold text-[#25302c]">How this evidence was built</h2>
        </div>
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#edf2ef] text-[#60716a] transition-transform group-open:rotate-180" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4" strokeLinecap="round" strokeLinejoin="round"><path d="m6 8 4 4 4-4" /></svg>
        </span>
      </summary>
      <div className="border-t border-[#e1e6e3] bg-[#f8f9f7] px-5 py-6 sm:px-6">
        <p className="max-w-3xl text-sm leading-6 text-[#69756f]">Public conversations are cleaned and organized into comparable customer observations before patterns are identified. One source record may contain several distinct observations.</p>
        <ol className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {steps.map(step => (
            <li key={step.number} className="flex min-w-0 flex-col rounded-xl border border-[#dfe5e1] bg-white p-4 sm:p-5">
              <div className="flex min-h-7 items-center gap-2.5">
                <span className="w-5 shrink-0 text-[10px] font-semibold tracking-[0.08em] text-[#819088]">{step.number}</span>
                <h3 className="text-sm font-semibold leading-5 text-[#25302c]">{step.title}</h3>
              </div>
              <p className="mt-3 flex-1 text-xs leading-5 text-[#69756f]">{step.detail}</p>
              {step.metric !== undefined && (
                <p className="mt-5 flex items-baseline gap-2 border-t border-[#e7ebe8] pt-4 text-xs text-[#69756f]">
                  <strong className="shrink-0 text-xl font-semibold tracking-[-0.02em] text-[#34423c]">{step.metric.toLocaleString()}</strong>
                  <span className="leading-4">{step.unit}</span>
                </p>
              )}
            </li>
          ))}
        </ol>
      </div>
    </details>
  );
}
