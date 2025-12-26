from fastapi import APIRouter, HTTPException, Depends
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/api/intent/detect")
async def detect_intent_api(query: str, state: AppState = Depends(get_state)):
    """
    Detect user intent from search query for auto-mode switching.
    """
    try:
        if not query.strip():
            return {
                "primary_intent": "general",
                "secondary_intents": [],
                "confidence": 0.5,
                "badges": [],
                "suggestions": [],
            }

        intent_result = state.intent_detector.detect_intent(query)
        return intent_result
    except Exception as e:
        print(f"Intent detection error: {e}")
        return {
            "primary_intent": "general",
            "secondary_intents": [],
            "confidence": 0.5,
            "badges": [],
            "suggestions": [],
        }


@router.get("/intent/detect")
async def detect_intent_v2(query: str, state: AppState = Depends(get_state)):
    """
    Detect search intent from a query.

    Args:
        query: User search query string

    Returns:
        Intent detection results including primary intent, secondary intents,
        confidence scores, suggestions, and badges
    """
    try:
        if not query or not query.strip():
            return {
                "intent": "generic",
                "confidence": 0.0,
                "suggestions": [],
                "badges": [],
            }

        result = state.intent_detector.detect_intent(query)
        return {
            "intent": result["primary_intent"],
            "confidence": result["confidence"],
            "secondary_intents": result["secondary_intents"],
            "suggestions": result["suggestions"],
            "badges": result["badges"],
            "description": result["description"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intent/suggestions")
async def get_search_suggestions(query: str, limit: int = 3, state: AppState = Depends(get_state)):
    """
    Get search suggestions based on detected intent.

    Args:
        query: User search query string
        limit: Maximum number of suggestions to return

    Returns:
        List of suggested search queries
    """
    try:
        suggestions = state.intent_detector.get_search_suggestions(query)
        return {"suggestions": suggestions[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intent/badges")
async def get_search_badges(query: str, state: AppState = Depends(get_state)):
    """
    Get intent badges for UI display.

    Args:
        query: User search query string

    Returns:
        List of intent badges with labels and icons
    """
    try:
        badges = state.intent_detector.get_search_badges(query)
        return {"badges": badges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intent/all")
async def get_all_intents(state: AppState = Depends(get_state)):
    """
    Get all supported intents with descriptions.

    Returns:
        Dictionary of all supported intents
    """
    try:
        return state.intent_detector.get_all_intents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
