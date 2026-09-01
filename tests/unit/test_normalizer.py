import pytest
from backend.cleaning.normalizer import TextNormalizer

def test_normalize():
    norm = TextNormalizer()
    
    # 1. Whitespace collapsing
    assert norm.normalize("This   is  a\t\ttest") == "This is a test"
    
    # 2. Preserve newlines
    assert norm.normalize("Line 1\n\nLine   2") == "Line 1\nLine 2"
    
    # 3. Unicode normalization (NFC)
    # e.g., decomposed vs composed e with acute
    assert norm.normalize("e\u0301") == "\u00e9"
    
def test_detect_language():
    norm = TextNormalizer()
    
    assert norm.detect_language("This is an English sentence.") == "en"
    
    # French
    assert norm.detect_language("C'est une phrase en français.") == "fr"
    
    # Empty
    assert norm.detect_language("") == "unknown"
