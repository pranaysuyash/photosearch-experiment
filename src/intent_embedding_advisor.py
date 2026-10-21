"""Local zero-shot intent advisor.

An IntentDetector-shaped wrapper that escalates low-confidence keyword
verdicts to a local text-embedding zero-shot classification over the same 12
intents. Free, offline, no API key; complements (and sits beneath) the cloud
JevIntentAdvisor tier:

    keyword IntentDetector → EmbeddingIntentAdvisor (local) → JevIntentAdvisor (cloud, off)

Escalation triggers mirror JevIntentAdvisor: low keyword confidence or a
contested top-two margin. The model loads lazily on first escalation, so
server startup and CI never download weights.

Provenance is recorded under ``base["embedding_advisor"]`` alongside the
Jev-style ``base["advisor"]`` metadata.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional

DEFAULT_MODEL = "all-MiniLM-L6-v2"  # ungated, MIT, ~80 MB
DEFAULT_TAIL_THRESHOLD = 0.5
DEFAULT_MARGIN_THRESHOLD = 2.0
DEFAULT_SIMILARITY_GATE = 0.35


class EmbeddingIntentAdvisor:
    """IntentDetector-shaped wrapper adding a local embedding advisory tier."""

    def __init__(
        self,
        detector: Any,
        *,
        enabled: bool = True,
        model_name: str = DEFAULT_MODEL,
        tail_threshold: float = DEFAULT_TAIL_THRESHOLD,
        margin_threshold: float = DEFAULT_MARGIN_THRESHOLD,
        similarity_gate: float = DEFAULT_SIMILARITY_GATE,
        encoder: Optional[Callable[[List[str]], List[List[float]]]] = None,
    ):
        self.detector = detector
        self.model_name = model_name
        self.enabled = bool(enabled)
        self.tail_threshold = tail_threshold
        self.margin_threshold = margin_threshold
        self.similarity_gate = similarity_gate
        # Injected encoder (tests) or lazy SentenceTransformer.
        self._encoder = encoder
        self._model = None
        self._label_embeddings: Optional[List[List[float]]] = None
        self._label_names: List[str] = []

    @classmethod
    def from_env(cls, detector: Any) -> "EmbeddingIntentAdvisor":
        """Build from environment; nothing here can raise at startup."""

        def _float(name: str, default: float) -> float:
            try:
                return float(os.environ.get(name, "") or default)
            except ValueError:
                return default

        return cls(
            detector,
            enabled=os.environ.get("INTENT_EMBEDDING_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off"),
            model_name=os.environ.get("INTENT_EMBEDDING_MODEL", DEFAULT_MODEL),
            tail_threshold=_float("INTENT_EMBEDDING_TAIL_THRESHOLD", DEFAULT_TAIL_THRESHOLD),
            margin_threshold=_float("INTENT_EMBEDDING_MARGIN_THRESHOLD", DEFAULT_MARGIN_THRESHOLD),
            similarity_gate=_float("INTENT_EMBEDDING_SIMILARITY_GATE", DEFAULT_SIMILARITY_GATE),
        )

    # ------------------------------------------------------------------
    # IntentDetector-shaped public interface
    # ------------------------------------------------------------------

    @property
    def intent_definitions(self) -> Dict:
        """Delegate so outer wrappers (e.g. Jev) see the canonical definitions."""
        return self.detector.intent_definitions

    def detect_intent(self, query: str) -> Dict:
        base = self.detector.detect_intent(query)
        meta: Dict[str, Any] = {
            "enabled": self.enabled,
            "source": "keyword",
            "escalation": "none",
            "model": self.model_name,
            "latency_ms": None,
            "top_similarity": None,
            "embedding_choice": None,
            "error": None,
        }

        trigger = self._escalation_trigger(base)
        if trigger is not None:
            meta["escalation"] = trigger

        if not self.enabled or trigger is None or not query or not query.strip():
            base["embedding_advisor"] = meta
            return base

        merged = dict(base)
        try:
            started = time.perf_counter()
            ranked = self._rank_intents(query)
            meta["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)

            top_name, top_sim = ranked[0]
            meta["top_similarity"] = round(top_sim, 4)
            meta["embedding_choice"] = top_name

            if top_sim >= self.similarity_gate:
                self._merge_primary(merged, ranked)
                meta["source"] = "embedding"
            else:
                meta["source"] = "keyword_fallback"
                meta["error"] = "top similarity below gate"
        except Exception as exc:  # advisory failure must never break search
            meta["source"] = "keyword_fallback"
            meta["error"] = f"{type(exc).__name__}: {exc}"[:200]

        merged["embedding_advisor"] = meta
        return merged

    def get_search_badges(self, query: str) -> List[Dict]:
        return self.detect_intent(query)["badges"]

    def get_search_suggestions(self, query: str) -> List[str]:
        return self.detect_intent(query)["suggestions"]

    def get_all_intents(self) -> Dict:
        return self.detector.get_all_intents()

    # ------------------------------------------------------------------
    # Zero-shot classification
    # ------------------------------------------------------------------

    def _escalation_trigger(self, base: Dict) -> Optional[str]:
        """Same trigger bands as JevIntentAdvisor (see its docstring)."""
        if base.get("confidence", 0.0) < self.tail_threshold:
            return "low_confidence"
        scores = base.get("scores") or {}
        positive = sorted((v for v in scores.values() if v > 0), reverse=True)
        if len(positive) >= 2 and (positive[0] - positive[1]) < self.margin_threshold:
            return "contested_margin"
        return None

    def _ensure_model(self) -> None:
        if self._encoder is not None and self._label_embeddings is not None:
            return
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

        definitions = self.detector.intent_definitions
        # Zero-shot labels reuse the detector's own descriptions — one source
        # of truth for what each intent means, no duplicated definitions.
        prompts = [f"A photo search query about: {definitions[name].get('description', name)}" for name in definitions]
        self._label_names = list(definitions.keys())
        embeddings = (
            self._encoder(prompts)
            if self._encoder is not None
            else self._model.encode(prompts, normalize_embeddings=True).tolist()
        )
        self._label_embeddings = embeddings

    def _rank_intents(self, query: str) -> List[tuple]:
        """Return [(intent_name, cosine_similarity)] sorted descending."""
        self._ensure_model()
        query_vec = (
            self._encoder([query])[0]
            if self._encoder is not None
            else self._model.encode([query], normalize_embeddings=True)[0].tolist()
        )

        def cosine(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5 or 1.0
            nb = sum(x * x for x in b) ** 0.5 or 1.0
            return dot / (na * nb)

        ranked = [
            (name, cosine(query_vec, label_vec))
            for name, label_vec in zip(self._label_names, self._label_embeddings or [])
        ]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _merge_primary(self, merged: Dict, ranked: List[tuple]) -> None:
        """Apply the embedding verdict onto the keyword result dict."""
        top_name, top_sim = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else None

        merged["primary_intent"] = top_name
        # Confidence from zero-shot similarity: a weak-but-winning similarity
        # stays proportionally unconfident.
        merged["confidence"] = round(max(0.0, min(1.0, top_sim)), 4)
        secondaries = [name for name, _ in ranked[1:3] if name != top_name]
        if runner_up:
            merged["secondary_intents"] = secondaries
        scores = dict(merged.get("scores") or {})
        if scores:
            # Keep the scores payload shaped like the keyword detector's
            # (relative shares) so downstream consumers still work.
            total = sum(sim for _, sim in ranked) or 1.0
            for name, sim in ranked:
                scores[name] = round(sim / total, 4)
            merged["scores"] = scores
