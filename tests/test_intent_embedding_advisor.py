"""EmbeddingIntentAdvisor tests (local zero-shot intent tier, P3.2).

Proves: escalation only on weak keyword verdicts, override above the
similarity gate, keyword fallback below the gate, exception safety, and the
keyword-passthrough interface shape.
"""

from src.intent_embedding_advisor import EmbeddingIntentAdvisor

# Each fake intent's description carries one unique keyword; the fake encoder
# maps those keywords to orthogonal axes so similarity is fully controlled.
INTENTS = {
    "camera": {"description": "queries about camera device brand", "keywords": []},
    "location": {"description": "queries about a place or gps spot", "keywords": []},
    "date": {"description": "queries about when a photo was taken", "keywords": []},
    "generic": {"description": "anything else at all misc", "keywords": []},
}
AXIS_WORDS = ["brand", "spot", "when", "misc"]
DIM = len(AXIS_WORDS)


def fake_encode(texts):
    vectors = []
    for text in texts:
        vec = [0.0] * DIM
        for i, word in enumerate(AXIS_WORDS):
            if word in text:
                vec[i] = 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        vectors.append([v / norm for v in vec])
    return vectors


class FakeKeywordDetector:
    """Deterministic stand-in for IntentDetector."""

    def __init__(self, primary="generic", confidence=0.0, scores=None):
        self.intent_definitions = INTENTS
        self._primary = primary
        self._confidence = confidence
        self._scores = scores or {}

    def detect_intent(self, query):
        return {
            "primary_intent": self._primary,
            "secondary_intents": [],
            "confidence": self._confidence,
            "scores": dict(self._scores),
            "suggestions": [],
            "badges": [],
        }

    def get_all_intents(self):
        return INTENTS


def make_advisor(detector, **kwargs):
    defaults = dict(enabled=True, encoder=fake_encode, similarity_gate=0.35)
    defaults.update(kwargs)
    return EmbeddingIntentAdvisor(detector, **defaults)


class TestEscalationTriggers:
    def test_confident_keyword_verdict_not_escalated(self):
        detector = FakeKeywordDetector(primary="camera", confidence=0.9, scores={"camera": 3.0})
        result = make_advisor(detector).detect_intent("canon photos")
        assert result["primary_intent"] == "camera"
        assert result["embedding_advisor"]["source"] == "keyword"
        assert result["embedding_advisor"]["escalation"] == "none"

    def test_low_confidence_escalates(self):
        detector = FakeKeywordDetector(primary="generic", confidence=0.2, scores={"generic": 0.5})
        result = make_advisor(detector).detect_intent("seaside brand")
        assert result["embedding_advisor"]["escalation"] == "low_confidence"

    def test_contested_margin_escalates(self):
        detector = FakeKeywordDetector(primary="camera", confidence=0.6, scores={"camera": 2.0, "date": 1.5})
        result = make_advisor(detector).detect_intent("anything")
        assert result["embedding_advisor"]["escalation"] == "contested_margin"


class TestEmbeddingVerdict:
    def test_override_above_gate(self):
        # Keyword says generic with low confidence; embedding clearly says camera.
        detector = FakeKeywordDetector(primary="generic", confidence=0.2, scores={"generic": 0.4})
        result = make_advisor(detector).detect_intent("which brand took this")
        assert result["primary_intent"] == "camera"
        assert result["embedding_advisor"]["source"] == "embedding"
        assert result["embedding_advisor"]["embedding_choice"] == "camera"
        assert 0.0 <= result["confidence"] <= 1.0

    def test_below_gate_falls_back_to_keyword(self):
        detector = FakeKeywordDetector(primary="date", confidence=0.2, scores={"date": 0.4})
        # Query shares no axis word → similarity 0 → below gate.
        result = make_advisor(detector).detect_intent("xyzzy")
        assert result["primary_intent"] == "date"
        assert result["embedding_advisor"]["source"] == "keyword_fallback"

    def test_scores_payload_reshaped_not_dropped(self):
        detector = FakeKeywordDetector(primary="generic", confidence=0.2, scores={"generic": 0.4})
        result = make_advisor(detector).detect_intent("which brand took this")
        assert "scores" in result
        assert set(result["scores"]) == set(INTENTS)


class TestSafetyAndInterface:
    def test_encoder_failure_never_breaks_search(self):
        def exploding_encoder(texts):
            raise RuntimeError("model exploded")

        detector = FakeKeywordDetector(primary="date", confidence=0.1, scores={"date": 0.3})
        advisor = EmbeddingIntentAdvisor(detector, enabled=True, encoder=exploding_encoder)
        result = advisor.detect_intent("anything")
        assert result["primary_intent"] == "date"
        assert result["embedding_advisor"]["source"] == "keyword_fallback"
        assert "RuntimeError" in result["embedding_advisor"]["error"]

    def test_disabled_advisor_is_passthrough(self):
        detector = FakeKeywordDetector(primary="generic", confidence=0.1)
        result = make_advisor(detector, enabled=False).detect_intent("seaside brand")
        assert result["primary_intent"] == "generic"
        assert result["embedding_advisor"]["source"] == "keyword"

    def test_intent_definitions_delegate_for_outer_wrappers(self):
        advisor = make_advisor(FakeKeywordDetector())
        assert advisor.intent_definitions is INTENTS

    def test_passthrough_helpers(self):
        advisor = make_advisor(FakeKeywordDetector())
        assert advisor.get_all_intents() == INTENTS
        assert advisor.get_search_suggestions("q") == []
        assert advisor.get_search_badges("q") == []

    def test_empty_query_never_escalates(self):
        detector = FakeKeywordDetector(primary="generic", confidence=0.0)
        result = make_advisor(detector).detect_intent("   ")
        assert result["embedding_advisor"]["source"] == "keyword"
