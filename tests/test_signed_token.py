from server.signed_urls import issue_token, verify_token, TokenError
from server.config import settings
import time

def test_issue_and_verify_token(monkeypatch):
    monkeypatch.setattr(settings, "SIGNED_URL_SECRET", "test_secret")

    token = issue_token("/tmp/photo.jpg", uid="user123", ttl=5, scope="thumbnail")
    payload = verify_token(token, expected_scope="thumbnail")
    assert payload["path"] == "/tmp/photo.jpg"
    assert payload["uid"] == "user123"

    # Expired token
    expired = issue_token("/tmp/photo.jpg", ttl=-1)
    try:
        verify_token(expired)
        assert False, "Expired token should raise"
    except TokenError:
        pass

    # Malformed token
    try:
        verify_token("not_a_token")
        assert False, "Malformed token should raise"
    except TokenError:
        pass
