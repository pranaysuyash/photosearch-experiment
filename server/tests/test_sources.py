from pathlib import Path

from server.sources import SourceStore


def test_create_list_redact(tmp_path: Path):
    store = SourceStore(tmp_path / "sources.db")
    s3 = store.create_source(
        "s3",
        name="My S3",
        config={
            "endpoint_url": "https://example.com",
            "region": "auto",
            "bucket": "bucket",
            "access_key_id": "AKIA_TEST",
            "secret_access_key": "SECRET_TEST",
        },
        status="pending",
    )
    assert s3.type == "s3"
    assert s3.config["secret_access_key"] == "SECRET_TEST"

    redacted = store.get_source(s3.id, redact=True)
    assert redacted.config["secret_access_key"] == "••••••••"
    assert str(redacted.config["access_key_id"]).startswith("AKIA")

    all_redacted = store.list_sources(redact=True)
    assert len(all_redacted) == 1
    assert all_redacted[0].id == s3.id


def test_update_and_delete(tmp_path: Path):
    store = SourceStore(tmp_path / "sources.db")
    src = store.create_source(
        "local_folder",
        name="Photos",
        config={"path": "/tmp/photos"},
        status="connected",
    )
    updated = store.update_source(src.id, status="error", last_error="boom", config_patch={"path": "/tmp/new"})
    assert updated.status == "error"
    assert updated.last_error == "boom"
    assert updated.config["path"] == "/tmp/new"

    store.delete_source(src.id)
    assert store.list_sources() == []
