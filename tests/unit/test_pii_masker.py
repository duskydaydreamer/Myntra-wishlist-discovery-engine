import pytest
from unittest.mock import patch, MagicMock
from backend.cleaning.pii_masker import PIIMasker
from presidio_analyzer import RecognizerResult

@patch('backend.cleaning.pii_masker.AnalyzerEngine')
@patch('backend.cleaning.pii_masker.AnonymizerEngine')
def test_pii_masker_regular(mock_anon_engine, mock_analyzer_engine):
    mock_analyzer = MagicMock()
    mock_analyzer_engine.return_value = mock_analyzer
    
    mock_anon = MagicMock()
    mock_anon_result = MagicMock()
    mock_anon_result.text = "Hi [NAME], contact me at [EMAIL]"
    mock_anon.anonymize.return_value = mock_anon_result
    mock_anon_engine.return_value = mock_anon
    
    # We must mock analyze to return valid RecognizerResult objects if our code relies on them
    res_name = RecognizerResult(entity_type="PERSON", start=3, end=11, score=0.99)
    res_email = RecognizerResult(entity_type="EMAIL_ADDRESS", start=25, end=41, score=1.0)
    mock_analyzer.analyze.return_value = [res_name, res_email]
    
    masker = PIIMasker()
    result = masker.mask("Hi John Doe, contact me at john@example.com")
    
    assert result == "Hi [NAME], contact me at [EMAIL]"
    mock_analyzer.analyze.assert_called_once()
    mock_anon.anonymize.assert_called_once()

@patch('backend.cleaning.pii_masker.AnalyzerEngine')
@patch('backend.cleaning.pii_masker.AnonymizerEngine')
def test_pii_masker_hinglish_context(mock_anon_engine, mock_analyzer_engine):
    mock_analyzer = MagicMock()
    mock_analyzer_engine.return_value = mock_analyzer
    
    mock_anon = MagicMock()
    mock_anon_result = MagicMock()
    # If it filters out "bhai", it won't replace it
    mock_anon_result.text = "Myntra delivery bhai is late"
    mock_anon.anonymize.return_value = mock_anon_result
    mock_anon_engine.return_value = mock_anon
    
    # "bhai" starts at 16, ends at 20. "Myntra" starts at 0, ends at 6.
    res_bhai = RecognizerResult(entity_type="PERSON", start=16, end=20, score=0.86)
    res_myntra = RecognizerResult(entity_type="PERSON", start=0, end=6, score=0.90)
    mock_analyzer.analyze.return_value = [res_myntra, res_bhai]
    
    masker = PIIMasker()
    text = "Myntra delivery bhai is late"
    result = masker.mask(text)
    
    # It should call anonymize with empty analyzer_results because both are false positives
    args, kwargs = mock_anon.anonymize.call_args
    assert len(kwargs['analyzer_results']) == 0

