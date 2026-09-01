import { DatasetStats } from "../lib/api";

export default function StatsCards({ stats }: { stats: DatasetStats | null }) {
  if (!stats) return null;

  const cards = [
    {
      label: "Records retained",
      value: stats.cleaned_records.toLocaleString(),
      suffix: "records",
      detail: "After duplicates and spam were removed",
    },
    {
      label: "Shopping-related feedback",
      value: stats.relevant_records.toLocaleString(),
      suffix: "records",
      detail: "Feedback with useful shopping context",
    },
    {
      label: "Customer observations",
      value: stats.canonical_observations.toLocaleString(),
      suffix: "observations",
      detail: "Organized by issue and shopping stage",
    },
    {
      label: "Public channels",
      value: Object.keys(stats.source_distribution_analyzed).length.toString(),
      suffix: "sources",
      detail: Object.keys(stats.source_distribution_analyzed)
        .map(source => source.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase()))
        .map(source => source.replace('Youtube', 'YouTube'))
        .join(" · "),
    },
  ];

  return (
    <section aria-label="Dataset overview" className="mb-14 grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
      {cards.map(card => (
        <article key={card.label} className="surface overview-card min-w-0 p-4 sm:p-5">
          <p className="text-xs font-bold leading-5 text-[var(--ink-soft)]">{card.label}</p>
          <div className="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <strong className="text-2xl font-bold tracking-[-0.04em] text-[var(--ink)] sm:text-[2rem]">{card.value}</strong>
            {card.suffix && <span className="text-[11px] font-medium text-[var(--ink-soft)]">{card.suffix}</span>}
          </div>
          <p className="mt-2 min-h-8 text-[11px] font-medium leading-4 text-[var(--muted)]">{card.detail}</p>
        </article>
      ))}
    </section>
  );
}
