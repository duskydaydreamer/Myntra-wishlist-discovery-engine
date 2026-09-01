interface DistributionItem { name: string; count: number }
interface DistributionBarProps { title: string; items: DistributionItem[]; total: number; limit?: number; unclassifiedCount?: number | null }

const formatLabel = (label: string) => label.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
const isUnclassified = (label: string) => {
  const value = label.trim();
  return !value
    || /^(unknown|unclear|not[_ ]classified|none|null|n\/a)$/i.test(value)
    || /^[\s?.,!:_-]+$/.test(value)
    || /(?:region[ _-]?restricted|free[ _-]?text)/i.test(value);
};

export default function DistributionBar({ title, items, total, limit = 5, unclassifiedCount }: DistributionBarProps) {
  const meaningfulItems = items.filter(item => !isUnclassified(item.name));
  const missingCount = unclassifiedCount ?? items.filter(item => isUnclassified(item.name)).reduce((sum, item) => sum + item.count, 0);
  const displayItems = meaningfulItems.slice(0, limit);
  const maxCount = Math.max(...displayItems.map(item => item.count), 1);

  return (
    <article className="surface h-full p-5">
      <h3 className="text-[15px] font-semibold tracking-[-0.01em] text-[#25302c]">{title}</h3>
      <div className="mt-5 space-y-4">
        {!displayItems.length ? <p className="text-sm text-[#69756f]">No data available.</p> : displayItems.map((item) => {
          const widthPct = Math.max((item.count / maxCount) * 100, 2);
          const rawPct = total > 0 ? (item.count / total) * 100 : 0;
          const relativePct = item.count > 0 && rawPct < 0.1 ? '<0.1' : rawPct.toFixed(1);
          return (
            <div key={`${item.name}-${item.count}`}>
              <div className="mb-1.5 flex items-baseline justify-between gap-3 text-xs">
                <span className="min-w-0 truncate font-medium text-[#43504b]" title={formatLabel(item.name)}>{formatLabel(item.name)}</span>
                <span className="shrink-0 tabular-nums text-[#69756f]">{item.count.toLocaleString()} <span className="text-[#8d9692]">· {relativePct}%</span></span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-[#edf0ee]">
                <div className="h-full rounded-full bg-gradient-to-r from-[#ff3f6c] to-[#ff8a5c] transition-[width] duration-500" style={{ width: `${widthPct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
      {missingCount > 0 && <p className="mt-5 border-t border-[var(--line)] pt-3 text-[10px] leading-4 text-[var(--faint)]">Not enough information to classify · {missingCount.toLocaleString()} records</p>}
    </article>
  );
}
