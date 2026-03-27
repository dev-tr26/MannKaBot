"""
test_mood_llm_integration.py — Test LLM mood analysis (mocked)
No real API call, no DB
"""

import pytest
from unittest.mock import patch, AsyncMock
import json

@pytest.mark.asyncio
async def test_llm_called_and_returns_expected_structure():
    mock_response = {
        "choices":[{"message":{"content":json.dumps({
            "mood":"happy","score":0.8,"ai_response":"Bahut achha!","suggestions":["Keep smiling"]})}}]
    }
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp_obj = AsyncMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp_obj)

        from backend.routes.sarvam import analyze_mood_from_text
        result = await analyze_mood_from_text("Aaj khush hoon!")
        assert result["mood"] == "happy"
        assert result["score"] == 0.8
        assert "ai_response" in result
        assert "suggestions" in result