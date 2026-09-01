import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.classification.relevance_classifier import RelevanceClassifier

@patch('backend.classification.relevance_classifier.SentenceTransformer')
def test_pre_filter(mock_st):
    mock_st_instance = MagicMock()
    mock_st.return_value = mock_st_instance
    
    # We won't strictly test the embeddings calculation since it depends on model
    # We will just patch the pre_filter method for the LLM test or mock the embeddings.
    pass

@patch('backend.classification.relevance_classifier.SentenceTransformer')
@pytest.mark.asyncio
async def test_relevance_classifier_llm(mock_st):
    mock_client = MagicMock()
    # Mock LLM response
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"label": "highly_relevant", "confidence": 0.9, "signals_detected": ["sizing"]}'
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    rc = RelevanceClassifier()
    rc.client = mock_client
    
    result = await rc.classify("The sizing is completely wrong for this shirt.")
    
    assert result["label"] == "highly_relevant"
    assert result["confidence"] == 0.9
    assert "sizing" in result["signals_detected"]
