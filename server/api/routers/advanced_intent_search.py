from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.locations_db import get_locations_db
from server.models.schemas.intent import IntentSearchParams


router = APIRouter()


@router.post("/search/intent")
async def search_with_intent(params: IntentSearchParams):
    """
    Advanced search with intent recognition and context-aware processing.

    This endpoint performs search considering the user's intent and provides
    enhanced results based on contextual information.
    """
    try:
        import time
        start_time = time.time()

        from server import main as main_module

        # Detect intent from query
        intent_result = main_module.intent_detector.detect_intent(params.query)

        # Apply intent-specific search logic
        results: List[Dict[str, Any]] = []

        # For people intent, search using face recognition if available
        if intent_result["primary_intent"] == "people":
            # Check if person name is in query
            people_results: List[Dict[str, Any]] = []
            try:
                from src.face_clustering import FACE_LIBRARIES_AVAILABLE

                if FACE_LIBRARIES_AVAILABLE:
                    # Search for faces with names matching query
                    # This is a simplified implementation
                    # In a full implementation, this would query the face clustering database
                    pass
            except ImportError:
                pass

        # For location intent, search using location data
        elif intent_result["primary_intent"] == "location":
            # Search for photos with matching location info
            locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
            location_results = locations_db.get_photos_by_place(params.query)
            # Add to results with location context

        # For date intent, enhance date filtering
        elif intent_result["primary_intent"] == "date":
            # Parse date expressions from query and apply to search
            base_query = params.query
            # Extract date ranges from query if possible
            # This would be enhanced with NLP for date parsing

        # For events, combine multiple filters
        elif intent_result["primary_intent"] == "event":
            # Events often involve people, locations, and specific activities
            # Apply multi-faceted search
            pass

        # Perform base search depending on intent
        # Use hybrid search with intent-based weightings
        metadata_weight, semantic_weight = 0.5, 0.5

        if intent_result["primary_intent"] in ["camera", "date", "technical"]:
            metadata_weight, semantic_weight = 0.8, 0.2
        elif intent_result["primary_intent"] in [
            "people",
            "object",
            "scene",
            "event",
            "emotion",
            "activity",
        ]:
            metadata_weight, semantic_weight = 0.2, 0.8
        elif intent_result["primary_intent"] in ["location", "color"]:
            metadata_weight, semantic_weight = 0.6, 0.4

        # Perform hybrid search with appropriate weights
        # This would use the existing hybrid search logic with intent weights

        # Fallback to regular search if no specific intent processing
        search_results_response = await main_module.search_photos(
            query=params.query,
            limit=params.limit,
            offset=params.offset,
            mode="hybrid",
            sort_by="date_desc",
        )

        search_results = search_results_response["results"]

        # Add intent information to results
        response = {
            "query": params.query,
            "intent": intent_result,
            "count": len(search_results),
            "results": search_results,
            "processing_time": time.time() - start_time,
            "filters_applied": params.filters or {},
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/refine")
async def refine_search(query: str, previous_results: List[Dict], refinement: str):
    """
    Refine search results based on user feedback.

    This endpoint allows users to refine existing search results with
    additional criteria or corrections.
    """
    try:
        from server import main as main_module

        # Detect intent in refinement query
        intent_result = main_module.intent_detector.detect_intent(refinement)

        # Apply refinement to previous results
        # For example, if refinement is "only show photos from 2023", filter by date
        # If refinement is "only beach photos", apply scene detection filter
        refined_results = previous_results[:]  # In a real implementation, this would apply filters
        suggestions = main_module.intent_detector.get_search_suggestions(f"{query} {refinement}")

        return {
            "original_query": query,
            "refinement": refinement,
            "intent": intent_result,
            "count": len(refined_results),
            "results": refined_results,
            "suggestions": suggestions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
