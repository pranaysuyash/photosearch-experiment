"""Tests for src/jev_intent_advisor.py — offline only, injected transport.

No test here may touch the network. The advisor is exercised through a fake
transport so behavior (escalation, gating, merge, fallback) is deterministic.
"""

import uuid

import pytest

from src.intent_recognition import IntentDetector
from src.jev_intent_advisor import JevIntentAdvisor


def make_advisor(detector, *, enabled=True, api_key=None, transport=lambda p: {}, **kwargs):
    # Per-run key: no credential-like literal in source (matches wave-3 convention).
    return JevIntentAdvisor(
        detector, enabled=enabled, api_key=api_key or uuid.uuid4().hex, transport=transport, **kwargs
    )


def jev_response(choice="activity", confidence=0.9, multi=0.8, privacy=0.1):
    return {
        "model": "jev-1.13.0",
        "answers": {
            "primary_intent": {"choice": choice, "confidence": confidence, "probabilities": {}},
            "needs_multiple_modes": {"noul": multi},
            "privacy_gate_review": {"noul": privacy},
        },
        "usage": {"input_tokens": 100, "output_tokens": 10},
    }


@pytest.fixture(scope="module")
def detector() -> IntentDetector:
    return IntentDetector()


class TestDisabledPassthrough:
    def test_disabled_never_calls_transport(self, detector):
        calls = []

        def transport(payload):
            calls.append(payload)
            return jev_response()

        advisor = make_advisor(detector, enabled=False, transport=transport)
        result = advisor.detect_intent("landscapes of Iceland")  # low confidence tail
        assert result["primary_intent"] == result["primary_intent"]  # shape intact
        assert calls == []
        assert result["advisor"]["source"] == "keyword"
        assert result["advisor"]["enabled"] is False

    def test_no_key_means_disabled(self, detector):
        advisor = JevIntentAdvisor(detector, enabled=True, api_key=None, transport=lambda p: jev_response())
        result = advisor.detect_intent("zzz qwerty florb")
        assert result["advisor"]["enabled"] is False
        assert result["advisor"]["source"] == "keyword"

    def test_high_confidence_keyword_result_not_escalated(self, detector):
        calls = []

        def transport(payload):
            calls.append(payload)
            return jev_response()

        advisor = make_advisor(detector, transport=transport)
        # Single keyword hit, no runner-up: clear people query, no call.
        advisor.detect_intent("photos of grandma at home")
        assert calls == []


class TestEscalation:
    def test_low_confidence_escalates_and_merges(self, detector):
        # "landscapes of Iceland" carries no keyword signal (generic, confidence 0),
        # so it always escalates; Jev resolves it to location.
        advisor = make_advisor(detector, transport=lambda p: jev_response(choice="location", confidence=0.9))
        result = advisor.detect_intent("landscapes of Iceland")
        assert result["advisor"]["source"] == "jev"
        assert result["primary_intent"] == "location"
        assert result["advisor"]["privacy_gate"] == pytest.approx(0.1)
        assert result["advisor"]["needs_multiple_modes"] == pytest.approx(0.8)
        # Badges and suggestions re-derived for the new primary.
        assert result["badges"][0]["intent"] == "location"
        assert "location" not in result["secondary_intents"]

    def test_invalid_choice_is_rejected_and_falls_back(self, detector):
        advisor = make_advisor(detector, transport=lambda p: jev_response(choice="teleportation"))
        result = advisor.detect_intent("zzz qwerty florb")
        assert result["primary_intent"] == "generic"  # keyword result kept
        assert result["advisor"]["source"] == "keyword_fallback"

    def test_choice_below_gate_falls_back(self, detector):
        advisor = make_advisor(
            detector,
            transport=lambda p: jev_response(choice="location", confidence=0.3),
            choice_gate=0.5,
        )
        result = advisor.detect_intent("landscapes of Iceland")
        assert result["primary_intent"] == "generic"  # keyword routing preserved
        assert result["advisor"]["source"] == "keyword_fallback"
        assert result["advisor"]["jev_choice"] == "location"  # still recorded for review


class TestFailureModes:
    def test_transport_error_falls_back(self, detector):
        def transport(payload):
            raise RuntimeError("provider down")

        advisor = make_advisor(detector, transport=transport)
        result = advisor.detect_intent("zzz qwerty florb")
        assert result["primary_intent"] == "generic"
        assert result["advisor"]["source"] == "keyword_fallback"
        assert "provider down" in result["advisor"]["error"]

    def test_malformed_response_falls_back(self, detector):
        advisor = make_advisor(detector, transport=lambda p: {"unexpected": True})
        result = advisor.detect_intent("zzz qwerty florb")
        assert result["advisor"]["source"] == "keyword_fallback"


class TestInterfaceParity:
    def test_badges_and_suggestions_delegate(self, detector):
        advisor = make_advisor(detector, enabled=False)
        assert advisor.get_search_badges("canon beach") == detector.get_search_badges("canon beach")
        assert advisor.get_search_suggestions("canon beach") == detector.get_search_suggestions("canon beach")

    def test_get_all_intents_passthrough(self, detector):
        advisor = make_advisor(detector, enabled=False)
        assert advisor.get_all_intents() == detector.get_all_intents()


class TestEscalationTriggers:
    """Regression coverage for the calibration-gap fix: confidence < threshold
    is a weak trigger because router confidence is score share, not
    calibration — contested queries (small top-two margin) escalate too."""

    def test_contested_high_confidence_escalates(self, detector):
        # "gopro photos from december 2023": date 3.0 beats camera 1.25,
        # confidence 0.706 — the confidently-wrong shape the old trigger missed.
        advisor = make_advisor(detector, transport=lambda p: jev_response(choice="camera", confidence=0.9))
        result = advisor.detect_intent("gopro photos from december 2023")
        assert result["advisor"]["escalation"] == "contested_margin"
        assert result["advisor"]["source"] == "jev"
        assert result["primary_intent"] == "camera"

    def test_clear_winner_does_not_escalate(self, detector):
        # Single keyword hit, no runner-up: confidence 1.0, margin None.
        advisor = make_advisor(detector, transport=lambda p: jev_response())
        result = advisor.detect_intent("photos of grandma at home")
        assert result["advisor"]["escalation"] == "none"
        assert result["advisor"]["source"] == "keyword"

    def test_tie_escalates(self, detector):
        advisor = make_advisor(detector, transport=lambda p: jev_response(choice="people", confidence=0.9))
        result = advisor.detect_intent("grandma smiling at the camera")  # 1.25/1.25 tie
        assert result["advisor"]["escalation"] == "contested_margin"

    def test_margin_threshold_configurable(self, detector):
        # "gopro photos from december 2023" has a 1.75 top-two margin; a
        # margin threshold below that declassifies it as contested.
        advisor = make_advisor(detector, transport=lambda p: jev_response(), margin_threshold=1.0)
        result = advisor.detect_intent("gopro photos from december 2023")
        assert result["advisor"]["escalation"] == "none"

    def test_disabled_records_trigger_without_calling(self, detector):
        calls = []

        def transport(payload):
            calls.append(payload)
            return jev_response()

        advisor = make_advisor(detector, enabled=False, transport=transport)
        result = advisor.detect_intent("gopro photos from december 2023")
        assert calls == []
        assert result["advisor"]["source"] == "keyword"
        assert result["advisor"]["escalation"] == "contested_margin"  # recorded, not acted on


class TestDetectorScoresField:
    def test_scores_present_and_consistent(self, detector):
        result = detector.detect_intent("Canon camera beach vacation")
        scores = result["scores"]
        assert scores["camera"] == max(scores.values())
        assert scores["generic"] == 0.0
        assert result["primary_intent"] == "camera"

    def test_no_signal_scores_all_zero(self, detector):
        result = detector.detect_intent("zzz qwerty florb")
        assert all(v == 0.0 for v in result["scores"].values())


class TestFromEnv:
    def test_env_off_by_default(self, detector, monkeypatch):
        monkeypatch.delenv("JEV_INTENT_ADVISOR_ENABLED", raising=False)
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        advisor = JevIntentAdvisor.from_env(detector)
        assert advisor.enabled is False

    def test_env_enabled_requires_key(self, detector, monkeypatch):
        monkeypatch.setenv("JEV_INTENT_ADVISOR_ENABLED", "1")
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        advisor = JevIntentAdvisor.from_env(detector)
        assert advisor.enabled is False

    def test_env_enabled_with_key(self, detector, monkeypatch):
        monkeypatch.setenv("JEV_INTENT_ADVISOR_ENABLED", "1")
        monkeypatch.setenv("TYPESAFE_API_KEY", "k")
        monkeypatch.setenv("JEV_MODEL", "jev-9.9.9")
        advisor = JevIntentAdvisor.from_env(detector)
        assert advisor.enabled is True
        assert advisor.model == "jev-9.9.9"

    def test_invalid_threshold_env_keeps_default(self, detector, monkeypatch):
        monkeypatch.setenv("JEV_INTENT_ADVISOR_ENABLED", "1")
        monkeypatch.setenv("TYPESAFE_API_KEY", "k")
        monkeypatch.setenv("JEV_INTENT_TAIL_THRESHOLD", "not-a-number")
        advisor = JevIntentAdvisor.from_env(detector)
        assert advisor.tail_threshold == 0.5
