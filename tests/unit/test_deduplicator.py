import pytest
from unittest.mock import patch, MagicMock
from backend.cleaning.deduplicator import Deduplicator
import numpy as np

@patch('backend.cleaning.deduplicator.SentenceTransformer')
def test_exact_duplicate(mock_st):
    mock_st_instance = MagicMock()
    mock_st.return_value = mock_st_instance
    # Return dummy embedding
    mock_st_instance.encode.return_value = [np.array([1.0, 0.0])]
    
    dedup = Deduplicator()
    
    # First time
    is_dup, dup_of = dedup.check_duplicate("id1", "This is a test review", "play_store")
    assert is_dup is False
    assert dup_of is None
    
    # Second time, exact match
    is_dup, dup_of = dedup.check_duplicate("id2", "this is a test review", "play_store")
    assert is_dup is True
    assert dup_of == "id1"

@patch('backend.cleaning.deduplicator.SentenceTransformer')
def test_near_duplicate(mock_st):
    mock_st_instance = MagicMock()
    mock_st.return_value = mock_st_instance
    
    # Return very similar embeddings for near duplicates
    mock_st_instance.encode.side_effect = [
        [np.array([1.0, 0.0, 0.0])], # id1
        [np.array([0.95, 0.05, 0.0])] # id2
    ]
    
    dedup = Deduplicator(near_duplicate_similarity=0.90)
    
    is_dup, dup_of = dedup.check_duplicate("id1", "First review", "reddit")
    assert is_dup is False
    
    is_dup, dup_of = dedup.check_duplicate("id2", "First reviews slightly different", "reddit")
    assert is_dup is True
    assert dup_of == "id1"
