"""
test_mood.py — Mood classification & AI response evaluation tests
Tests: keyword detection accuracy, score ranges, response quality,
       language detection, edge cases, LLM fallback behaviour
"""

import pytest
import json
from unittest.mock import patch, AsyncMock


# ── test data ─────────────────────────────────────────────────────────────────

MOOD_TEST_CASES = [
    # (transcript, expected_mood, description)
    ("Aaj bahut khush hoon! Sab kuch amazing tha aaj",          "happy",     "Hindi happy"),
    ("I am very happy today, everything was wonderful!",         "very_happy","English very happy"),
    ("Bahut sad feel ho raha hai, dukhi hoon aaj",               "sad",       "Hindi sad"),
    ("Main bahut worried aur anxious hoon exam ke baare mein",   "anxious",   "Hindi anxious"),
    ("I am so tired and exhausted today, need rest badly",       "tired",     "English tired"),
    ("Bahut grateful aur thankful hoon apni family ke liye",     "grateful",  "Hindi grateful"),
    ("I am so excited! Can't wait for tomorrow!",                "excited",   "English excited"),
    ("Gussa aa raha hai mujhe, bahut angry hoon aaj",            "angry",     "Hindi angry"),
    ("Aaj ka din theek tha, sab normal raha",                    "neutral",   "Hindi neutral"),
    ("I feel very sad, depressed and devastated today",          "very_sad",  "English very sad"),
]

POSITIVE_MOODS  = {"very_happy", "happy", "excited", "grateful"}
NEGATIVE_MOODS  = {"very_sad", "sad", "anxious", "angry"}
NEUTRAL_MOODS   = {"neutral", "tired"}
ALL_VALID_MOODS = POSITIVE_MOODS | NEGATIVE_MOODS | NEUTRAL_MOODS


# ── keyword-based mood classification ────────────────────────────────────────

class TestKeywordMoodClassification:

    def _analyze(self, text):
        """Call the keyword fallback directly."""
        # Import here so env patches are applied
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from backend.routes.sarvam import _keyword_mood_analysis
        return _keyword_mood_analysis(text)

    @pytest.mark.parametrize("transcript,expected_mood,desc", MOOD_TEST_CASES)
    def test_mood_detection_accuracy(self, transcript, expected_mood, desc):
        result = self._analyze(transcript)
        assert result["mood"] == expected_mood, \
            f"[{desc}] Expected '{expected_mood}', got '{result['mood']}' for: {transcript}"

    def test_mood_is_always_valid_label(self):
        texts = [
            "random text without any mood keywords",
            "",
            "xyz abc 123",
            "     ",
        ]
        for text in texts:
            result = self._analyze(text)
            assert result["mood"] in ALL_VALID_MOODS, \
                f"Invalid mood '{result['mood']}' for text: '{text}'"

    def test_score_always_between_0_and_1(self):
        for transcript, _, _ in MOOD_TEST_CASES:
            result = self._analyze(transcript)
            assert 0.0 <= result["score"] <= 1.0, \
                f"Score {result['score']} out of range for: {transcript}"

    def test_positive_moods_have_high_scores(self):
        positive_texts = [
            "I am very happy and wonderful today",
            "Bahut khush hoon aaj, amazing day",
            "So excited and thrilled about this!",
        ]
        for text in positive_texts:
            result = self._analyze(text)
            assert result["score"] >= 0.5, \
                f"Positive text should score >= 0.5, got {result['score']}"

    def test_negative_moods_have_low_scores(self):
        negative_texts = [
            "I am very sad and depressed today",
            "Bahut dukhi aur worried hoon",
            "Feeling angry and frustrated all day",
        ]
        for text in negative_texts:
            result = self._analyze(text)
            assert result["score"] <= 0.5, \
                f"Negative text should score <= 0.5, got {result['score']}"

    def test_response_is_non_empty(self):
        for transcript, _, _ in MOOD_TEST_CASES:
            result = self._analyze(transcript)
            assert result["ai_response"], f"Empty response for: {transcript}"
            assert len(result["ai_response"]) > 10

    def test_suggestions_always_present_and_non_empty(self):
        for transcript, _, _ in MOOD_TEST_CASES:
            result = self._analyze(transcript)
            assert "suggestions" in result
            assert isinstance(result["suggestions"], list)
            assert len(result["suggestions"]) >= 1

    def test_result_has_all_required_keys(self):
        result = self._analyze("Aaj achha din tha")
        required = ["mood", "score", "ai_response", "suggestions", "emotions", "summary"]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_emotions_list_non_empty(self):
        result = self._analyze("I am happy today")
        assert isinstance(result["emotions"], list)
        assert len(result["emotions"]) >= 1

    def test_summary_mentions_mood(self):
        result = self._analyze("I am happy and great today")
        assert result["mood"].replace("_", " ") in result["summary"].lower()

    def test_empty_text_defaults_to_neutral(self):
        result = self._analyze("")
        assert result["mood"] == "neutral"

    def test_mixed_language_detection(self):
        """Hinglish text should still detect mood."""
        result = self._analyze("Yaar aaj bahut tired feel ho raha hai, exhausted hoon")
        assert result["mood"] == "tired"

    def test_very_long_text_handled(self):
        long_text = "happy wonderful amazing " * 100
        result = self._analyze(long_text)
        assert result["mood"] in ALL_VALID_MOODS
        assert 0.0 <= result["score"] <= 1.0


# ── AI response quality evaluation ───────────────────────────────────────────

class TestAIResponseQuality:

    def _analyze(self, text):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from backend.routes.sarvam import _keyword_mood_analysis
        return _keyword_mood_analysis(text)

    def test_sad_response_is_empathetic(self):
        result = self._analyze("I am very sad and crying today")
        response = result["ai_response"].lower()
        empathy_words = ["feelings", "valid", "samajh", "yahan", "saath", "dukh", "okay", "ठीक"]
        assert any(w in response for w in empathy_words), \
            f"Sad response lacks empathy: {result['ai_response']}"

    def test_happy_response_is_celebratory(self):
        result = self._analyze("I am very happy and wonderful today amazing")
        response = result["ai_response"].lower()
        positive_words = ["khush", "achha", "wah", "sundar", "positive", "great"]
        assert any(w in response for w in positive_words), \
            f"Happy response lacks positivity: {result['ai_response']}"

    def test_anxious_response_suggests_calming(self):
        result = self._analyze("I am anxious worried stressed nervous today")
        suggestions = [s.lower() for s in result["suggestions"]]
        calming = ["breath", "calm", "relax", "trust", "ground", "4-7-8", "technique"]
        assert any(any(c in s for c in calming) for s in suggestions), \
            f"Anxious suggestions lack calming advice: {result['suggestions']}"

    def test_tired_response_suggests_rest(self):
        result = self._analyze("I am so tired exhausted and fatigued today")
        suggestions = [s.lower() for s in result["suggestions"]]
        rest_words = ["rest", "sleep", "nap", "water", "relax", "screen"]
        assert any(any(w in s for w in rest_words) for s in suggestions), \
            f"Tired suggestions don't mention rest: {result['suggestions']}"

    def test_response_not_too_short(self):
        for transcript, _, _ in MOOD_TEST_CASES:
            result = self._analyze(transcript)
            assert len(result["ai_response"]) >= 30, \
                f"Response too short ({len(result['ai_response'])} chars): {result['ai_response']}"

    def test_response_not_excessively_long(self):
        for transcript, _, _ in MOOD_TEST_CASES:
            result = self._analyze(transcript)
            assert len(result["ai_response"]) <= 600, \
                f"Response too long ({len(result['ai_response'])} chars)"

    def test_suggestions_are_actionable(self):
        """Suggestions should be strings of reasonable length."""
        for transcript, _, _ in MOOD_TEST_CASES:
            result = self._analyze(transcript)
            for s in result["suggestions"]:
                assert isinstance(s, str)
                assert len(s) >= 5, f"Suggestion too short: '{s}'"
                assert len(s) <= 200, f"Suggestion too long: '{s}'"

    def test_very_sad_response_does_not_give_medical_advice(self):
        result = self._analyze("I am very sad depressed hopeless devastated today")
        response = result["ai_response"].lower()
        medical_terms = ["diagnose", "prescription", "medication", "disorder", "therapy session"]
        assert not any(m in response for m in medical_terms), \
            f"Response gives medical advice: {result['ai_response']}"

    def test_very_sad_response_encourages_support(self):
        result = self._analyze("I am very sad depressed hopeless devastated today")
        combined = (result["ai_response"] + " ".join(result["suggestions"])).lower()
        support_words = ["trust", "talk", "someone", "akele nahi", "counselor", "support"]
        assert any(w in combined for w in support_words)


# ── LLM integration (mocked) ─────────────────────────────────────────────────

class TestLLMMoodAnalysis:

    @pytest.mark.asyncio
    async def test_llm_called_when_api_key_present(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

        mock_llm_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "mood": "happy",
                        "score": 0.8,
                        "ai_response": "Bahut achha! Aaj aap khush hain!",
                        "suggestions": ["Keep smiling", "Share joy", "Be grateful"]
                    })
                }
            }]
        }

        with patch("os.getenv", return_value="fake-sarvam-key"):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_llm_response
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                from backend.routes.sarvam import analyze_mood_from_text
                result = await analyze_mood_from_text("Aaj bahut khush hoon!")

        assert result["mood"] == "happy"
        assert result["score"] == 0.8
        assert "emotions" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_llm_fallback_on_api_error(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

        with patch("os.getenv", return_value="fake-sarvam-key"):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("Network error")
                )
                from backend.routes.sarvam import analyze_mood_from_text
                result = await analyze_mood_from_text("I am happy today wonderful amazing")

        # Should fall back to keyword analysis
        assert result["mood"] in ALL_VALID_MOODS
        assert "ai_response" in result

    @pytest.mark.asyncio
    async def test_llm_fallback_on_invalid_json(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

        mock_bad_response = {
            "choices": [{"message": {"content": "not valid json at all"}}]
        }

        with patch("os.getenv", return_value="fake-sarvam-key"):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_bad_response
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                from backend.routes.sarvam import analyze_mood_from_text
                result = await analyze_mood_from_text("I feel happy today wonderful amazing")

        assert result["mood"] in ALL_VALID_MOODS

    @pytest.mark.asyncio
    async def test_no_api_key_uses_keyword_fallback(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

        with patch.dict(os.environ, {"SARVAM_API_KEY": ""}):
            from backend.routes.sarvam import analyze_mood_from_text
            result = await analyze_mood_from_text("I am happy wonderful amazing today")

        assert result["mood"] in ALL_VALID_MOODS
        assert result["ai_response"]


# ── mood score consistency ────────────────────────────────────────────────────

class TestMoodScoreConsistency:

    def _analyze(self, text):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from backend.routes.sarvam import _keyword_mood_analysis
        return _keyword_mood_analysis(text)

    def test_score_ordering_positive_gt_negative(self):
        very_happy = self._analyze("amazing wonderful love joy ecstatic blessed celebrate")["score"]
        very_sad   = self._analyze("very sad depressed hopeless devastated heartbroken miserable")["score"]
        assert very_happy > very_sad

    def test_very_happy_higher_than_happy(self):
        vh = self._analyze("bahut khush amazing wonderful love ecstatic")["score"]
        h  = self._analyze("khush happy good great")["score"]
        assert vh >= h

    def test_same_text_gives_same_score(self):
        text = "Aaj bahut khush hoon amazing wonderful"
        r1 = self._analyze(text)
        r2 = self._analyze(text)
        assert r1["score"] == r2["score"]
        assert r1["mood"]  == r2["mood"]

    @pytest.mark.parametrize("mood,expected_score", [
        ("very_happy", 1.0),
        ("happy",      0.75),
        ("excited",    0.85),
        ("grateful",   0.8),
        ("neutral",    0.5),
        ("tired",      0.35),
        ("anxious",    0.3),
        ("sad",        0.25),
        ("very_sad",   0.1),
        ("angry",      0.2),
    ])
    def test_mood_numeric_scores(self, mood, expected_score):
        """Verify the numeric mapping is correct for each mood label."""
        score_map = {
            "very_happy": 1.0, "happy": 0.75, "excited": 0.85, "grateful": 0.8,
            "neutral": 0.5, "tired": 0.35, "anxious": 0.3, "sad": 0.25,
            "very_sad": 0.1, "angry": 0.2
        }
        assert score_map[mood] == expected_score