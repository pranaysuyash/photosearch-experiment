"""store_generated_caption policy tests (register-seed on-ramp, R1)."""

import pytest

from server.config import settings
from server.vlm_caption_service import VLMCaptionService


@pytest.fixture
def service(tmp_path, monkeypatch):
    # Keep unit tests off the network: disable the dedicated caption embedder.
    monkeypatch.setattr(settings, "CAPTION_EMBEDDING_MODEL", "")
    return VLMCaptionService(str(tmp_path / "captions.db"))


class TestStoreGeneratedCaption:
    def test_stores_when_no_existing(self, service):
        result = service.store_generated_caption("/a.jpg", "a beach", "blip-base", "photo-register")
        assert result == {"stored": True, "replaced": False}
        stored = service.get_caption("/a.jpg")
        assert stored["caption"] == "a beach"
        assert stored["provider"] == "photo-register"
        assert stored["is_generated"] is True
        assert stored["is_edited"] is False

    def test_never_overwrites_user_edited(self, service):
        service.update_caption("/a.jpg", "my hand-written caption")
        result = service.store_generated_caption(
            "/a.jpg", "blip says something", "blip-base", "photo-register", overwrite_generated=True
        )
        assert result["stored"] is False
        assert "user-edited" in result["reason"]
        assert service.get_caption("/a.jpg")["caption"] == "my hand-written caption"

    def test_keeps_existing_generated_unless_forced(self, service):
        service.store_generated_caption("/a.jpg", "gemma quality caption", "gemma4:e4b", "ollama")
        result = service.store_generated_caption("/a.jpg", "blip caption", "blip-base", "photo-register")
        assert result["stored"] is False
        assert service.get_caption("/a.jpg")["caption"] == "gemma quality caption"

        forced = service.store_generated_caption(
            "/a.jpg", "blip caption", "blip-base", "photo-register", overwrite_generated=True
        )
        assert forced == {"stored": True, "replaced": True}
        assert service.get_caption("/a.jpg")["provider"] == "photo-register"

    def test_empty_caption_is_noop(self, service):
        result = service.store_generated_caption("/a.jpg", "   ", "blip-base", "photo-register")
        assert result["stored"] is False
        assert service.get_caption("/a.jpg") is None

    def test_get_all_captions_includes_seeded(self, service):
        service.store_generated_caption("/a.jpg", "a beach", "blip-base", "photo-register")
        rows = service.get_all_captions()
        assert len(rows) == 1
        assert rows[0]["photo_path"] == "/a.jpg"
        assert rows[0]["updated_at"]
