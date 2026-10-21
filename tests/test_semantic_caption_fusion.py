"""Semantic search caption-fusion tests (P0.1).

Proves the fusion contract in /search/semantic:
- a caption score higher than the image score wins and is marked matchedVia
- caption-only matches appear as results
- global re-ranking + pagination happen after fusion
- caption failures never break image search
"""

import asyncio
from types import SimpleNamespace

from server.api.routers.semantic_search import search_semantic


class FakeEmbedding:
    model_name = "fake-model"

    def generate_text_embedding(self, text):
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def __init__(self, results):
        self._results = results

    def search(self, query_embedding, limit=50, offset=0):
        return self._results[:limit]


class FakeCaptionIndex:
    def __init__(self, hits, count=None, fail=False):
        self._hits = hits
        self._count = len(hits) if count is None else count
        self._fail = fail
        self.queries = []

    def get_count(self):
        return self._count

    def embed_query(self, query, embedding_generator=None):
        self.queries.append(query)
        return [0.1, 0.2, 0.3]

    def search(self, query_embedding, limit=50, min_score=0.0):
        if self._fail:
            raise RuntimeError("index exploded")
        return [h for h in self._hits if h["score"] >= min_score][:limit]


class FakeMetadataDB:
    def get_metadata_by_path(self, path):
        return {"file.path": path}


def make_state(vector_results, caption_hits, caption_fail=False):
    return SimpleNamespace(
        embedding_generator=FakeEmbedding(),
        vector_store=FakeVectorStore(vector_results),
        caption_index=FakeCaptionIndex(caption_hits, fail=caption_fail),
        photo_search_engine=SimpleNamespace(db=FakeMetadataDB()),
    )


def img(path, score):
    return {"id": path, "score": score, "metadata": {"path": path, "filename": path.split("/")[-1]}}


def cap(path, score):
    return {"path": path, "score": score, "caption": f"caption for {path}"}


def run(state, **kwargs):
    kwargs.setdefault("query", "sunset picnic")
    return asyncio.run(search_semantic(state=state, **kwargs))


class TestFusion:
    def test_higher_caption_score_wins_and_is_marked(self):
        state = make_state([img("/a.jpg", 0.30), img("/b.jpg", 0.80)], [cap("/a.jpg", 0.60)])
        result = run(state, limit=10)

        by_path = {r["path"]: r for r in result["results"]}
        assert by_path["/a.jpg"]["score"] == 0.60
        assert by_path["/a.jpg"]["matchedVia"] == "caption"
        assert by_path["/b.jpg"]["matchedVia"] == "image"
        assert by_path["/b.jpg"]["score"] == 0.80

    def test_lower_caption_score_keeps_image_score(self):
        state = make_state([img("/a.jpg", 0.80)], [cap("/a.jpg", 0.40)])
        result = run(state, limit=10)
        assert result["results"][0]["score"] == 0.80
        assert result["results"][0]["matchedVia"] == "image"

    def test_caption_only_match_included(self):
        state = make_state([img("/a.jpg", 0.50)], [cap("/c.jpg", 0.55)])
        result = run(state, limit=10)
        paths = {r["path"] for r in result["results"]}
        assert paths == {"/a.jpg", "/c.jpg"}
        cap_result = next(r for r in result["results"] if r["path"] == "/c.jpg")
        assert cap_result["matchedVia"] == "caption"
        assert "caption" in cap_result["matchExplanation"]

    def test_global_ranking_after_fusion(self):
        state = make_state(
            [img("/low.jpg", 0.30), img("/high.jpg", 0.70)],
            [cap("/mid.jpg", 0.50), cap("/top.jpg", 0.90)],
        )
        result = run(state, limit=10)
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)
        assert result["results"][0]["path"] == "/top.jpg"

    def test_pagination_applies_after_fusion(self):
        state = make_state(
            [img("/a.jpg", 0.30), img("/b.jpg", 0.70)],
            [cap("/c.jpg", 0.90)],
        )
        result = run(state, limit=1, offset=1)
        assert len(result["results"]) == 1
        assert result["results"][0]["path"] == "/b.jpg"  # 0.90, 0.70, 0.30 → second

    def test_min_score_applies_to_caption_leg(self):
        state = make_state([], [cap("/weak.jpg", 0.10)])
        result = run(state, limit=10, min_score=0.22)
        assert result["results"] == []

    def test_caption_failure_never_breaks_image_search(self):
        state = make_state([img("/a.jpg", 0.50)], [], caption_fail=True)
        result = run(state, limit=10)
        assert result["results"][0]["path"] == "/a.jpg"

    def test_empty_caption_index_is_skipped(self):
        state = make_state([img("/a.jpg", 0.50)], [])
        assert state.caption_index.get_count() == 0
        result = run(state, limit=10)
        assert result["results"][0]["path"] == "/a.jpg"
