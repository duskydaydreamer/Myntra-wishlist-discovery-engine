import unicodedata
import re
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Enforce consistent results for langdetect
DetectorFactory.seed = 0

class TextNormalizer:
    def normalize(self, text: str) -> str:
        if not text:
            return ""
            
        # 1. Unicode normalization (NFC)
        normalized = unicodedata.normalize('NFC', text)
        
        # 2 & 3 & 4: Collapse horizontal whitespace (spaces, tabs) to single space,
        # but preserve newlines.
        # \h is horizontal whitespace in some regex engines, but Python's re module doesn't support it directly.
        # We can split by lines, process each line, and rejoin.
        lines = normalized.splitlines()
        processed_lines = []
        for line in lines:
            # Replace multiple spaces/tabs with a single space and strip
            clean_line = re.sub(r'[ \t]+', ' ', line).strip()
            if clean_line:
                processed_lines.append(clean_line)
                
        return "\n".join(processed_lines)
        
    def detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return "unknown"
            
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"
