import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from server.config import settings
from server.utils.files import is_video_file
from server.utils.search_explanations import (
    generate_hybrid_match_explanation,
    generate_metadata_match_explanation,
)
from server.utils.sorting import apply_date_filter, apply_sort
from server.validation import (
    validate_date_input,
    validate_pagination_params,
    validate_search_query,
)
from server.api.deps import get_state
from server.core.state import AppState

router = APIRouter()


def _aux_search_paths(query: str) -> set[str]:
    """Return extra matching photo paths from feature DBs.

    This is primarily used to make feature integrations (notes/tags/locations/people
    tags) discoverable via /search even when a file hasn't been scanned into the
    main metadata DB yet.
    """

    q = (query or "").strip()
    if not q:
        return set()

    q_lower = q.lower()
    paths: set[str] = set()

    try:
        # People tags (free-form tagging, independent from face clusters)
        if q_lower.startswith("person:"):
            person_name = q.split(":", 1)[1].strip()
            if person_name:
                from server.people_tags_db import get_people_tags_db

                people_db = get_people_tags_db(settings.BASE_DIR / "people_tags.db")
                paths.update(people_db.search_photos_by_person(person_name))
            return paths

        # Tag structured queries like: tag:foo OR tag:bar, tag:foo AND tag:bar
        if "tag:" in q_lower:
            tag_names = re.findall(r"tag:([^\s]+)", q, flags=re.IGNORECASE)
            tag_names = [t.strip() for t in tag_names if t.strip()]
            if tag_names:
                from server.tags_db import get_tags_db

                tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
                sets = [set(tags_db.get_tag_paths(t)) for t in tag_names]
                if sets:
                    if " AND " in q.upper():
                        paths.update(set.intersection(*sets))
                    else:
                        paths.update(set.union(*sets))
            return paths

        # Location structured queries like: location:Central Park
        if q_lower.startswith("location:"):
            place = q.split(":", 1)[1].strip()
            if place:
                from server.locations_db import get_locations_db

                locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
                rows = locations_db.get_photos_by_place(place)
                for r in rows:
                    p = r.get("photo_path")
                    if isinstance(p, str) and p:
                        paths.add(p)
            return paths

        # Generic: union matches from notes/tags/locations/people
        from server.notes_db import get_notes_db
        from server.tags_db import get_tags_db
        from server.locations_db import get_locations_db
        from server.people_tags_db import get_people_tags_db

        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        for r in notes_db.search_notes(q, limit=200):
            p = r.get("path")
            if isinstance(p, str) and p:
                paths.add(p)

        tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
        paths.update(tags_db.get_tag_paths(q))

        people_db = get_people_tags_db(settings.BASE_DIR / "people_tags.db")
        paths.update(people_db.search_photos_by_person(q))

        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        for r in locations_db.get_photos_by_place(q):
            p = r.get("photo_path")
            if isinstance(p, str) and p:
                paths.add(p)

    except Exception:
        # Auxiliary matches should never break core search.
        return paths

    return paths


@router.get("/search")
async def search_photos(
    state: AppState = Depends(get_state),
    query: str = "",
    limit: int = 50,
    offset: int = 0,
    mode: str = "metadata",
    sort_by: str = "date_desc",  # date_desc, date_asc, name, size
    type_filter: str = "all",  # all, photos, videos
    source_filter: str = "all",  # all, local, cloud, hybrid
    favorites_filter: str = "all",  # all, favorites_only
    tag: Optional[
        str
    ] = None,  # Filter to a single user tag (deprecated, use tags instead)
    tags: Optional[str] = None,  # Filter by multiple tags, format: "tag1,tag2,tag3"
    tag_logic: str = "OR",  # "AND" or "OR" for combining multiple tags
    date_from: Optional[str] = None,  # YYYY-MM or ISO date/datetime
    date_to: Optional[str] = None,  # YYYY-MM or ISO date/datetime
    person: Optional[str] = None,  # Filter by person name (searches face clusters)
    log_history: bool = True,  # Whether to log this search to history
):
    """
    Unified Search Endpoint.
    Modes:
      - 'metadata' (SQL)
      - 'semantic' (CLIP)
      - 'hybrid' (Merge Metadata + Semantic)
    Sort: date_desc (default), date_asc, name, size
    Type Filter: all (default), photos, videos
    Favorites Filter: all (default), favorites_only
    """
    try:
        from server.api.routers.semantic_search import search_semantic

        photo_search_engine = state.photo_search_engine
        face_clusterer = state.face_clusterer
        intent_detector = state.intent_detector
        saved_search_manager = state.saved_search_manager
        ps_logger = state.ps_logger
        log_search_operation = state.log_search_operation
        import time

        start_time = time.time()

        # Input validation
        query_result = validate_search_query(query, max_length=500)
        if not query_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search query: {query_result.error_message}",
            )
        _validated_query = query_result.sanitized_value

        pagination_result = validate_pagination_params(limit, offset)
        if not pagination_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pagination: {pagination_result.error_message}",
            )
        _validated_limit = pagination_result.sanitized_value["limit"]
        _validated_offset = pagination_result.sanitized_value["offset"]

        # Validate dates
        if date_from:
            date_from_result = validate_date_input(date_from)
            if not date_from_result.is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date_from: {date_from_result.error_message}",
                )
            _validated_date_from = date_from_result.sanitized_value
        else:
            _validated_date_from = None

        if date_to:
            date_to_result = validate_date_input(date_to)
            if not date_to_result.is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date_to: {date_to_result.error_message}",
                )
            _validated_date_to = date_to_result.sanitized_value
        else:
            _validated_date_to = None

        # Validate mode
        valid_modes = {"metadata", "semantic", "hybrid"}
        if mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode}. Must be one of {valid_modes}",
            )

        # Validate sort_by
        valid_sort_options = {"date_desc", "date_asc", "name", "size"}
        if sort_by not in valid_sort_options:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by: {sort_by}. Must be one of {valid_sort_options}",
            )

        # Validate filters
        valid_type_filters = {"all", "photos", "videos"}
        if type_filter not in valid_type_filters:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type_filter: {type_filter}. Must be one of {valid_type_filters}",
            )

        valid_source_filters = {"all", "local", "cloud", "hybrid"}
        if source_filter not in valid_source_filters:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_filter: {source_filter}. Must be one of {valid_source_filters}",
            )

        valid_favorites_filters = {"all", "favorites_only"}
        if favorites_filter not in valid_favorites_filters:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid favorites_filter: {favorites_filter}. Must be one of {valid_favorites_filters}",
            )

        if tag_logic not in {"AND", "OR"}:
            raise HTTPException(
                status_code=400, detail="Invalid tag_logic: Must be 'AND' or 'OR'"
            )

        tagged_paths = None
        if tag or tags:
            try:
                from server.tags_db import get_tags_db

                tags_db = get_tags_db(settings.BASE_DIR / "tags.db")

                # Handle both single tag and multiple tags
                if tags:
                    # Split multiple tags and remove whitespace
                    tag_list = [t.strip() for t in tags.split(",")]

                    # Get paths for each tag
                    all_tagged_paths = {}
                    for t in tag_list:
                        if t:  # Skip empty tags
                            all_tagged_paths[t] = set(tags_db.get_tag_paths(t))

                    # Apply logic based on tag_logic (AND/OR)
                    if tag_logic.upper() == "AND":
                        # For AND logic, find intersection of all tag sets
                        if all_tagged_paths:
                            tagged_paths = set.intersection(*all_tagged_paths.values())
                    elif tag_logic.upper() == "OR":
                        # For OR logic, find union of all tag sets
                        if all_tagged_paths:
                            tagged_paths = set.union(*all_tagged_paths.values())
                        else:
                            tagged_paths = set()
                    else:
                        # Default to OR if invalid logic provided
                        if all_tagged_paths:
                            tagged_paths = set.union(*all_tagged_paths.values())
                        else:
                            tagged_paths = set()
                elif tag:
                    # Original single tag logic
                    tagged_paths = set(tags_db.get_tag_paths(tag))
            except Exception as e:
                print(f"Tag filtering error: {e}")
                tagged_paths = set()

        # Person filter - get photo paths containing the person
        # Also auto-detect person names from query if not explicitly provided
        person_paths = None
        person_to_search = person
        remaining_query = query  # Query after extracting person: prefix

        # Parse person: prefix from query (e.g., "person:John Doe")
        if not person and query and query.lower().startswith("person:"):
            person_to_search = query.split(":", 1)[1].strip()
            remaining_query = ""
            print(
                f"Explicit person search: '{person_to_search}', remaining query: '{remaining_query}'"
            )

        # Auto-detect: if query matches a person/cluster label, treat it as person search
        if not person_to_search and query and face_clusterer:
            try:
                cursor = face_clusterer.conn.cursor()
                # Check if query matches any cluster label (exact or partial match)
                cursor.execute(
                    """
                    SELECT c.label FROM clusters c
                    WHERE LOWER(c.label) LIKE LOWER(?)
                    AND c.label NOT LIKE 'Person %'
                """,
                    (f"%{query}%",),
                )
                matching_labels = [row[0] for row in cursor.fetchall()]
                if matching_labels:
                    # Query matches a person name - use it as person filter
                    person_to_search = query
                    print(
                        f"Auto-detected person search: '{query}' matches {matching_labels}"
                    )
            except Exception as e:
                print(f"Person auto-detection error: {e}")

        if person_to_search:
            try:
                if face_clusterer:
                    cursor = face_clusterer.conn.cursor()
                    # Find clusters matching the person name (case-insensitive)
                    cursor.execute(
                        """
                        SELECT c.id FROM clusters c
                        WHERE LOWER(c.label) LIKE LOWER(?)
                    """,
                        (f"%{person_to_search}%",),
                    )
                    matching_clusters = [row[0] for row in cursor.fetchall()]

                    if matching_clusters:
                        # Get all faces for these clusters
                        placeholders = ",".join(["?"] * len(matching_clusters))
                        cursor.execute(
                            f"""
                            SELECT DISTINCT image_path FROM faces
                            WHERE cluster_id IN ({placeholders})
                        """,
                            matching_clusters,
                        )
                        person_paths = set(row[0] for row in cursor.fetchall())
                    else:
                        person_paths = set()  # No matching person, return empty
            except Exception as e:
                print(f"Person filtering error: {e}")
                person_paths = None

        # Build person results with high priority score (if person detected)
        person_results = []
        if person_to_search and person_paths:
            import json

            cursor = photo_search_engine.db.conn.cursor()
            if person_paths:
                placeholders = ",".join(["?" for _ in person_paths])
                cursor.execute(
                    f"SELECT file_path, metadata_json FROM metadata WHERE file_path IN ({placeholders})",
                    list(person_paths),
                )
                for row in cursor.fetchall():
                    metadata = (
                        json.loads(row["metadata_json"]) if row["metadata_json"] else {}
                    )
                    person_results.append(
                        {
                            "path": row["file_path"],
                            "filename": os.path.basename(row["file_path"]),
                            "score": 2.0,  # Highest priority for person matches
                            "metadata": metadata,
                            "match_type": "person",
                            "matched_person": person_to_search,
                        }
                    )

        # 1. Semantic Search
        if mode == "semantic":
            results_response = await search_semantic(
                query, limit * 2, 0
            )  # Get more for filtering
            results = results_response.get("results", [])

            if tagged_paths is not None:
                results = [r for r in results if r.get("path") in tagged_paths]

            # Apply person filter
            if person_paths is not None:
                results = [r for r in results if r.get("path") in person_paths]

            # Apply type filter
            if type_filter == "photos":
                results = [r for r in results if not is_video_file(r.get("path", ""))]
            elif type_filter == "videos":
                results = [r for r in results if is_video_file(r.get("path", ""))]

            # Apply favorites filter
            if favorites_filter == "favorites_only":
                results = [
                    r
                    for r in results
                    if photo_search_engine.is_favorite(r.get("path", ""))
                ]

            # Apply date filter (filesystem.created)
            results = apply_date_filter(results, date_from, date_to)
            # Apply source filter (local/cloud/hybrid)
            if source_filter != "all":

                def is_cloud_path(p: str) -> bool:
                    if not p:
                        return False
                    lower = p.lower()
                    return (
                        lower.startswith("http://")
                        or lower.startswith("https://")
                        or lower.startswith("s3://")
                        or lower.startswith("cloud:")
                        or lower.startswith("gdrive:")
                        or "amazonaws.com" in lower
                        or lower.startswith("dropbox:")
                        or lower.startswith("onedrive:")
                    )

                def is_local_path(p: str) -> bool:
                    if not p:
                        return False
                    return bool(re.match(r"^[A-Za-z]:\\|^/|^file://|^~/", p))

                if source_filter == "local":
                    results = [r for r in results if is_local_path(r.get("path", ""))]
                elif source_filter == "cloud":
                    results = [r for r in results if is_cloud_path(r.get("path", ""))]
                elif source_filter == "hybrid":
                    results = [
                        r
                        for r in results
                        if (
                            not is_local_path(r.get("path", ""))
                            and not is_cloud_path(r.get("path", ""))
                        )
                    ]

            # Apply sort
            results = apply_sort(results, sort_by)

            # Merge person results (highest priority) with other results
            if person_results:
                seen_paths = set()
                merged = []
                # Add person matches first (score 2.0)
                for r in person_results:
                    path = r.get("path")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        merged.append(r)
                # Add other results (avoiding duplicates)
                for r in results:
                    path = r.get("path")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        merged.append(r)
                results = merged

            # Paginate
            paginated = results[offset : offset + limit]
            return {
                "count": len(results),
                "results": paginated,
                "matched_person": person_to_search if person_results else None,
            }

        # 2. Metadata Search
        if mode == "metadata":
            # For empty query, directly get all files from database
            if not query.strip():
                cursor = photo_search_engine.db.conn.cursor()
                cursor.execute("SELECT file_path, metadata_json FROM metadata")
                results = []
                for row in cursor.fetchall():
                    import json

                    results.append(
                        {
                            "file_path": row["file_path"],
                            "metadata": json.loads(row["metadata_json"])
                            if row["metadata_json"]
                            else {},
                        }
                    )
            else:
                # Check if query has structured operators (=, >, <, LIKE, etc.)
                has_operators = any(
                    op in query
                    for op in ["=", ">", "<", "!=", " LIKE ", " CONTAINS ", ":"]
                )
                print(f"DEBUG: Query='{query}', has_operators={has_operators}")

                if not has_operators:
                    # Simple search term - search in filename using shortcut format
                    search_query = f"filename:{query}"
                    print(
                        f"DEBUG: Simple query '{query}' converted to '{search_query}'"
                    )
                    results = photo_search_engine.query_engine.search(search_query)
                else:
                    # Structured query - use as-is
                    print(f"DEBUG: Using structured query as-is: '{query}'")
                    results = photo_search_engine.query_engine.search(query)

            # Formatted list with match explanations
            formatted_results = []
            for r in results:
                path = r.get("file_path", r.get("path"))
                result_item = {
                    "path": path,
                    "filename": os.path.basename(path),
                    "score": r.get("score", 0),
                    "metadata": r.get("metadata", {}),
                }

                # Generate match explanation for metadata search
                if query.strip():
                    result_item["matchExplanation"] = (
                        generate_metadata_match_explanation(query, r)
                    )

                formatted_results.append(result_item)

            # Apply type filter
            if type_filter == "photos":
                formatted_results = [
                    r for r in formatted_results if not is_video_file(r.get("path", ""))
                ]
            elif type_filter == "videos":
                formatted_results = [
                    r for r in formatted_results if is_video_file(r.get("path", ""))
                ]

            if tagged_paths is not None:
                formatted_results = [
                    r for r in formatted_results if r.get("path") in tagged_paths
                ]

            # Apply person filter
            if person_paths is not None:
                formatted_results = [
                    r for r in formatted_results if r.get("path") in person_paths
                ]

            # Apply favorites filter
            if favorites_filter == "favorites_only":
                formatted_results = [
                    r
                    for r in formatted_results
                    if photo_search_engine.is_favorite(r.get("path", ""))
                ]

            # Apply date filter (filesystem.created)
            formatted_results = apply_date_filter(formatted_results, date_from, date_to)
            # Apply source filter (local/cloud/hybrid)
            if source_filter != "all":

                def is_cloud_path(p: str) -> bool:
                    if not p:
                        return False
                    lower = p.lower()
                    return (
                        lower.startswith("http://")
                        or lower.startswith("https://")
                        or lower.startswith("s3://")
                        or lower.startswith("cloud:")
                        or lower.startswith("gdrive:")
                        or "amazonaws.com" in lower
                        or lower.startswith("dropbox:")
                        or lower.startswith("onedrive:")
                    )

                def is_local_path(p: str) -> bool:
                    if not p:
                        return False
                    return bool(re.match(r"^[A-Za-z]:\\|^/|^file://|^~/", p))

                if source_filter == "local":
                    formatted_results = [
                        r for r in formatted_results if is_local_path(r.get("path", ""))
                    ]
                elif source_filter == "cloud":
                    formatted_results = [
                        r for r in formatted_results if is_cloud_path(r.get("path", ""))
                    ]
                elif source_filter == "hybrid":
                    formatted_results = [
                        r
                        for r in formatted_results
                        if (
                            not is_local_path(r.get("path", ""))
                            and not is_cloud_path(r.get("path", ""))
                        )
                    ]

            # Apply sorting
            formatted_results = apply_sort(formatted_results, sort_by)

            # Merge person results (highest priority) with other results
            if person_results:
                seen_paths = set()
                merged = []
                # Add person matches first (score 2.0)
                for r in person_results:
                    path = r.get("path")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        merged.append(r)
                # Add other results (avoiding duplicates)
                for r in formatted_results:
                    path = r.get("path")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        merged.append(r)
                formatted_results = merged

            # Include matches from auxiliary feature DBs (notes/tags/locations/people tags).
            try:
                aux_paths = _aux_search_paths(query)
                if aux_paths:
                    seen = {r.get("path") for r in formatted_results if r.get("path")}
                    for p in sorted(aux_paths):
                        if p in seen:
                            continue
                        formatted_results.append(
                            {
                                "path": p,
                                "filename": os.path.basename(p),
                                "score": 1.0,
                                "metadata": {},
                                "matchExplanation": "Matched via notes/tags/locations/people",
                            }
                        )
                        seen.add(p)
            except Exception:
                pass

            # Apply Pagination Slicing
            count = len(formatted_results)
            paginated = formatted_results[offset : offset + limit]

            return {
                "count": count,
                "results": paginated,
                "matched_person": person_to_search if person_results else None,
            }

        # 3. Hybrid Search (Metadata + Semantic with weighted scoring)
        if mode == "hybrid":
            # A. Get Metadata Results (All)
            metadata_results = []
            try:
                if any(op in query for op in ["=", ">", "<", "LIKE"]):
                    metadata_results = photo_search_engine.query_engine.search(query)
                else:
                    safe_query = query.replace("'", "''")
                    metadata_results = photo_search_engine.query_engine.search(
                        f"file.path LIKE '%{safe_query}%'"
                    )
            except Exception as e:
                print(f"Metadata search error in hybrid: {e}")

            # B. Get Semantic Results (Top N = limit + offset)
            # We need deep fetch to ensure correct global ranking after merge
            semantic_limit = limit + offset
            semantic_response = await search_semantic(query, semantic_limit, offset=0)
            semantic_results = semantic_response["results"]

            # C. Normalize semantic scores
            if semantic_results:
                max_score = max(r["score"] for r in semantic_results)
                min_score = min(r["score"] for r in semantic_results)
                score_range = max_score - min_score if max_score != min_score else 1.0

                for r in semantic_results:
                    r["normalized_score"] = (r["score"] - min_score) / score_range

            # D. Enhanced Merge Logic with Intent Detection
            # Note: Default weights are determined by get_weights_from_intent() below

            # Get intent-based weights using the intent detector
            intent_result = intent_detector.detect_intent(query)

            # Map intent to weights
            def get_weights_from_intent(primary_intent):
                """Get metadata/semantic weights based on primary intent"""
                # Metadata-heavy intents
                if primary_intent in ["camera", "date", "technical"]:
                    return 0.7, 0.3
                # Semantic-heavy intents
                elif primary_intent in [
                    "people",
                    "object",
                    "scene",
                    "event",
                    "emotion",
                    "activity",
                ]:
                    return 0.4, 0.6
                # Balanced intents
                elif primary_intent in ["location", "color"]:
                    return 0.5, 0.5
                # Default balanced
                else:
                    return 0.6, 0.4

            intent_metadata_weight, intent_semantic_weight = get_weights_from_intent(
                intent_result["primary_intent"]
            )

            seen_paths = set()
            hybrid_results = []

            for r in metadata_results:
                path = r.get("file_path", r.get("path"))
                seen_paths.add(path)
                semantic_match = next(
                    (s for s in semantic_results if s["path"] == path), None
                )

                if semantic_match:
                    # Both sources available - use intent-based weights
                    combined_score = (intent_metadata_weight * 1.0) + (
                        intent_semantic_weight
                        * semantic_match.get("normalized_score", 0.5)
                    )
                else:
                    # Only metadata available
                    combined_score = intent_metadata_weight * 0.8

                hybrid_results.append(
                    {
                        "path": path,
                        "filename": os.path.basename(path),
                        "score": round(combined_score, 3),
                        "metadata": r.get("metadata", {}),
                        "source": "both" if semantic_match else "metadata",
                        "intent": "metadata" if metadata_results else "semantic",
                    }
                )

            for r in semantic_results:
                if r["path"] not in seen_paths:
                    seen_paths.add(r["path"])
                    hybrid_results.append(
                        {
                            "path": r["path"],
                            "filename": r["filename"],
                            "score": round(
                                intent_semantic_weight
                                * r.get("normalized_score", r["score"]),
                                3,
                            ),
                            "metadata": r.get("metadata", {}),
                            "source": "semantic",
                            "intent": "semantic",
                        }
                    )

            # Sort by score descending
            hybrid_results.sort(key=lambda x: x["score"], reverse=True)

            # Apply type filter
            if type_filter == "photos":
                hybrid_results = [
                    r for r in hybrid_results if not is_video_file(r.get("path", ""))
                ]
            elif type_filter == "videos":
                hybrid_results = [
                    r for r in hybrid_results if is_video_file(r.get("path", ""))
                ]

            if tagged_paths is not None:
                hybrid_results = [
                    r for r in hybrid_results if r.get("path") in tagged_paths
                ]

            # Apply person filter
            if person_paths is not None:
                hybrid_results = [
                    r for r in hybrid_results if r.get("path") in person_paths
                ]

            # Apply favorites filter
            if favorites_filter == "favorites_only":
                hybrid_results = [
                    r
                    for r in hybrid_results
                    if photo_search_engine.is_favorite(r.get("path", ""))
                ]

            # Apply date filter (filesystem.created)
            hybrid_results = apply_date_filter(hybrid_results, date_from, date_to)
            # Apply source filter (local/cloud/hybrid)
            if source_filter != "all":

                def is_cloud_path(p: str) -> bool:
                    if not p:
                        return False
                    lower = p.lower()
                    return (
                        lower.startswith("http://")
                        or lower.startswith("https://")
                        or lower.startswith("s3://")
                        or lower.startswith("cloud:")
                        or lower.startswith("gdrive:")
                        or "amazonaws.com" in lower
                        or lower.startswith("dropbox:")
                        or lower.startswith("onedrive:")
                    )

                def is_local_path(p: str) -> bool:
                    if not p:
                        return False
                    return bool(re.match(r"^[A-Za-z]:\\|^/|^file://|^~/", p))

                if source_filter == "local":
                    hybrid_results = [
                        r for r in hybrid_results if is_local_path(r.get("path", ""))
                    ]
                elif source_filter == "cloud":
                    hybrid_results = [
                        r for r in hybrid_results if is_cloud_path(r.get("path", ""))
                    ]
                elif source_filter == "hybrid":
                    hybrid_results = [
                        r
                        for r in hybrid_results
                        if (
                            not is_local_path(r.get("path", ""))
                            and not is_cloud_path(r.get("path", ""))
                        )
                    ]

            # Merge person results (highest priority) with other results
            if person_results:
                seen_paths = set()
                merged = []
                # Add person matches first (score 2.0)
                for r in person_results:
                    path = r.get("path")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        merged.append(r)
                # Add other results (avoiding duplicates)
                for r in hybrid_results:
                    path = r.get("path")
                    if path not in seen_paths:
                        seen_paths.add(path)
                        merged.append(r)
                hybrid_results = merged

            # Apply Pagination Slicing
            count = len(hybrid_results)
            paginated_raw = hybrid_results[offset : offset + limit]

            # Format results with match explanations
            paginated = []
            for r in paginated_raw:
                result_item = {
                    "path": r["path"],
                    "filename": r["filename"],
                    "score": r["score"],
                    "metadata": r.get("metadata", {}),
                    "source": r.get("source", "hybrid"),
                    "intent": r.get("intent", "balanced"),
                }

                # Generate hybrid match explanation with detailed breakdown
                if query.strip():
                    result_item["matchExplanation"] = generate_hybrid_match_explanation(
                        query, r, intent_metadata_weight, intent_semantic_weight
                    )

                paginated.append(result_item)

            # Log search to history if enabled
            if log_history:
                execution_time_ms = int(round((time.time() - start_time) * 1000))
                intent_result = intent_detector.detect_intent(query)
                saved_search_manager.log_search_history(
                    query=query,
                    mode=mode,
                    results_count=count,
                    intent=intent_result["primary_intent"],
                    execution_time_ms=execution_time_ms,
                    user_agent="api",
                    ip_address="localhost",
                )

                # Add structured logging for search operation
                try:
                    log_search_operation(
                        ps_logger,
                        query=query,
                        mode=mode,
                        results_count=count,
                        execution_time=execution_time_ms,
                    )
                except Exception as e:
                    print(f"Error logging search operation: {e}")

            return {
                "count": count,
                "results": paginated,
                "intent": {
                    "primary_intent": intent_result["primary_intent"],
                    "secondary_intents": intent_result["secondary_intents"],
                    "metadata_weight": intent_metadata_weight,
                    "semantic_weight": intent_semantic_weight,
                    "confidence": intent_result["confidence"],
                    "badges": intent_result["badges"],
                    "suggestions": intent_result["suggestions"],
                    "execution_time_ms": execution_time_ms,
                },
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
