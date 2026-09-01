import { ThemeStat, ClusterStat } from "../lib/api";
import { patternGroupLabel, plainResearchLanguage } from "../lib/plainLanguage";

const PATTERN_SECTION_LABELS: Record<string, string> = {
  cluster_018: 'Positive comments about product quality and satisfaction',
  cluster_017: 'Shopping value, offers and trust',
  cluster_023: 'Inconsistent pricing and product quality',
  cluster_008: 'Fabric quality and fit uncertainty',
  cluster_002: 'Cross-platform quality comparisons',
  cluster_014: 'Missing product links and item tags',
  cluster_012: 'Lack of height-based sizing',
};

// Mirrors the small, manually reviewed role map in backend/research_rules.py.
// This keeps the dashboard usable while an older API process is still running
// and does not classify any unreviewed cluster.
const REVIEWED_PATTERN_ROLES: Record<string, 'positive' | 'mixed' | 'friction'> = {
  cluster_018: 'positive',
  cluster_017: 'mixed',
  cluster_008: 'mixed',
  cluster_002: 'mixed',
  cluster_023: 'friction',
  cluster_014: 'friction',
  cluster_012: 'friction',
};

function evidenceRole(cluster: ClusterStat) {
  return cluster.evidence_role && cluster.evidence_role !== 'unreviewed'
    ? cluster.evidence_role
    : REVIEWED_PATTERN_ROLES[cluster.cluster_id] || 'unreviewed';
}

function PatternRows({ clusters, tone }: { clusters: ClusterStat[]; tone: 'positive' | 'mixed' | 'friction' }) {
  const maxCount = Math.max(...clusters.map(cluster => cluster.unique_source_count), 1);
  const barColor = tone === 'positive' ? '#4bd0a0' : tone === 'mixed' ? '#bc8cff' : '#dc7884';
  return (
    <div className="mt-3 divide-y divide-[var(--line)]">
      {clusters.map(cluster => {
        const label = PATTERN_SECTION_LABELS[cluster.cluster_id] || patternGroupLabel(cluster.cluster_id, cluster.canonical_label);
        return (
          <div key={cluster.cluster_id} className="py-3.5">
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4">
              <span className="min-w-0 text-[13px] font-medium leading-5 text-[var(--ink-soft)]">{label}</span>
              <span className="whitespace-nowrap pt-0.5 text-right text-[11px] tabular-nums text-[var(--muted)]"><strong className="text-[13px] font-semibold text-[var(--ink)]">{cluster.unique_source_count.toLocaleString()}</strong> records</span>
            </div>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-[var(--line)]" aria-hidden="true">
              <div className="h-full rounded-full" style={{ width: `${Math.max(cluster.unique_source_count / maxCount * 100, 4)}%`, backgroundColor: barColor }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ThemeGrid({ themes }: { themes: ThemeStat[] }) {
  if (!themes?.length) return null;
  const displayThemes = themes.slice(0, 6);
  const maxCount = Math.max(...displayThemes.map(theme => theme.observation_count), 1);
  return (
    <section className="h-full" aria-labelledby="theme-heading">
      <div className="mb-3">
        <h3 id="theme-heading" className="text-[15px] font-semibold text-[var(--ink)]">Topics customers mention</h3>
        <p className="mt-1 text-xs leading-5 text-[var(--muted)]">Common shopping topics across feedback; one comment may mention several.</p>
      </div>
      <div className="surface divide-y divide-[#e7ebe8] overflow-hidden">
        {displayThemes.map(theme => (
          <div key={theme.theme_id} className="p-4">
            <div className="flex items-center justify-between gap-4">
              <span className="text-[13px] font-medium text-[var(--ink-soft)]">{plainResearchLanguage(theme.canonical_name)}</span>
              <span className="shrink-0 text-xs tabular-nums text-[var(--muted)]">{theme.observation_count.toLocaleString()}</span>
            </div>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-[var(--line)]"><div className="h-full rounded-full bg-gradient-to-r from-[#ff3f6c] to-[#bc8cff]" style={{ width: `${Math.max(theme.observation_count / maxCount * 100, 2)}%` }} /></div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ClusterGrid({ clusters }: { clusters: ClusterStat[] }) {
  if (!clusters?.length) return null;
  const valuePatterns = clusters.filter(cluster => evidenceRole(cluster) === 'positive');
  const mixedPatterns = clusters.filter(cluster => evidenceRole(cluster) === 'mixed');
  const frictionPatterns = clusters.filter(cluster => evidenceRole(cluster) === 'friction');

  if (!valuePatterns.length && !mixedPatterns.length && !frictionPatterns.length) {
    return (
      <section className="h-full" aria-labelledby="cluster-heading">
        <div className="mb-3">
          <h3 id="cluster-heading" className="text-[15px] font-semibold text-[var(--ink)]">Patterns found in customer feedback</h3>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">Reviewed patterns are separated into praise, mixed experiences, and purchase friction.</p>
        </div>
        <div className="surface px-5 py-8">
          <h4 className="text-sm font-semibold text-[var(--ink)]">Reviewed patterns are temporarily unavailable</h4>
          <p className="mt-2 text-xs leading-5 text-[var(--muted)]">Refresh the dashboard after the analysis service reconnects.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="h-full" aria-labelledby="cluster-heading">
      <div className="mb-3">
        <h3 id="cluster-heading" className="text-[15px] font-semibold text-[var(--ink)]">Patterns found in customer feedback</h3>
        <p className="mt-1 text-xs leading-5 text-[var(--muted)]">Reviewed patterns are separated into praise, mixed experiences, and purchase friction.</p>
      </div>
      <div className="surface overflow-hidden">
        <section className="px-5 py-5">
          <p className="text-[9px] font-bold uppercase tracking-[0.13em] text-[#4f8b76]">Positive signals</p>
          <div className="mt-1 flex items-baseline justify-between gap-4">
            <h4 className="text-[15px] font-semibold leading-6 text-[var(--ink)]">What customers value</h4>
            <span className="shrink-0 text-[10px] text-[var(--muted)]">{valuePatterns.length} {valuePatterns.length === 1 ? 'pattern' : 'patterns'}</span>
          </div>
          <PatternRows clusters={valuePatterns} tone="positive" />
        </section>
        <section className="border-t border-[var(--line)] bg-[var(--surface-muted)] px-5 py-5">
          <p className="text-[9px] font-bold uppercase tracking-[0.13em] text-[var(--derived)]">Mixed customer feedback</p>
          <div className="mt-1 flex items-baseline justify-between gap-4">
            <h4 className="text-[15px] font-semibold leading-6 text-[var(--ink)]">Both positive and negative experiences</h4>
            <span className="shrink-0 text-[10px] text-[var(--muted)]">{mixedPatterns.length} {mixedPatterns.length === 1 ? 'pattern' : 'patterns'}</span>
          </div>
          <PatternRows clusters={mixedPatterns} tone="mixed" />
        </section>
        <section className="border-t border-[var(--line)] bg-[var(--canvas-subtle)] px-5 py-5">
          <p className="text-[9px] font-bold uppercase tracking-[0.13em] text-[var(--danger)]">Purchase friction</p>
          <div className="mt-1 flex items-baseline justify-between gap-4">
            <h4 className="text-[15px] font-semibold leading-6 text-[var(--ink)]">Where customers struggle</h4>
            <span className="shrink-0 text-[10px] text-[var(--muted)]">{frictionPatterns.length} {frictionPatterns.length === 1 ? 'pattern' : 'patterns'}</span>
          </div>
          <PatternRows clusters={frictionPatterns} tone="friction" />
        </section>
        <div className="border-t border-[var(--line)] bg-[var(--canvas-subtle)] px-5 py-3">
          <p className="text-[10px] leading-4 text-[var(--muted)]">Counts show matching feedback records—not unique customers or satisfaction scores. Only the patterns shown here received a directional evidence review.</p>
        </div>
      </div>
    </section>
  );
}
