import Link from "next/link";
import { DistributionResponse } from "../lib/api";

const GROUPS = [
  {
    key: "genuine_purchase",
    label: "Ready-to-buy savers",
    description: "Saved with a stated intention to purchase.",
  },
  {
    key: "comparison_shortlist",
    label: "Product comparers",
    description: "Saved while weighing the item against alternatives.",
  },
  {
    key: "inspiration",
    label: "Inspiration collectors",
    description: "Saved for styling ideas or visual reference.",
  },
  {
    key: "price_tracking",
    label: "Deal waiters",
    description: "Saved to monitor a lower price or offer.",
  },
  {
    key: "occasion_planning",
    label: "Occasion planners",
    description: "Saved for a future event or specific need.",
  },
  {
    key: "bookmarking",
    label: "Revisit bookmarkers",
    description: "Saved mainly so the product could be found again.",
  },
  {
    key: "aspirational_saving",
    label: "Aspirational savers",
    description: "Liked and saved despite weak or distant purchase intent.",
  },
] as const;

export default function WishlistBehaviorGroups({ data }: { data: DistributionResponse }) {
  const counts = new Map(data.items.map((item) => [item.name.toLowerCase(), item.count]));
  const groups = GROUPS.map((group) => ({ ...group, count: counts.get(group.key) || 0 })).filter((group) => group.count > 0);
  const classifiedTotal = groups.reduce((sum, group) => sum + group.count, 0);
  const unclassifiedTotal = Math.max(data.denominator - classifiedTotal, 0);
  const coveragePercentage = data.denominator > 0 ? (classifiedTotal / data.denominator) * 100 : 0;

  return (
    <section aria-labelledby="wishlist-groups-heading">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h3 id="wishlist-groups-heading" className="text-[17px] font-semibold tracking-[-0.015em] text-[var(--ink)]">Wishlist behaviour groups found in the evidence</h3>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-[var(--muted)]">How clearly expressed saving purposes differ across the existing customer feedback.</p>
        </div>
        <div className="shrink-0 text-left sm:text-right">
          <strong className="block text-lg tabular-nums text-[var(--ink)]">{classifiedTotal.toLocaleString()}</strong>
          <span className="text-[10px] font-semibold uppercase tracking-[0.09em] text-[var(--muted)]">classified records</span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {groups.map((group) => {
          const percentage = classifiedTotal > 0 ? (group.count / classifiedTotal) * 100 : 0;
          return (
            <Link
              key={group.key}
              href={`/evidence?wishlist_intent=${group.key}`}
              className="surface group flex min-h-[11.25rem] flex-col p-4 transition hover:-translate-y-0.5 hover:border-[var(--line-strong)] hover:shadow-[var(--shadow-md)]"
            >
              <span className="text-[13px] font-semibold leading-5 text-[var(--ink)]">{group.label}</span>
              <span className="mt-1 text-[11px] leading-[1.55] text-[var(--muted)]">{group.description}</span>
              <span className="mt-auto pt-4">
                <span className="flex items-end justify-between gap-3">
                  <strong className="text-[1.45rem] font-semibold leading-none tabular-nums text-[var(--ink)]">{group.count.toLocaleString()}</strong>
                  <span className="text-xs tabular-nums text-[var(--muted)]">{percentage.toFixed(1)}%</span>
                </span>
                <span className="mt-2 block h-1.5 overflow-hidden rounded-full bg-[var(--surface-raised)]">
                  <span className="block h-full rounded-full bg-gradient-to-r from-[#ff3f6c] to-[#ff8a5c]" style={{ width: `${Math.max(percentage, 2)}%` }} />
                </span>
                <span className="mt-3 block text-[10px] font-semibold text-[var(--brand)]">View evidence →</span>
              </span>
            </Link>
          );
        })}

        <article className="surface flex min-h-[11.25rem] flex-col border-dashed p-4">
          <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--muted)]">Classification coverage</span>
          <strong className="mt-3 text-[1.45rem] font-semibold leading-none tabular-nums text-[var(--ink)]">{coveragePercentage.toFixed(1)}%</strong>
          <p className="mt-2 text-[11px] leading-[1.55] text-[var(--muted)]">of all records contained enough information to identify why an item was saved.</p>
          <p className="mt-auto border-t border-[var(--line)] pt-3 text-[10px] leading-4 text-[var(--faint)]">{unclassifiedTotal.toLocaleString()} records remain unclassified.</p>
        </article>
      </div>

      <p className="mt-3 text-[10px] leading-4 text-[var(--faint)]">
        Group percentages compare the {classifiedTotal.toLocaleString()} classified feedback records—not unique shoppers.
      </p>
    </section>
  );
}
