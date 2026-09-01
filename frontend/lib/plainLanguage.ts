export function plainResearchLanguage(value: string) {
  return value
    .replace(/canonical observations?/gi, match => match.endsWith('s') ? 'evidence records' : 'evidence record')
    .replace(/canonical evidence/gi, 'customer evidence')
    .replace(/canonical records?/gi, match => match.endsWith('s') ? 'evidence records' : 'evidence record')
    .replace(/canonical quotes?/gi, match => match.endsWith('s') ? 'customer quotes' : 'customer quote')
    .replace(/derived analysis/gi, 'research interpretation')
    .replace(/derived relationships?/gi, match => match.endsWith('s') ? 'research links' : 'research link')
    .replace(/derived context/gi, 'research context')
    .replace(/\bcanonical\b/gi, 'source-backed')
    .replace(/\bderived\b/gi, 'interpreted');
}

const PATTERN_GROUP_LABELS: Record<string, string> = {
  cluster_000: 'Myntra Deals Compared with Other Platforms',
  cluster_001: 'Wrong Items and Missing Product Links',
  cluster_002: 'Myntra vs Meesho Quality Comparisons',
  cluster_003: 'Footwear Quality, Comfort and Styling',
  cluster_004: 'Affordable Fashion and Product Quality',
  cluster_005: 'Size Exchanges and Sale Return Friction',
  cluster_006: 'T-Shirt Quality and Product References',
  cluster_007: 'Myntra Fashion Preference and Outfit Inspiration',
  cluster_017: 'Overall Shopping Value, Trust and Offers',
  cluster_008: 'Fabric Quality and Fit Experience',
  cluster_009: 'Jeans Fit, Comfort and Product Identification',
  cluster_010: 'Clothing Quality Versus Price',
  cluster_011: 'Sizing Guidance and Model References',
  cluster_012: 'Lack of Height-Based Sizing',
  cluster_013: 'High Overall Dress Quality',
  cluster_014: 'Missing Product Links and Item Tags',
  cluster_015: 'Dress Product Link Requests',
  cluster_016: 'Delivery Failures, Refunds and Trust Concerns',
  cluster_018: 'Positive Comments About Product Quality',
  cluster_019: 'Platform Quality and Brand Selection Comparisons',
  cluster_020: 'High and Non-Refundable Platform Fees',
  cluster_021: 'Delayed and Cancelled Deliveries',
  cluster_022: 'Platform and Product Comparisons',
  cluster_023: 'Inconsistent Pricing and Product Quality',
  cluster_024: 'Discounts and Size Availability',
  cluster_025: 'Fast Delivery, Deals and Product Quality',
  cluster_026: 'Easy Delivery, Returns and Exchanges',
  cluster_027: 'Return and Exchange Policy Experience',
  cluster_028: 'Product Authenticity and Smooth Returns',
  cluster_029: 'Return Problems and Customer Support',
  cluster_030: 'Price-to-Quality Value Perception',
  cluster_031: 'Mixed Product Quality Experiences',
  cluster_032: 'Delayed or Unprocessed Order Refunds',
  cluster_033: 'Incorrect Deliveries and Unresponsive Support',
  cluster_034: 'Prolonged Delivery Delays and Poor Updates',
  cluster_035: 'Delivery-Agent Cancellations',
  cluster_036: 'Repeated Rescheduling and Order Cancellations',
  cluster_noise: 'Mixed or Unclassified Feedback',
};

const PATTERN_LABEL_OVERRIDES: Record<string, string> = {
  cluster_018: 'Positive Comments About Product Quality',
};

export function patternGroupLabel(clusterId: string, suppliedLabel?: string | null) {
  if (PATTERN_LABEL_OVERRIDES[clusterId]) return PATTERN_LABEL_OVERRIDES[clusterId];
  const label = suppliedLabel?.trim();
  const isPlaceholder = !label || /^Emergent Pattern \d+$/i.test(label) || /^Cluster[_ ]/i.test(label);
  if (isPlaceholder) return PATTERN_GROUP_LABELS[clusterId] || 'Other Recurring Feedback Pattern';
  if (label) return plainResearchLanguage(label);
  return 'Other Recurring Feedback Pattern';
}

const OPPORTUNITY_AREA_LABELS: Record<string, string> = {
  opp_001: 'High-intent shoppers need clearer information to judge apparel fit before buying.',
  opp_002: 'Unexpected pricing changes and fees reduce shoppers’ trust in the platform.',
  opp_003: 'Delivery, return and support problems reduce confidence in future purchases.',
};

export function opportunityAreaLabel(opportunityId: string, suppliedLabel?: string | null) {
  const label = suppliedLabel?.trim();
  if (label && !/^opp[_ -]?\d+$/i.test(label)) return plainResearchLanguage(label);
  return OPPORTUNITY_AREA_LABELS[opportunityId] || 'Other opportunity area';
}

export function displayEvidenceQuote(value: string) {
  return value
    .replace(/\s*\[(?:NAME|EMAIL|PHONE|CARD|PAN|AADHAAR|URL)\]\s*/gi, ' […] ')
    .replace(/(?:\s*\[…]\s*){2,}/g, ' […] ')
    .replace(/\s+([.,!?;:])/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

export function hasPrivacyMask(value: string) {
  return /\[(?:NAME|EMAIL|PHONE|CARD|PAN|AADHAAR|URL)\]/i.test(value);
}
