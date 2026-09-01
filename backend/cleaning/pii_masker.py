from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from typing import List

class PIIMasker:
    def __init__(self, entities: List[str] = None):
        # Initialize Presidio Analyzer and Anonymizer
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Map our config entities to Presidio entities
        self.default_entities = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IN_PAN", "IN_AADHAAR"]
        self.entities = entities if entities else self.default_entities
        
        # Note on LOCATION: To avoid removing contextual mentions like "Bangalore", 
        # we might omit LOCATION or implement a custom recognizer. We'll stick to 
        # explicit PII for now.

    def mask(self, text: str) -> str:
        if not text:
            return text
            
        results = self.analyzer.analyze(text=text, entities=self.entities, language='en')

        # PERSON recognition is especially noisy for brand names and Hinglish
        # transliterations. Keep only high-confidence person matches so ordinary
        # product or conversational words are less likely to be removed.
        filtered_results = []
        hinglish_false_positives = {
            "myntra", "flipkart", "amazon", "meesho", "ajio", 
            "kurta", "saree", "lehenga", "dupatta", "jeans", "shirt",
            "bhai", "yaar", "sir", "madam", "bro", "dude",
            "delivery", "app", "order", "return", "refund", "size", "fit", 
            "quality", "price", "money", "time", "day", "month", "year"
        }
        for result in results:
            if result.entity_type == "PERSON":
                word = text[result.start:result.end].lower().strip()
                # Skip masking if the recognized word is a known product/context term
                if word in hinglish_false_positives:
                    continue
                # For very short words, require high confidence
                if len(word) <= 4 and result.score < 0.95:
                    continue
                # General threshold for PERSON
                if result.score < 0.85:
                    continue
            filtered_results.append(result)
            
        results = filtered_results
        
        # We can map entity types to specific placeholders
        operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[NAME]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CARD]"}),
            "IN_PAN": OperatorConfig("replace", {"new_value": "[PAN]"}),
            "IN_AADHAAR": OperatorConfig("replace", {"new_value": "[AADHAAR]"}),
            "URL": OperatorConfig("replace", {"new_value": "[URL]"})
        }
        
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )
        
        return anonymized_result.text
