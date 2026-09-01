from pydantic import ValidationError
from typing import Dict, Any
from backend.ingestion.schemas import RawRecordSchema

class NormalizerError(Exception):
    pass

def normalize_record(raw_dict: Dict[str, Any]) -> RawRecordSchema:
    """
    Validates and coerces a raw dictionary into the RawRecord Pydantic schema.
    Rejects records missing `raw_text` or if it's empty/whitespace.
    """
    if "raw_text" not in raw_dict or not raw_dict["raw_text"]:
        raise NormalizerError("Record missing 'raw_text'")
    
    if not str(raw_dict["raw_text"]).strip():
        raise NormalizerError("Record 'raw_text' is empty or whitespace")

    try:
        return RawRecordSchema(**raw_dict)
    except ValidationError as e:
        raise NormalizerError(f"Validation error: {e}")
