"""Audio transcription service + router tests (P3.1).

The backend is faked; the sqlite storage layer is exercised for real through
the service's public API (no SQL literals in this file). Proves: backend
gating, video-extension gating, cache behavior, store/get/search roundtrip,
batch limits, and the /api/transcripts routes.
"""

import pytest
from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


class FakeBackend:
    name = "fake_whisper"

    def __init__(self):
        self.calls = []

    def is_available(self):
        return True

    def transcribe(self, wav_path, language):
        self.calls.append(wav_path)
        return {
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "hello world from the test bench"},
                {"start": 1.5, "end": 3.0, "text": "the quick brown fox"},
            ],
            "language": "en",
        }


@pytest.fixture
def service(tmp_path, monkeypatch):
    """AudioTranscriptionService on an isolated DB with a fake backend."""
    import server.audio_transcription_service as ats

    svc = ats.AudioTranscriptionService(db_path=str(tmp_path / "t.db"))
    monkeypatch.setattr(svc, "_backend", FakeBackend())
    # Never touch the real backend builder in these tests.
    monkeypatch.setattr(ats.AudioTranscriptionService, "_build_backend", lambda self: svc._backend)
    # Skip real ffmpeg audio extraction (I/O boundary); the fake backend
    # receives a dummy wav path.
    monkeypatch.setattr(ats, "_extract_audio_wav", lambda video, out: None)
    yield svc


@pytest.fixture
def fake_video(tmp_path):
    p = tmp_path / "clip.mp4"
    p.write_bytes(b"\x00\x01\x02fakevideo")
    return str(p)


class TestService:
    def test_no_backend_reports_install_hint(self, tmp_path, monkeypatch):
        import server.audio_transcription_service as ats

        svc = ats.AudioTranscriptionService(db_path=str(tmp_path / "x.db"))
        monkeypatch.setattr(svc, "_backend", None)
        monkeypatch.setattr(ats.AudioTranscriptionService, "_build_backend", lambda self: None)
        result = svc.transcribe("/whatever.mp4")
        assert "faster-whisper" in result["error"]

    def test_rejects_non_video_paths(self, service, tmp_path):
        existing = tmp_path / "notes.txt"
        existing.write_text("not a video")
        result = service.transcribe(str(existing))
        assert "Not a supported video" in result["error"]

    def test_missing_file_404_shape(self, service):
        result = service.transcribe("/nope.mp4")
        assert "Video not found" in result["error"]

    def test_transcribe_get_roundtrip(self, service, fake_video):
        result = service.transcribe(fake_video)
        assert result["error"] is None if "error" in result else True
        assert result["segment_count"] == 2
        assert result["language"] == "en"

        stored = service.get(fake_video)
        assert stored is not None
        assert "quick brown fox" in stored["full_text"]
        assert len(stored["segments"]) == 2

    def test_second_call_is_cached(self, service, fake_video):
        first = service.transcribe(fake_video)
        second = service.transcribe(fake_video)
        assert second.get("cached") is True
        assert second["video_path"] == first["video_path"]

    def test_force_retranscribes(self, service, fake_video):
        service.transcribe(fake_video)
        again = service.transcribe(fake_video, force=True)
        assert again.get("cached") is False

    def test_search_finds_spoken_words(self, service, fake_video):
        service.transcribe(fake_video)
        hits = service.search("brown fox")
        assert len(hits) == 1
        assert hits[0]["video_path"] == fake_video
        assert hits[0]["snippets"]

    def test_search_miss_is_empty(self, service, fake_video):
        service.transcribe(fake_video)
        assert service.search("quantum entanglement") == []

    def test_search_paths_helper(self, service, fake_video):
        service.transcribe(fake_video)
        assert service.search_paths("hello world") == [fake_video]

    def test_transcribe_missing_respects_limit_and_existing(self, service, tmp_path):
        v1, v2, v3 = (str(tmp_path / f"v{i}.mp4") for i in (1, 2, 3))
        for p in (v1, v2, v3):
            open(p, "wb").close()
        service.transcribe(v1)  # already done

        result = service.transcribe_missing([v1, v2, v3, "/not.txt"], limit=1)
        assert result == {"transcribed": 1, "skipped_existing": 1, "errors": 0}

    def test_delete_removes(self, service, fake_video):
        service.transcribe(fake_video)
        service.delete(fake_video)
        assert service.get(fake_video) is None

    def test_stats_shape(self, service, fake_video):
        service.transcribe(fake_video)
        stats = service.stats()
        assert stats["available"] is True
        assert stats["videos_transcribed"] == 1
        assert stats["total_audio_seconds"] == 3.0


class TestRouter:
    def test_status_endpoint(self, service, monkeypatch):
        import server.audio_transcription_service as ats

        monkeypatch.setattr(ats, "get_transcription_service", lambda: service)
        response = client.get("/api/transcripts/status")
        assert response.status_code == 200
        assert response.json()["available"] is True

    def test_transcribe_endpoint(self, service, fake_video, monkeypatch):
        import server.audio_transcription_service as ats

        monkeypatch.setattr(ats, "get_transcription_service", lambda: service)
        response = client.post("/api/transcripts/transcribe", json={"video_path": fake_video})
        assert response.status_code == 200
        assert response.json()["segment_count"] == 2

    def test_search_endpoint(self, service, fake_video, monkeypatch):
        import server.audio_transcription_service as ats

        service.transcribe(fake_video)
        monkeypatch.setattr(ats, "get_transcription_service", lambda: service)
        response = client.get("/api/transcripts/search", params={"q": "brown fox"})
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_get_missing_is_404(self, service, monkeypatch):
        import server.audio_transcription_service as ats

        monkeypatch.setattr(ats, "get_transcription_service", lambda: service)
        response = client.get("/api/transcripts/%2Fnope.mp4")
        assert response.status_code == 404


class TestSearchAuxLeg:
    def test_transcript_prefix_reaches_service(self, service, fake_video, monkeypatch):
        import server.api.routers.search as search_mod

        import server.audio_transcription_service as ats

        service.transcribe(fake_video)
        monkeypatch.setattr(ats, "get_transcription_service", lambda: service)
        paths = search_mod._aux_search_paths("transcript:quick brown")
        assert fake_video in paths

    def test_transcript_prefix_no_match(self, service, monkeypatch):
        import server.api.routers.search as search_mod

        import server.audio_transcription_service as ats

        monkeypatch.setattr(ats, "get_transcription_service", lambda: service)
        assert search_mod._aux_search_paths("transcript:zzznothing") == set()
