export default function SourceDistribution({ analyzed, raw }: { analyzed: Record<string, number>; raw: Record<string, number> }) {
  if (!analyzed) return null;
  const sources = Object.keys(analyzed);
  const total = Object.values(analyzed).reduce((sum, count) => sum + count, 0);
  const fills = ['#ff3f6c', '#ff7a65', '#bc8cff', '#4bd0a0'];
  return (
    <section className="surface mb-6 p-5 sm:p-6" aria-labelledby="source-heading">
      <div className="section-header mb-5">
        <div>
          <h3 id="source-heading" className="text-[15px] font-semibold text-[#25302c]">Source distribution</h3>
          <p className="mt-1 text-xs text-[#69756f]">Channel mix within the analyzed evidence</p>
        </div>
        <span className="text-xs tabular-nums text-[#69756f]">{total.toLocaleString()} observations</span>
      </div>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-[#edf0ee]" aria-hidden="true">
        {sources.map((source, index) => <span key={source} style={{ width: `${total ? analyzed[source] / total * 100 : 0}%`, background: fills[index % fills.length] }} />)}
      </div>
      <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 lg:grid-cols-4">
        {sources.map((source, index) => {
          const pct = total ? analyzed[source] / total * 100 : 0;
          return (
            <div key={source} className="flex items-start gap-2.5">
              <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: fills[index % fills.length] }} />
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold capitalize text-[#34423c]">{source.replaceAll('_', ' ')}</p>
                <p className="mt-0.5 text-[11px] tabular-nums text-[#69756f]">{analyzed[source].toLocaleString()} · {pct.toFixed(1)}%</p>
                {raw?.[source] && <p className="mt-0.5 text-[10px] text-[#8d9692]">{raw[source].toLocaleString()} collected</p>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
