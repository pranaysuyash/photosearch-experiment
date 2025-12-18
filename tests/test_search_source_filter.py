from fastapi.testclient import TestClient
from server.main import app
from server.config import settings

client = TestClient(app)


def test_search_with_source_filter_returns_ok(monkeypatch):
    # Basic smoke test to ensure source_filter parameter is accepted
    res = client.get('/search', params={'query': '', 'mode': 'metadata', 'source_filter': 'cloud'})
    assert res.status_code == 200
    assert 'results' in res.json()
