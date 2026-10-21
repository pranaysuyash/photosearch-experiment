"""Ollama VLM provider + provider auto-selection tests.

Covers the completion of OllamaVLMProvider (docs/OSS_MODEL_INTEGRATION_
EXPLORATION_2026-10-19.md P0.2/P1): real /api/generate call, model-presence
detection with family-prefix matching, actionable missing-model errors, the
analyze primitive, JSON parsing, and local-first auto resolution.
"""

import json

import pytest

from server.vlm_caption_service import (
    GeminiVLMProvider,
    OllamaVLMProvider,
    OpenAIVLMProvider,
    VLMCaptionService,
    _parse_json_object,
)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _ollama_tags_response(models):
    return _FakeResponse(200, {"models": [{"name": n} for n in models]})


@pytest.fixture
def photo(tmp_path):
    p = tmp_path / "photo.jpg"
    p.write_bytes(b"\xff\xd8\xff\xe0fakejpg")
    return str(p)


class TestOllamaAvailability:
    def test_server_down_means_unavailable(self, monkeypatch):
        def refused(url, timeout=None):
            raise ConnectionError("refused")

        monkeypatch.setattr("requests.get", refused)
        provider = OllamaVLMProvider(model="gemma4:e4b")
        assert provider.is_available() is False
        assert provider.is_model_available() is False

    def test_model_available_exact_tag(self, monkeypatch):
        monkeypatch.setattr(
            "requests.get",
            lambda url, timeout=None: _ollama_tags_response(["gemma4:e4b", "llava"]),
        )
        provider = OllamaVLMProvider(model="gemma4:e4b")
        assert provider.is_model_available() is True

    def test_model_available_family_prefix(self, monkeypatch):
        # User pulls gemma4 (implicit :latest) but config says gemma4:e4b.
        monkeypatch.setattr(
            "requests.get",
            lambda url, timeout=None: _ollama_tags_response(["gemma4:latest"]),
        )
        provider = OllamaVLMProvider(model="gemma4:e4b")
        assert provider.is_model_available() is True

    def test_model_missing_detected(self, monkeypatch):
        monkeypatch.setattr(
            "requests.get",
            lambda url, timeout=None: _ollama_tags_response(["llava"]),
        )
        provider = OllamaVLMProvider(model="gemma4:e4b")
        assert provider.is_available() is True  # server up
        assert provider.is_model_available() is False  # model not pulled


class TestOllamaGenerate:
    def test_caption_success(self, monkeypatch, photo):
        monkeypatch.setattr("requests.get", lambda url, timeout=None: _ollama_tags_response(["gemma4:e4b"]))

        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["payload"] = json
            return _FakeResponse(200, {"response": "  A dog on a beach.  ", "eval_count": 42})

        monkeypatch.setattr("requests.post", fake_post)

        provider = OllamaVLMProvider(model="gemma4:e4b")
        result = provider.generate_caption(photo)

        assert result["caption"] == "A dog on a beach."
        assert result["provider"] == "ollama"
        assert result["model"] == "gemma4:e4b"
        assert result["generated_at"]
        # Vision payload shape: prompt + base64 image, non-streaming.
        assert captured["payload"]["model"] == "gemma4:e4b"
        assert captured["payload"]["images"]
        assert captured["payload"]["stream"] is False

    def test_missing_model_error_is_actionable(self, monkeypatch, photo):
        monkeypatch.setattr("requests.get", lambda url, timeout=None: _ollama_tags_response(["llava"]))
        provider = OllamaVLMProvider(model="gemma4:e4b")
        result = provider.generate_caption(photo)
        assert result["caption"] is None
        assert "ollama pull gemma4:e4b" in result["error"]
        assert result.get("model_missing") is True

    def test_http_error_surfaces_status(self, monkeypatch, photo):
        monkeypatch.setattr("requests.get", lambda url, timeout=None: _ollama_tags_response(["gemma4:e4b"]))
        monkeypatch.setattr("requests.post", lambda url, json=None, timeout=None: _FakeResponse(500, {}, "boom"))
        provider = OllamaVLMProvider(model="gemma4:e4b")
        result = provider.generate_caption(photo)
        assert "500" in result["error"]

    def test_analyze_uses_json_format_flag(self, monkeypatch, photo):
        monkeypatch.setattr("requests.get", lambda url, timeout=None: _ollama_tags_response(["gemma4:e4b"]))
        analysis_json = json.dumps({"caption": "c", "tags": ["t"], "quality": 3})
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["payload"] = json
            return _FakeResponse(200, {"response": analysis_json})

        monkeypatch.setattr("requests.post", fake_post)

        provider = OllamaVLMProvider(model="gemma4:e4b")
        result = provider.analyze_image(photo)
        assert result["analysis"] == analysis_json
        assert captured["payload"]["format"] == "json"


class TestJsonParsing:
    def test_raw_json(self):
        assert _parse_json_object('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert _parse_json_object('```json\n{"a": 2}\n```') == {"a": 2}

    def test_prose_wrapped_json(self):
        assert _parse_json_object('Sure! {"a": 3} hope that helps') == {"a": 3}

    def test_garbage_returns_empty(self):
        assert _parse_json_object("no json here") == {}
        assert _parse_json_object("") == {}
        assert _parse_json_object('["not", "object"]') == {}


class TestProviderAutoResolution:
    def test_explicit_pin_wins(self, monkeypatch):
        assert VLMCaptionService._resolve_provider_name("openai") == "openai"

    def test_auto_prefers_local_when_model_pulled(self, monkeypatch):
        monkeypatch.setattr(OllamaVLMProvider, "is_model_available", lambda self: True)
        monkeypatch.setattr(GeminiVLMProvider, "is_available", lambda self: True)
        assert VLMCaptionService._resolve_provider_name("auto") == "ollama"

    def test_auto_falls_back_to_gemini_key(self, monkeypatch):
        monkeypatch.setattr(OllamaVLMProvider, "is_model_available", lambda self: False)
        monkeypatch.setattr(OllamaVLMProvider, "is_available", lambda self: False)
        monkeypatch.setattr(GeminiVLMProvider, "is_available", lambda self: True)
        assert VLMCaptionService._resolve_provider_name("auto") == "gemini"

    def test_auto_with_nothing_available_points_at_local_setup(self, monkeypatch):
        # Neither local nor cloud keys: prefer the local error path so the
        # user gets the actionable `ollama pull` message. Every cloud
        # provider must be neutralised — an ambient OPENAI_API_KEY would
        # otherwise decide the outcome of this test.
        monkeypatch.setattr(OllamaVLMProvider, "is_model_available", lambda self: False)
        monkeypatch.setattr(OllamaVLMProvider, "is_available", lambda self: True)
        monkeypatch.setattr(GeminiVLMProvider, "is_available", lambda self: False)
        monkeypatch.setattr(OpenAIVLMProvider, "is_available", lambda self: False)
        assert VLMCaptionService._resolve_provider_name("auto") == "ollama"

    def test_ollama_enabled_requires_model(self, monkeypatch, tmp_path):
        # A reachable server without the model must NOT count as enabled.
        monkeypatch.setattr(OllamaVLMProvider, "is_model_available", lambda self: False)
        monkeypatch.setattr(OllamaVLMProvider, "is_available", lambda self: True)
        monkeypatch.setattr(GeminiVLMProvider, "is_available", lambda self: False)
        service = VLMCaptionService(str(tmp_path / "captions.db"), provider="ollama")
        assert service.is_enabled() is False
