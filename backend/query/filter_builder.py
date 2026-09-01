from sqlalchemy import or_
from typing import Dict, List, Any
from backend.store.database import Observation

VALID_FILTER_VALUES = {
    "source": {"play_store", "app_store", "youtube", "reddit"},
    "wishlist_intent": {
        "unknown", "genuine_purchase", "comparison_shortlist", "inspiration",
        "price_tracking", "occasion_planning", "bookmarking", "aspirational_saving",
    },
    "purchase_intent": {"high", "low", "none", "unknown"},
    "primary_barrier": {"price", "trust", "fit", "quality", "delivery", "unknown"},
    "journey_stage": {"discovery", "evaluation", "purchase", "post_purchase", "unknown"},
    "decision_outcome": {"bought", "abandoned", "delayed", "switched", "unknown"},
}

FILTER_VALUE_ALIASES = {
    "source": {"google_play": "play_store", "google_play_store": "play_store", "ios": "app_store"},
    "wishlist_intent": {
        "price_monitoring": "price_tracking", "comparison": "comparison_shortlist",
        "purchase": "genuine_purchase", "occasion": "occasion_planning",
    },
    "purchase_intent": {"medium": "low"},
    "primary_barrier": {
        "fit_and_sizing": "fit", "sizing": "fit", "size": "fit",
        "returns": "delivery", "return": "delivery", "shipping": "delivery",
    },
    "journey_stage": {"checkout": "purchase", "postpurchase": "post_purchase"},
    "decision_outcome": {"postponed": "delayed", "purchased": "bought", "cancelled": "abandoned"},
}


def normalize_implied_filters(implied_filters: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Keep model-generated filters aligned with values that actually exist in the dataset."""
    normalized_filters: Dict[str, List[str]] = {}
    for field, values in (implied_filters or {}).items():
        if field not in VALID_FILTER_VALUES or not values:
            continue

        normalized_values = []
        for value in values:
            normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
            normalized = FILTER_VALUE_ALIASES.get(field, {}).get(normalized, normalized)
            if normalized in VALID_FILTER_VALUES[field] and normalized not in normalized_values:
                normalized_values.append(normalized)

        if normalized_values:
            normalized_filters[field] = normalized_values

    return normalized_filters

def build_sqlalchemy_filters(implied_filters: Dict[str, List[str]]) -> List[Any]:
    """
    Translates a dictionary of implied filters (from the intent parser) 
    into a list of SQLAlchemy filter conditions.
    """
    filters = []
    
    implied_filters = normalize_implied_filters(implied_filters)
    if not implied_filters:
        return filters
        
    for field, values in implied_filters.items():
        if not values:
            continue
            
        if field == "source":
            filters.append(Observation.source.in_(values))
        elif field == "wishlist_intent":
            filters.append(Observation.wishlist_intent.in_(values))
        elif field == "purchase_intent":
            filters.append(Observation.purchase_intent.in_(values))
        elif field == "primary_barrier":
            filters.append(Observation.primary_barrier.in_(values))
        elif field == "journey_stage":
            filters.append(Observation.journey_stage.in_(values))
        elif field == "decision_outcome":
            filters.append(Observation.decision_outcome.in_(values))
            
    return filters
