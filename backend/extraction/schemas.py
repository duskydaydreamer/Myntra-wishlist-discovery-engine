from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Literal

class ExtractedObservation(BaseModel):
    """
    Contract for future LLM or local-model observation extraction.
    Strictly separates topic, sentiment, and problem status.
    """
    model_config = ConfigDict(extra="forbid")
    
    topic: Optional[str] = Field(
        None, 
        description="The core subject of the feedback (e.g., 'delivery speed', 'size chart', 'fabric quality'). Must NOT imply a problem or valence."
    )
    
    sentiment: Literal["positive", "negative", "mixed", "neutral", "unknown"] = Field(
        "unknown",
        description="The emotional valence of the customer's text."
    )
    
    problem_status: Literal["problem", "praise", "mixed", "informational", "unknown"] = Field(
        "unknown",
        description="Whether the feedback indicates a friction point/issue (problem), positive reinforcement (praise), or just stating facts (informational)."
    )
    
    primary_barrier: Optional[str] = Field(
        None,
        description="The main obstacle preventing purchase or causing dissatisfaction. Only applicable if problem_status is 'problem' or 'mixed'."
    )
    
    evidence_quote: str = Field(
        ...,
        description="The exact verbatim quote from the customer. Must be perfectly traceable to the source text."
    )
    
    ai_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="The model's self-rated confidence (0.0 to 1.0) in this extraction. Note: This is an internal self-rating, not a validated accuracy metric."
    )
    
    # NOTE: The 'evidence_scope' (e.g., 'direct_experience', 'hearsay') is no longer 
    # extracted by the AI. It MUST be mapped deterministically from `raw_records.evidence_type`.

    @model_validator(mode='after')
    def validate_cross_fields(self):
        if self.problem_status in ("praise", "informational") and self.primary_barrier is not None:
            raise ValueError(f"primary_barrier cannot be set for problem_status '{self.problem_status}'")
        return self

    def validate_quote(self, source_text: str):
        if self.evidence_quote not in source_text:
            raise ValueError("evidence_quote is fabricated or altered. It does not exist verbatim in the source text.")

