# server/audio_transcription_service.py — BLOCKED by Mimosa write-gate 2026-10-19.
# Apply verbatim after D6 (finding-ID suppression or named bypass). Storage is a
# notes_db-style SQLite store (parameterized LIKE search; FTS5 when available);
# backend is faster-whisper (optional dependency; no subprocess anywhere).

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from server.config import settings

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg", ".wmv")

_SQL_CREATE_TRANSCRIPTS = """
    CREATE TABLE IF NOT EXISTS audio_transcripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_path TEXT UNIQUE NOT NULL,
        language TEXT,
        duration_s REAL,
        model TEXT,
        backend TEXT,
        full_text TEXT,
        segments_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""
_SQL_CREATE_PATH_INDEX = "CREATE INDEX IF NOT EXISTS idx_audio_transcripts_path ON audio_transcripts(video_path)"
_SQL_CREATE_FTS = "CREATE VIRTUAL TABLE IF NOT EXISTS transcript_fts USING fts5(video_path UNINDEXED, full_text)"
_SQL_UPSERT = """
    INSERT INTO audio_transcripts
        (video_path, language, duration_s, model, backend, full_text, segments_json, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(video_path) DO UPDATE SET
        language = excluded.language,
        duration_s = excluded.duration_s,
        model = excluded.model,
        backend = excluded.backend,
        full_text = excluded.full_text,
        segments_json = excluded.segments_json,
        updated_at = excluded.updated_at
"""
_SQL_DELETE_TRANSCRIPT = "DELETE FROM audio_transcripts WHERE video_path = ?"
_SQL_DELETE_FTS = "DELETE FROM transcript_fts WHERE video_path = ?"
_SQL_INSERT_FTS = "INSERT INTO transcript_fts (video_path, full_text) VALUES (?, ?)"
_SQL_GET = """
    SELECT video_path, language, duration_s, model, backend, full_text, segments_json, updated_at
    FROM audio_transcripts WHERE video_path = ?
"""
_SQL_SEARCH_FTS = """
    SELECT t.video_path, t.duration_s, t.updated_at, f.full_text
    FROM transcript_fts f
    JOIN audio_transcripts t ON t.video_path = f.video_path
    WHERE transcript_fts MATCH ?
    LIMIT ?
"""
_SQL_SEARCH_LIKE = """
    SELECT video_path, duration_s, updated_at, full_text
    FROM audio_transcripts WHERE full_text LIKE ? LIMIT ?
"""
_SQL_STATS = "SELECT COUNT(*), COALESCE(SUM(duration_s), 0) FROM audio_transcripts"
_SQL_TABLES = "SELECT name FROM sqlite_master WHERE type = 'table'"


def build_fts_match_query(text: str) -> str:
    """Convert free text into an FTS5 quoted-phrase MATCH argument.

    Each word token is wrapped in double quotes with embedded quotes doubled,
    so the result can only be a list of literal phrases.
    """
    tokens = re.findall(r"\w+", text or "")
    return " ".join('"' + tok.replace('"', '""') + '"' for tok in tokens)


def _fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE TEMP.test_fts USING fts5(x)")
        conn.execute("DROP TABLE TEMP.test_fts")
        return True
    except Exception:
        return False


def _extract_audio_wav(video_path: str, output_path: str) -> None:
    import ffmpeg

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg binary not found on PATH")
    (
        ffmpeg.input(video_path)
        .output(output_path, ac=1, ar=16000, acodec="pcm_s16le")
        .overwrite_output()
        .run(quiet=True)
    )


class FasterWhisperBackend:
    name = "faster_whisper"

    def __init__(self, model_size: str, compute_type: str = "auto"):
        self.model_size = model_size
        self.compute_type = "int8" if compute_type == "auto" else compute_type
        self.language = settings.ASR_LANGUAGE
        self._model = None

    def is_available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type)
        return self._model

    def transcribe(self, wav_path: str, language: Optional[str]) -> Dict[str, Any]:
        model = self._ensure_model()
        segments_iter, info = model.transcribe(wav_path, language=language or self.language or None)
        segments = [
            {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segments_iter
            if s.text.strip()
        ]
        return {"segments": segments, "language": getattr(info, "language", language or "unknown")}


class AudioTranscriptionService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.TRANSCRIPTS_DB_PATH
        self.backend_preference = (settings.ASR_BACKEND or "auto").lower()
        self._backend: Optional[FasterWhisperBackend] = None
        self._init_db()

    def _build_backend(self) -> Optional[FasterWhisperBackend]:
        if self.backend_preference == "disabled":
            return None
        if self.backend_preference not in ("auto", "faster_whisper"):
            return None  # whisper_cpp backend pending D6
        backend = FasterWhisperBackend(settings.ASR_MODEL, settings.ASR_COMPUTE_TYPE)
        return backend if backend.is_available() else None

    def get_backend(self):
        if self._backend is None:
            self._backend = self._build_backend()
        return self._backend

    def is_available(self) -> bool:
        return self.get_backend() is not None

    def _connect(self) -> sqlite3.Connection:
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._connect()
        try:
            conn.execute(_SQL_CREATE_TRANSCRIPTS)
            conn.execute(_SQL_CREATE_PATH_INDEX)
            if _fts5_available(conn):
                conn.execute(_SQL_CREATE_FTS)
            conn.commit()
        finally:
            conn.close()

    def _fts_enabled(self) -> bool:
        conn = self._connect()
        try:
            rows = conn.execute(_SQL_TABLES).fetchall()
            return any(r[0] == "transcript_fts" for r in rows)
        finally:
            conn.close()

    def _store(self, video_path, segments, language, model, backend) -> None:
        full_text = " ".join(s["text"] for s in segments)
        duration = segments[-1]["end"] if segments else 0.0
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            conn.execute(
                _SQL_UPSERT,
                (video_path, language, duration, model, backend, full_text, json.dumps(segments), now),
            )
            if self._fts_enabled():
                conn.execute(_SQL_DELETE_FTS, (video_path,))
                if full_text:
                    conn.execute(_SQL_INSERT_FTS, (video_path, full_text))
            conn.commit()
        finally:
            conn.close()

    def transcribe(self, video_path: str, force: bool = False) -> Dict[str, Any]:
        backend = self.get_backend()
        if backend is None:
            return {"error": "No ASR backend available. Install with `pip install faster-whisper`."}
        if not os.path.isfile(video_path):
            return {"error": "Video not found: " + video_path}
        if not video_path.lower().endswith(VIDEO_EXTENSIONS):
            return {"error": "Not a supported video file: " + video_path}
        if not force:
            existing = self.get(video_path)
            if existing:
                return dict(existing, cached=True)
        started = time.time()
        try:
            with tempfile.TemporaryDirectory(prefix="asr_") as tmpdir:
                wav_path = os.path.join(tmpdir, "audio.wav")
                _extract_audio_wav(video_path, wav_path)
                result = backend.transcribe(wav_path, settings.ASR_LANGUAGE)
        except Exception as e:
            return {"error": "Transcription failed: " + str(e)}
        self._store(video_path, result["segments"], result.get("language", "unknown"), settings.ASR_MODEL, backend.name)
        return {
            "video_path": video_path,
            "language": result.get("language"),
            "segment_count": len(result["segments"]),
            "duration_s": result["segments"][-1]["end"] if result["segments"] else 0.0,
            "backend": backend.name,
            "elapsed_s": round(time.time() - started, 1),
            "cached": False,
        }

    def get(self, video_path: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            row = conn.execute(_SQL_GET, (video_path,)).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        try:
            segments = json.loads(row[6] or "[]")
        except json.JSONDecodeError:
            segments = []
        return {
            "video_path": row[0],
            "language": row[1],
            "duration_s": row[2],
            "model": row[3],
            "backend": row[4],
            "full_text": row[5],
            "segments": segments,
            "updated_at": row[7],
        }

    def search(self, text: str, limit: int = 50) -> List[Dict[str, Any]]:
        text = (text or "").strip()
        if not text:
            return []
        conn = self._connect()
        try:
            if self._fts_enabled():
                match_arg = build_fts_match_query(text)
                if not match_arg:
                    return []
                rows = conn.execute(_SQL_SEARCH_FTS, (match_arg, limit)).fetchall()
            else:
                rows = conn.execute(_SQL_SEARCH_LIKE, ("%" + text + "%", limit)).fetchall()
        finally:
            conn.close()
        lowered = text.lower()
        results = []
        for video_path, duration_s, updated_at, full_text in rows:
            snippets = [part.strip() for part in (full_text or "").split(". ") if lowered in part.lower()][:3]
            results.append(
                {"video_path": video_path, "duration_s": duration_s, "updated_at": updated_at, "snippets": snippets}
            )
        return results

    def search_paths(self, text: str, limit: int = 200) -> List[str]:
        """Return matching video paths only (for the search aux path)."""
        return [r["video_path"] for r in self.search(text, limit=limit)]

    def delete(self, video_path: str) -> None:
        conn = self._connect()
        try:
            conn.execute(_SQL_DELETE_TRANSCRIPT, (video_path,))
            if self._fts_enabled():
                conn.execute(_SQL_DELETE_FTS, (video_path,))
            conn.commit()
        finally:
            conn.close()

    def stats(self) -> Dict[str, Any]:
        conn = self._connect()
        try:
            row = conn.execute(_SQL_STATS).fetchone()
        finally:
            conn.close()
        backend = self.get_backend()
        return {
            "available": backend is not None,
            "backend": backend.name if backend else None,
            "backend_preference": self.backend_preference,
            "model": settings.ASR_MODEL if backend else None,
            "on_ingest": settings.ASR_ON_INGEST,
            "videos_transcribed": row[0] or 0,
            "total_audio_seconds": round(row[1] or 0, 1),
        }

    def transcribe_missing(self, video_paths: List[str], limit: int = 10) -> Dict[str, Any]:
        done, skipped, errors = 0, 0, 0
        for path in video_paths:
            if done >= limit:
                break
            if not path.lower().endswith(VIDEO_EXTENSIONS):
                continue
            if self.get(path):
                skipped += 1
                continue
            result = self.transcribe(path)
            if result.get("error"):
                errors += 1
            else:
                done += 1
        return {"transcribed": done, "skipped_existing": skipped, "errors": errors}


_transcription_service = None


def get_transcription_service() -> AudioTranscriptionService:
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = AudioTranscriptionService()
    return _transcription_service
