"""Transparent research rules used by the API.

These rules do not backfill missing model outputs. They identify a small set of
clusters whose representative evidence was reviewed for the current research
snapshot. Everything else remains explicitly unreviewed.
"""

from typing import Dict, Tuple


DATASET_SCOPE_CAVEAT = (
    "This result describes the analyzed public-feedback dataset from Play Store, "
    "YouTube, App Store, and Reddit. It is not a measure of all Myntra customers."
)


OPPORTUNITY_RULES: Dict[str, dict] = {
    "opp_001": {
        "title": "Shoppers need clearer size and fit information before choosing apparel.",
        "description": (
            "Investigate where missing measurements, model-size references, and "
            "height or length guidance make an online size decision difficult."
        ),
        "cluster_ids": ("cluster_011", "cluster_012"),
        "preferred_representative_source_ids": (
            "youtube_UC-4nT6iDREQp9-My-L-NibA_2021-02-23T05:44:23Z",
            "youtube_UCbINNfIq5ZMIueubX17HsYA_2026-03-01T15:27:11Z",
            "play_store_fcdb9109-cb80-4d41-b7c0-a1e6154c5dc2",
        ),
        "supporting_needs": (
            "Clear garment measurements, model-size context, and height or length guidance.",
        ),
        "representative_terms": (
            "size", "sizing", "fit", "height", "length", "inseam", "waist", "measurement", "description",
        ),
        "representative_problem_terms": (
            "confused", "difficult", "cannot", "can't", "always short", "too big", "too small",
            "could you", "please tell", "what size", "which size",
        ),
        "calculation_note": (
            "Counts only the reviewed sizing-information and height-based sizing clusters; "
            "the positive dress-quality cluster previously included in this total is excluded."
        ),
    },
    "opp_002": {
        "title": "Inconsistent pricing and product quality can weaken purchase confidence.",
        "description": (
            "Investigate unexpected price changes, fee concerns, and inconsistent product "
            "quality without treating positive quality feedback as purchase friction."
        ),
        "cluster_ids": ("cluster_023",),
        "preferred_representative_source_ids": (
            "play_store_088f7548-4d4a-4eda-82ba-36b6a5d91db6",
            "play_store_543c1b8e-395e-4db1-8fec-2e0e7897c9bb",
            "play_store_42316205-0e3a-49be-882f-76e5591aad00",
        ),
        "supporting_needs": (
            "Clear pricing and fees, with consistent product-quality expectations.",
        ),
        "representative_terms": (
            "price", "cost", "quality", "discount", "fee", "duplicate", "wrong product", "defective",
        ),
        "representative_problem_terms": (
            "costly", "high price", "low quality", "duplicate", "wrong", "defective", "doesn't", "didn't",
            "not", "nahi", "nhi", "bekar", "bekaar", "fee", "charges", "disappointed",
        ),
        "calculation_note": (
            "Counts only the reviewed inconsistent-pricing and quality cluster; the positive "
            "product-quality cluster previously included in this total is excluded."
        ),
    },
    "opp_003": {
        "title": "Delivery, refund, and support failures can reduce confidence in buying again.",
        "description": (
            "Investigate incorrect deliveries, unresolved refunds, and unresponsive support "
            "as post-purchase trust and retention risks."
        ),
        "cluster_ids": ("cluster_032", "cluster_033"),
        "preferred_representative_source_ids": (
            "play_store_4f9ee0f8-57a0-4afb-bb88-c70a121818e8",
            "play_store_150f5e0e-96ef-43d9-8a85-f4c7cab9e9a9",
            "play_store_c12b0d6e-8efd-44a4-9c33-95dd9055c120",
        ),
        "supporting_needs": (
            "Reliable delivery resolution, timely refunds, and responsive customer support.",
        ),
        "representative_terms": (
            "delivery", "refund", "return", "exchange", "support", "wrong product", "missing", "cancelled",
        ),
        "representative_problem_terms": (
            "not", "wrong", "refused", "failed", "still", "delay", "missing", "cancelled", "rejected",
            "confusing", "no response", "never",
        ),
        "calculation_note": (
            "Counts only the reviewed refund-failure and incorrect-delivery/support clusters; "
            "the mixed return-experience cluster previously included in this total is excluded."
        ),
    },
}


PATTERN_EVIDENCE_ROLES: Dict[str, str] = {
    "cluster_018": "positive",
    "cluster_017": "mixed",
    "cluster_008": "mixed",
    "cluster_002": "mixed",
    "cluster_023": "friction",
    "cluster_014": "friction",
    "cluster_012": "friction",
}


def opportunity_cluster_ids(opportunity_id: str) -> Tuple[str, ...]:
    rule = OPPORTUNITY_RULES.get(opportunity_id)
    return tuple(rule["cluster_ids"]) if rule else ()
