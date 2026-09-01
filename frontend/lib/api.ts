const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DatasetStats {
  total_raw_records: number;
  cleaned_records: number;
  relevant_records: number;
  processed_source_records: number;
  canonical_observations: number;
  source_distribution_analyzed: Record<string, number>;
  source_distribution_raw: Record<string, number>;
  date_range: { start: string; end: string };
  analysis_run_metadata: { run_id: string; timestamp: string };
}

export interface ThemeStat {
  theme_id: string;
  canonical_name: string;
  observation_count: number;
  unique_source_count: number;
  mapping_rate_pct: number;
}

export interface ClusterStat {
  cluster_id: string;
  canonical_label: string | null;
  observation_count: number;
  unique_source_count: number;
  evidence_role: 'positive' | 'mixed' | 'friction' | 'unreviewed';
  review_status: 'directionally_reviewed' | 'unreviewed';
}

export interface RepresentativeQuote {
  quote: string;
  source: string | null;
  source_url: string | null;
}

export interface OpportunityStat {
  opportunity_id: string;
  title: string;
  original_generated_label?: string;
  description: string | null;
  metric_relevance: string;
  unique_source_count: number;
  dataset_percentage: number;
  denominator: number;
  denominator_definition: string;
  supporting_unmet_needs: string[];
  representative_quotes: RepresentativeQuote[];
  calculation_note: string;
  validation_status: 'directional_reviewed_clusters';
}

export interface DistributionItem {
  name: string;
  count: number;
}

export interface DistributionResponse {
  items: DistributionItem[];
  denominator: number;
  denominator_definition: string;
  denominator_scope: string;
  active_filters: Record<string, string>;
  classified_count?: number | null;
  unclassified_count?: number | null;
}

export interface UnmetNeed {
  unmet_need: string;
  observation_count: number | null;
  associated_barriers_json: string | null;
  associated_intents_json: string | null;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new ApiError(
      `API error: ${res.status} ${res.statusText}`,
      res.status
    );
  }
  return res.json();
}

export interface ObservationResponse {
  observation_id: string;
  source: string | null;
  evidence_quote: string;
  primary_barrier: string | null;
  wishlist_intent: string | null;
  purchase_intent: string | null;
  journey_stage: string | null;
  decision_outcome: string | null;
  uncertainty: string | null;
  ai_confidence: number | null;
  topic: string | null;
  sentiment: string | null;
  problem_status: string | null;
  evidence_scope: string | null;
  predefined_themes: string[];
  emergent_clusters: string[];
}

export interface EvidenceListResponse {
  items: ObservationResponse[];
  total: number;
  page: number;
  size: number;
}

export interface ObservationDetailResponse extends ObservationResponse {
  source_url: string | null;
  source_record_id: string;
  is_myntra_specific: boolean | null;
  product_category: string | null;
  secondary_barriers: string[] | null;
  root_cause: string | null;
  information_needed: string | null;
  workaround: string | null;
  external_platform_used: string | null;
  alternative_considered: string | null;
  occasion: string | null;
  segment_signal: string | null;
  opportunity_ids: string[];
}

export interface QueryRequest {
  query: string;
}

export interface EvidenceRecord {
  observation_id: string;
  evidence_quote: string;
  source: string | null;
  source_url: string | null;
  primary_barrier: string | null;
  workaround: string | null;
  source_record_id: string | null;
  theme_context: string | null;
  cluster_context: string | null;
}

export interface QueryResponse {
  query: string;
  query_type: string;
  retrieval_mode: string;
  applied_filters: Record<string, string[]>;
  evidence_count: number;
  unique_source_count: number;
  dataset_scope_caveat: string;
  answer: string;
  evidence: EvidenceRecord[];
  
  numerator?: number | null;
  denominator?: number | null;
  denominator_definition?: string | null;
  denominator_scope?: string | null;
}

export interface KnowledgeGraphCluster {
  cluster_id: string;
  canonical_label: string | null;
  observation_count: number;
  description: string | null;
  primary_root_cause: string | null;
  primary_unmet_need: string | null;
}

export interface KnowledgeGraphNeed {
  unmet_need: string;
  observation_count: number;
  associated_barriers: string[];
  associated_intents: string[];
  clusters: KnowledgeGraphCluster[];
}

export interface KnowledgeGraphOpportunity {
  id: string;
  title: string;
  description: string;
  relevance: { purchase: string; wishlist: string };
  unmet_needs: KnowledgeGraphNeed[];
}

export interface KnowledgeGraphResponse {
  metadata?: Record<string, string | number>;
  opportunities: KnowledgeGraphOpportunity[];
}

export const api = {
  health: () => fetchApi<{ status: string }>('/api/health'),
  
  // Meta
  filterOptions: () => fetchApi<Record<string, string[]>>('/api/meta/filter-options'),
  
  // Dashboard
  stats: () => fetchApi<DatasetStats>('/api/dashboard/stats'),
  themes: () => fetchApi<ThemeStat[]>('/api/dashboard/themes'),
  clusters: () => fetchApi<ClusterStat[]>('/api/dashboard/clusters'),
  opportunities: () => fetchApi<OpportunityStat[]>('/api/dashboard/opportunities'),
  barriers: () => fetchApi<DistributionResponse>('/api/dashboard/barriers'),
  wishlistMotivations: () => fetchApi<DistributionResponse>('/api/dashboard/wishlist-motivations'),
  purchaseIntents: () => fetchApi<DistributionResponse>('/api/dashboard/purchase-intents'),
  uncertainties: () => fetchApi<DistributionResponse>('/api/dashboard/uncertainties'),
  informationNeeds: () => fetchApi<DistributionResponse>('/api/dashboard/information-needs'),
  workarounds: () => fetchApi<DistributionResponse>('/api/dashboard/workarounds'),
  segments: () => fetchApi<DistributionResponse>('/api/dashboard/segments'),
  journeyStages: () => fetchApi<DistributionResponse>('/api/dashboard/journey-stages'),
  decisionOutcomes: () => fetchApi<DistributionResponse>('/api/dashboard/decision-outcomes'),
  
  // Unmet needs
  unmetNeeds: () => fetchApi<UnmetNeed[]>('/api/unmet-needs'),
  
  // Evidence
  evidence: (params: Record<string, string | number | boolean | null | undefined>) => {
    const urlParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value) urlParams.append(key, String(value));
    }
    return fetchApi<EvidenceListResponse>(`/api/evidence?${urlParams.toString()}`);
  },
  evidenceDetail: (id: string) => fetchApi<ObservationDetailResponse>(`/api/evidence/${id}`),
  evidenceExportUrl: (params: URLSearchParams, format: 'csv' | 'json') => {
    const exportParams = new URLSearchParams(params.toString());
    exportParams.set('format', format);
    return `${API_BASE}/api/evidence/export?${exportParams.toString()}`;
  },

  // Query
  query: async (req: QueryRequest) => {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new ApiError(`API error: ${res.status} ${res.statusText}`, res.status);
    }
    return res.json() as Promise<QueryResponse>;
  },
  
  opportunityDetail: (id: string) => fetchApi<OpportunityDetailStat>(`/api/opportunities/${id}`),
  knowledgeGraph: () => fetchApi<KnowledgeGraphResponse>('/api/knowledge-graph'),
};

export interface OpportunityDetailStat {
  opportunity_id: string;
  title: string;
  original_generated_label: string;
  description: string;
  purchase_metric_relevance: string;
  wishlist_metric_relevance: string;
  unique_source_count: number;
  dataset_percentage: number;
  denominator: number;
  denominator_definition: string;
  calculation_note: string;
  validation_status: 'directional_reviewed_clusters';
  source_distribution: Record<string, number>;
  supporting_needs: string[];
  supporting_observations: {
    observation_id: string;
    evidence_quote: string;
    source: string | null;
    source_url: string | null;
  }[];
}
