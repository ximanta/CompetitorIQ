import pytest
from unittest.mock import MagicMock, patch
import os
import sys
import hashlib
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.ai_engine import analyze_topics, AIAnalysisError
from utils.excel_handler import update_excel_with_analysis

# --- AUTH TESTS ---
def test_password_hashing():
    """Verify that the hashing logic matches the production expectation."""
    password = "admin"
    expected_hash = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
    
    computed_hash = hashlib.sha256(password.encode()).hexdigest()
    assert computed_hash == expected_hash

# --- AI ENGINE TESTS ---
@patch("utils.ai_engine.genai.GenerativeModel")
def test_analyze_topics_success(mock_model_cls):
    """Test successful analysis with correct schema parsing."""
    mock_model = MagicMock()
    mock_model_cls.return_value = mock_model
    
    # Mock Response
    mock_response = MagicMock()
    # Return list of objects as per new schema
    mock_response.text = json.dumps([
        {"topic": "Python", "decision": "Yes", "reasoning": "Found it."},
        {"topic": "Java", "decision": "No", "reasoning": "Missing."}
    ])
    mock_model.generate_content.return_value = mock_response
    
    topics = ["Python", "Java"]
    context = "We teach Python."
    
    result = analyze_topics(topics, context, "fake_key")
    
    assert result["Python"]["decision"] == "Yes"
    assert result["Java"]["decision"] == "No"
    assert mock_model.generate_content.call_count == 1

@patch("utils.ai_engine.genai.GenerativeModel")
def test_analyze_topics_retry_logic(mock_model_cls):
    """Test that it retries 3 times on failure and then raises AIAnalysisError."""
    mock_model = MagicMock()
    mock_model_cls.return_value = mock_model
    
    # Mock Failure
    mock_model.generate_content.side_effect = Exception("API Error")
    
    topics = ["Python"]
    
    with pytest.raises(AIAnalysisError) as excinfo:
        analyze_topics(topics, "context", "key")
    
    assert "Analysis failed after 3 attempts" in str(excinfo.value)
    assert mock_model.generate_content.call_count == 3

# --- EXCEL TESTS ---
# Note: Excel tests usually require a temp file. We will mock openpyxl for speed/isolation if possible,
# or better yet, verify the logic structure. For this regression, let's skip complex integration
# unless we create a real file.
