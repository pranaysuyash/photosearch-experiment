"""
Face Recognition Onboarding API Router - Phase 9

Provides API endpoints for face recognition onboarding and user experience enhancements.

Features:
1. Onboarding flow management
2. Progress tracking and analytics
3. Contextual help system
4. Tutorial completion tracking
5. User feedback collection
6. Personalized guidance

Endpoints:
- Onboarding flow creation and management
- Step-by-step progress tracking
- Contextual help and guidance
- Tutorial system integration
- Feedback collection and analysis
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from server.config import settings
from server.api.deps import get_state
from server.core.state import AppState
from server.face_onboarding_service import FaceOnboardingService

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models


class OnboardingStartRequest(BaseModel):
    """Request to start onboarding flow"""

    user_id: str = Field(..., description="User identifier")
    personalization: Optional[Dict[str, Any]] = Field(None, description="User preferences and personalization")


class StepProgressRequest(BaseModel):
    """Request to track step progress"""

    user_id: str = Field(..., description="User identifier")
    step_id: str = Field(..., description="Step identifier")
    action: str = Field(..., description="Action taken (started, completed, skipped)")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional step data")


class ContextualHelpRequest(BaseModel):
    """Request for contextual help"""

    user_id: str = Field(..., description="User identifier")
    context: str = Field(..., description="Help context (face_detection_failed, low_confidence, etc.)")
    specific_issue: Optional[str] = Field(None, description="Specific issue description")


class OnboardingFeedbackRequest(BaseModel):
    """Request to provide onboarding feedback"""

    user_id: str = Field(..., description="User identifier")
    rating: Optional[int] = Field(None, description="Rating 1-5")
    comments: Optional[str] = Field(None, description="Feedback comments")
    suggestions: Optional[List[str]] = Field(None, description="Improvement suggestions")


class UserPreferencesRequest(BaseModel):
    """Request to update user preferences"""

    user_id: str = Field(..., description="User identifier")
    experience_level: str = Field(default="beginner", description="User experience level")
    preferred_pace: str = Field(default="normal", description="Preferred tutorial pace")
    show_advanced_features: bool = Field(default=False, description="Show advanced features")
    skip_basic_tutorials: bool = Field(default=False, description="Skip basic tutorials")
    enable_tooltips: bool = Field(default=True, description="Enable contextual tooltips")


# Helper function to get onboarding service
def get_onboarding_service(state: AppState) -> FaceOnboardingService:
    """Get face onboarding service instance"""
    if not hasattr(state, "_face_onboarding_service"):
        state._face_onboarding_service = FaceOnboardingService(db_path=settings.FACE_CLUSTERS_DB_PATH)
    return state._face_onboarding_service


def get_user_id_from_request(request: Request) -> str:
    """Extract user ID from request headers"""
    return request.headers.get("X-User-ID", "default_user")


# Onboarding Flow Management Endpoints


@router.post("/api/onboarding/create")
async def create_onboarding_flow(
    onboarding_request: OnboardingStartRequest, request: Request, state: AppState = Depends(get_state)
):
    """
    Create personalized onboarding flow for user.

    Creates a customized onboarding experience based on user preferences
    and experience level.
    """
    try:
        onboarding_service = get_onboarding_service(state)

        flow = onboarding_service.create_onboarding_flow(
            user_id=onboarding_request.user_id, personalization=onboarding_request.personalization
        )

        return {
            "success": True,
            "message": "Onboarding flow created successfully",
            "flow": {
                "flow_id": flow.flow_id,
                "user_id": flow.user_id,
                "status": flow.status.value,
                "current_step": flow.current_step,
                "progress_percentage": flow.progress_percentage,
                "total_steps": len(flow.steps),
                "steps": [
                    {
                        "step_id": step.step_id,
                        "step_type": step.step_type.value,
                        "title": step.title,
                        "description": step.description,
                        "required": step.required,
                        "estimated_time_minutes": step.estimated_time_minutes,
                        "prerequisites": step.prerequisites,
                        "content": step.content,
                    }
                    for step in flow.steps
                ],
                "personalization": flow.personalization,
            },
        }

    except Exception as e:
        logger.error(f"Create onboarding flow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/onboarding/start")
async def start_onboarding(user_id: str, request: Request, state: AppState = Depends(get_state)):
    """Start onboarding flow for user."""
    try:
        onboarding_service = get_onboarding_service(state)

        result = onboarding_service.start_onboarding(user_id)

        return {"success": True, **result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Start onboarding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/onboarding/status/{user_id}")
async def get_onboarding_status(user_id: str, request: Request, state: AppState = Depends(get_state)):
    """Get current onboarding status for user."""
    try:
        onboarding_service = get_onboarding_service(state)

        status = onboarding_service.get_onboarding_status(user_id)

        return {"success": True, "user_id": user_id, **status}

    except Exception as e:
        logger.error(f"Get onboarding status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Progress Tracking Endpoints


@router.post("/api/onboarding/progress")
async def track_step_progress(
    progress_request: StepProgressRequest, request: Request, state: AppState = Depends(get_state)
):
    """Track user progress through onboarding steps."""
    try:
        onboarding_service = get_onboarding_service(state)

        result = onboarding_service.track_step_progress(
            user_id=progress_request.user_id,
            step_id=progress_request.step_id,
            action=progress_request.action,
            data=progress_request.data,
        )

        return {"success": True, "message": "Progress tracked successfully", **result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Track step progress failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/onboarding/progress/{user_id}")
async def get_progress_analytics(user_id: str, request: Request, state: AppState = Depends(get_state)):
    """Get detailed progress analytics for user."""
    try:
        onboarding_service = get_onboarding_service(state)

        # Get onboarding status with detailed progress
        status = onboarding_service.get_onboarding_status(user_id)

        if status.get("status") == "not_started":
            return {
                "success": True,
                "user_id": user_id,
                "analytics": {"status": "not_started", "message": "User has not started onboarding"},
            }

        # Calculate analytics
        step_progress = status.get("step_progress", [])
        completed_steps = [s for s in step_progress if s["status"] == "completed"]
        total_time = sum(s.get("time_spent_seconds", 0) for s in step_progress)

        analytics = {
            "overall_progress": status.get("progress_percentage", 0),
            "current_step": status.get("current_step"),
            "total_steps": len(step_progress) if step_progress else 0,
            "completed_steps": len(completed_steps),
            "remaining_steps": len(step_progress) - len(completed_steps) if step_progress else 0,
            "total_time_spent_seconds": total_time,
            "average_time_per_step": total_time / len(completed_steps) if completed_steps else 0,
            "completion_rate": (len(completed_steps) / len(step_progress)) * 100 if step_progress else 0,
            "started_at": status.get("started_at"),
            "estimated_completion": None,  # Could calculate based on remaining steps and average time
        }

        return {"success": True, "user_id": user_id, "analytics": analytics, "step_details": step_progress}

    except Exception as e:
        logger.error(f"Get progress analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Contextual Help Endpoints


@router.post("/api/onboarding/help")
async def get_contextual_help(
    help_request: ContextualHelpRequest, request: Request, state: AppState = Depends(get_state)
):
    """Get contextual help based on user's current situation."""
    try:
        onboarding_service = get_onboarding_service(state)

        help_content = onboarding_service.provide_contextual_help(
            user_id=help_request.user_id, context=help_request.context, specific_issue=help_request.specific_issue
        )

        return {"success": True, "message": "Contextual help provided", **help_content}

    except Exception as e:
        logger.error(f"Get contextual help failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/onboarding/help/contexts")
async def get_help_contexts(request: Request, state: AppState = Depends(get_state)):
    """Get available help contexts and their descriptions."""
    try:
        help_contexts = {
            "face_detection_failed": {
                "title": "No Faces Detected",
                "description": "Help when face detection doesn't find any faces",
                "common_causes": ["Poor image quality", "Faces too small", "Extreme angles"],
            },
            "low_confidence": {
                "title": "Low Confidence Detection",
                "description": "Help when face detection has low confidence",
                "common_causes": ["Partial occlusion", "Poor lighting", "Blurry images"],
            },
            "clustering_confusion": {
                "title": "Understanding Face Clusters",
                "description": "Help understanding how face clustering works",
                "common_causes": ["First time using system", "Unexpected clustering results"],
            },
            "person_identification": {
                "title": "Identifying People",
                "description": "Help with naming and organizing people",
                "common_causes": ["Too many unknown clusters", "Duplicate people"],
            },
            "privacy_concerns": {
                "title": "Privacy and Data Protection",
                "description": "Help with privacy settings and data control",
                "common_causes": ["Privacy questions", "Data retention concerns"],
            },
        }

        return {"success": True, "help_contexts": help_contexts, "total_contexts": len(help_contexts)}

    except Exception as e:
        logger.error(f"Get help contexts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User Preferences and Personalization Endpoints


@router.put("/api/onboarding/preferences")
async def update_user_preferences(
    preferences_request: UserPreferencesRequest, request: Request, state: AppState = Depends(get_state)
):
    """Update user preferences for personalized onboarding."""
    try:
        onboarding_service = get_onboarding_service(state)

        # Update preferences in database
        with onboarding_service._get_privacy_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO onboarding_preferences
                (user_id, experience_level, preferred_pace, show_advanced_features,
                 skip_basic_tutorials, enable_tooltips, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    preferences_request.user_id,
                    preferences_request.experience_level,
                    preferences_request.preferred_pace,
                    preferences_request.show_advanced_features,
                    preferences_request.skip_basic_tutorials,
                    preferences_request.enable_tooltips,
                ),
            )
            conn.commit()

        return {
            "success": True,
            "message": "User preferences updated successfully",
            "preferences": {
                "experience_level": preferences_request.experience_level,
                "preferred_pace": preferences_request.preferred_pace,
                "show_advanced_features": preferences_request.show_advanced_features,
                "skip_basic_tutorials": preferences_request.skip_basic_tutorials,
                "enable_tooltips": preferences_request.enable_tooltips,
            },
            "updated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Update user preferences failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/onboarding/preferences/{user_id}")
async def get_user_preferences(user_id: str, request: Request, state: AppState = Depends(get_state)):
    """Get user preferences for onboarding personalization."""
    try:
        onboarding_service = get_onboarding_service(state)

        preferences = onboarding_service._get_user_preferences(user_id)

        return {"success": True, "user_id": user_id, "preferences": preferences}

    except Exception as e:
        logger.error(f"Get user preferences failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Feedback and Completion Endpoints


@router.post("/api/onboarding/feedback")
async def submit_onboarding_feedback(
    feedback_request: OnboardingFeedbackRequest, request: Request, state: AppState = Depends(get_state)
):
    """Submit feedback about the onboarding experience."""
    try:
        onboarding_service = get_onboarding_service(state)

        feedback_data = {
            "rating": feedback_request.rating,
            "comments": feedback_request.comments,
            "suggestions": feedback_request.suggestions,
            "submitted_at": datetime.now().isoformat(),
        }

        # Complete onboarding with feedback
        result = onboarding_service.complete_onboarding(user_id=feedback_request.user_id, feedback=feedback_data)

        return {"success": True, "message": "Feedback submitted successfully", "feedback_data": feedback_data, **result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Submit onboarding feedback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/onboarding/complete/{user_id}")
async def complete_onboarding(user_id: str, request: Request, state: AppState = Depends(get_state)):
    """Complete onboarding flow for user."""
    try:
        onboarding_service = get_onboarding_service(state)

        result = onboarding_service.complete_onboarding(user_id)

        return {"success": True, **result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Complete onboarding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics and Reporting Endpoints


@router.get("/api/onboarding/analytics/overview")
async def get_onboarding_analytics_overview(request: Request, days: int = 30, state: AppState = Depends(get_state)):
    """Get overall onboarding analytics and metrics."""
    try:
        onboarding_service = get_onboarding_service(state)

        with onboarding_service._get_privacy_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get completion statistics
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_flows,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_flows,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_flows,
                    SUM(CASE WHEN status = 'not_started' THEN 1 ELSE 0 END) as not_started_flows,
                    AVG(progress_percentage) as avg_progress
                FROM onboarding_flows
                WHERE created_at > datetime('now', '-{} days')
            """.format(days)
            )

            flow_stats = dict(cursor.fetchone())

            # Get step completion rates
            cursor.execute(
                """
                SELECT
                    step_id,
                    COUNT(*) as attempts,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completions,
                    AVG(time_spent_seconds) as avg_time_seconds
                FROM onboarding_progress
                WHERE started_at > datetime('now', '-{} days')
                GROUP BY step_id
                ORDER BY attempts DESC
            """.format(days)
            )

            step_stats = [dict(row) for row in cursor.fetchall()]

            # Calculate completion rates
            for step in step_stats:
                step["completion_rate"] = (step["completions"] / step["attempts"]) * 100 if step["attempts"] > 0 else 0

            # Get feedback statistics
            cursor.execute(
                """
                SELECT
                    AVG(feedback_rating) as avg_rating,
                    COUNT(*) as total_feedback,
                    COUNT(CASE WHEN feedback_rating >= 4 THEN 1 END) as positive_feedback
                FROM tutorial_completions
                WHERE tutorial_type = 'face_recognition_onboarding'
                AND completed_at > datetime('now', '-{} days')
            """.format(days)
            )

            feedback_stats = dict(cursor.fetchone())

        analytics = {
            "period_days": days,
            "flow_statistics": flow_stats,
            "step_statistics": step_stats,
            "feedback_statistics": feedback_stats,
            "completion_rate": (flow_stats["completed_flows"] / flow_stats["total_flows"]) * 100
            if flow_stats["total_flows"] > 0
            else 0,
            "generated_at": datetime.now().isoformat(),
        }

        return {"success": True, "analytics": analytics}

    except Exception as e:
        logger.error(f"Get onboarding analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/onboarding/tutorials/available")
async def get_available_tutorials(request: Request, state: AppState = Depends(get_state)):
    """Get list of available tutorials and their completion status."""
    try:
        tutorials = {
            "face_recognition_basics": {
                "title": "Face Recognition Basics",
                "description": "Learn the fundamentals of face recognition",
                "estimated_time_minutes": 5,
                "difficulty": "beginner",
                "topics": ["Face detection", "Person identification", "Basic organization"],
            },
            "advanced_search": {
                "title": "Advanced Search Techniques",
                "description": "Master natural language and attribute-based search",
                "estimated_time_minutes": 8,
                "difficulty": "intermediate",
                "topics": ["Natural language queries", "Facial attributes", "Complex filters"],
            },
            "privacy_controls": {
                "title": "Privacy and Data Control",
                "description": "Understand and configure privacy settings",
                "estimated_time_minutes": 6,
                "difficulty": "beginner",
                "topics": ["Privacy levels", "Consent management", "Data export"],
            },
            "professional_workflows": {
                "title": "Professional Workflows",
                "description": "Advanced features for professional photographers",
                "estimated_time_minutes": 12,
                "difficulty": "advanced",
                "topics": ["Batch processing", "Export options", "Performance optimization"],
            },
        }

        return {"success": True, "tutorials": tutorials, "total_tutorials": len(tutorials)}

    except Exception as e:
        logger.error(f"Get available tutorials failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import required modules
import sqlite3
