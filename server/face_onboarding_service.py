"""
Face Recognition Onboarding Service - Phase 9

Provides guided onboarding experience for new users to understand
and configure face recognition features effectively.

Features:
1. Interactive setup wizard for face recognition
2. Progressive disclosure of advanced features
3. Tutorial system with contextual help
4. Progress tracking and completion metrics
5. Personalized onboarding based on user preferences
6. Quality feedback and improvement suggestions

Onboarding Flow:
1. Welcome and privacy consent
2. First photo scan demonstration
3. Person identification tutorial
4. Advanced features introduction
5. Privacy settings configuration
6. Completion and next steps

Usage:
    onboarding = FaceOnboardingService(db_path)
    flow = onboarding.create_onboarding_flow(user_id)
    onboarding.track_progress(user_id, step_id)
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class OnboardingStep(Enum):
    """Onboarding step types"""

    WELCOME = "welcome"
    PRIVACY_CONSENT = "privacy_consent"
    FIRST_SCAN = "first_scan"
    PERSON_IDENTIFICATION = "person_identification"
    ADVANCED_FEATURES = "advanced_features"
    PRIVACY_SETTINGS = "privacy_settings"
    COMPLETION = "completion"


class OnboardingStatus(Enum):
    """Onboarding completion status"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class OnboardingStepData:
    """Individual onboarding step information"""

    step_id: str
    step_type: OnboardingStep
    title: str
    description: str
    content: Dict[str, Any]
    required: bool
    estimated_time_minutes: int
    prerequisites: List[str]
    completion_criteria: Dict[str, Any]


@dataclass
class OnboardingFlow:
    """Complete onboarding flow for user"""

    flow_id: str
    user_id: str
    steps: List[OnboardingStepData]
    current_step: Optional[str]
    status: OnboardingStatus
    progress_percentage: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    personalization: Dict[str, Any]


@dataclass
class OnboardingProgress:
    """User progress tracking"""

    user_id: str
    step_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    time_spent_seconds: int
    interactions: List[Dict[str, Any]]
    feedback: Optional[Dict[str, Any]]


class FaceOnboardingService:
    """Face recognition onboarding and tutorial service"""

    def __init__(self, db_path: str):
        """
        Initialize face onboarding service.

        Args:
            db_path: Database path for onboarding data
        """
        self.db_path = Path(db_path)
        self._init_onboarding_database()

        # Default onboarding configuration
        self.onboarding_config = {
            "enable_personalization": True,
            "allow_step_skipping": True,
            "show_progress_indicators": True,
            "provide_contextual_help": True,
            "track_detailed_analytics": True,
            "adaptive_pacing": True,
        }

        logger.info("FaceOnboardingService initialized")

    def _init_onboarding_database(self):
        """Initialize onboarding database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Onboarding flows
            conn.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_flows (
                    flow_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    progress_percentage REAL DEFAULT 0,
                    personalization TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Step progress tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_progress (
                    progress_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    flow_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    time_spent_seconds INTEGER DEFAULT 0,
                    interactions TEXT,
                    feedback TEXT,
                    FOREIGN KEY (flow_id) REFERENCES onboarding_flows(flow_id)
                )
            """)

            # User preferences and personalization
            conn.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_preferences (
                    user_id TEXT PRIMARY KEY,
                    experience_level TEXT DEFAULT 'beginner',
                    preferred_pace TEXT DEFAULT 'normal',
                    show_advanced_features BOOLEAN DEFAULT 0,
                    skip_basic_tutorials BOOLEAN DEFAULT 0,
                    enable_tooltips BOOLEAN DEFAULT 1,
                    preferences_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tutorial completion tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tutorial_completions (
                    completion_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    tutorial_type TEXT NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completion_score REAL,
                    feedback_rating INTEGER,
                    feedback_comments TEXT
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_onboarding_user ON onboarding_flows(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_progress_user_step ON onboarding_progress(user_id, step_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tutorial_user_type ON tutorial_completions(user_id, tutorial_type)"
            )

    def create_onboarding_flow(self, user_id: str, personalization: Optional[Dict[str, Any]] = None) -> OnboardingFlow:
        """
        Create personalized onboarding flow for user.

        Args:
            user_id: User identifier
            personalization: User preferences and personalization data

        Returns:
            Complete onboarding flow with personalized steps
        """
        try:
            flow_id = str(uuid.uuid4())

            # Get user preferences
            user_prefs = self._get_user_preferences(user_id)
            if personalization:
                user_prefs.update(personalization)

            # Create personalized steps
            steps = self._create_personalized_steps(user_prefs)

            # Create flow record
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """
                    INSERT INTO onboarding_flows
                    (flow_id, user_id, status, current_step, personalization, started_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        flow_id,
                        user_id,
                        OnboardingStatus.NOT_STARTED.value,
                        steps[0].step_id if steps else None,
                        json.dumps(user_prefs),
                    ),
                )

            flow = OnboardingFlow(
                flow_id=flow_id,
                user_id=user_id,
                steps=steps,
                current_step=steps[0].step_id if steps else None,
                status=OnboardingStatus.NOT_STARTED,
                progress_percentage=0.0,
                started_at=None,
                completed_at=None,
                personalization=user_prefs,
            )

            logger.info(f"Onboarding flow created for user {user_id}: {flow_id}")
            return flow

        except Exception as e:
            logger.error(f"Failed to create onboarding flow: {e}")
            raise

    def _create_personalized_steps(self, user_prefs: Dict[str, Any]) -> List[OnboardingStepData]:
        """Create personalized onboarding steps based on user preferences"""

        experience_level = user_prefs.get("experience_level", "beginner")
        show_advanced = user_prefs.get("show_advanced_features", False)
        skip_basic = user_prefs.get("skip_basic_tutorials", False)

        steps = []

        # Step 1: Welcome
        if not skip_basic:
            steps.append(
                OnboardingStepData(
                    step_id="welcome",
                    step_type=OnboardingStep.WELCOME,
                    title="Welcome to Face Recognition",
                    description="Discover how we help you organize photos by the people in them",
                    content={
                        "welcome_message": "We're excited to help you organize your photo collection using advanced face recognition technology.",
                        "key_benefits": [
                            "Automatically find photos of specific people",
                            "Organize thousands of photos in minutes",
                            "Privacy-first processing on your device",
                            "Professional-grade accuracy and speed",
                        ],
                        "estimated_setup_time": "5-10 minutes",
                        "privacy_highlight": "All face processing happens locally on your device - we never see your photos.",
                    },
                    required=True,
                    estimated_time_minutes=2,
                    prerequisites=[],
                    completion_criteria={"action": "continue_clicked"},
                )
            )

        # Step 2: Privacy Consent
        steps.append(
            OnboardingStepData(
                step_id="privacy_consent",
                step_type=OnboardingStep.PRIVACY_CONSENT,
                title="Privacy and Consent",
                description="Configure your privacy preferences for face recognition",
                content={
                    "privacy_explanation": "We respect your privacy and give you full control over face recognition processing.",
                    "consent_types": [
                        {
                            "type": "face_recognition",
                            "title": "Face Recognition",
                            "description": "We detect and recognize faces in your photos",
                            "required": True,
                        },
                        {
                            "type": "facial_attributes",
                            "title": "Facial Attributes",
                            "description": "We analyze age, emotion, and other attributes",
                            "required": False,
                        },
                        {
                            "type": "face_clustering",
                            "title": "Face Clustering",
                            "description": "We group similar faces to identify people",
                            "required": True,
                        },
                    ],
                    "privacy_levels": [
                        {
                            "level": "full",
                            "title": "Full Processing",
                            "description": "All features enabled for best experience",
                        },
                        {
                            "level": "anonymous",
                            "title": "Anonymous Only",
                            "description": "Face detection without personal identification",
                        },
                        {"level": "minimal", "title": "Minimal Processing", "description": "Basic detection only"},
                    ],
                },
                required=True,
                estimated_time_minutes=3,
                prerequisites=["welcome"] if not skip_basic else [],
                completion_criteria={"consents_granted": ["face_recognition", "face_clustering"]},
            )
        )

        # Step 3: First Scan Demonstration
        steps.append(
            OnboardingStepData(
                step_id="first_scan",
                step_type=OnboardingStep.FIRST_SCAN,
                title="Your First Face Scan",
                description="Watch as we analyze your photos and detect faces",
                content={
                    "scan_explanation": "We'll scan a small sample of your photos to demonstrate face detection.",
                    "what_to_expect": [
                        "We'll process 10-20 sample photos",
                        "You'll see faces being detected in real-time",
                        "We'll show you the quality and confidence scores",
                        "This helps you understand how the system works",
                    ],
                    "demo_features": [
                        "Real-time face detection",
                        "Quality assessment",
                        "Confidence scoring",
                        "Bounding box visualization",
                    ],
                    "sample_size": 20,
                    "show_progress": True,
                    "interactive_demo": True,
                },
                required=True,
                estimated_time_minutes=3,
                prerequisites=["privacy_consent"],
                completion_criteria={"demo_completed": True, "faces_detected": ">0"},
            )
        )

        # Step 4: Person Identification Tutorial
        steps.append(
            OnboardingStepData(
                step_id="person_identification",
                step_type=OnboardingStep.PERSON_IDENTIFICATION,
                title="Identifying People",
                description="Learn how to name and organize the people in your photos",
                content={
                    "tutorial_explanation": "Now we'll show you how to identify and name the people we detected.",
                    "key_concepts": [
                        "Face clusters group similar faces together",
                        "You can name clusters to identify people",
                        "The system learns and improves over time",
                        "You can merge, split, and organize clusters",
                    ],
                    "interactive_tasks": [
                        {
                            "task": "name_person",
                            "description": "Give a name to your first person cluster",
                            "required": True,
                        },
                        {
                            "task": "review_suggestions",
                            "description": "Review and confirm face suggestions",
                            "required": False,
                        },
                        {"task": "merge_clusters", "description": "Merge duplicate person clusters", "required": False},
                    ],
                    "tips": [
                        "Start with people who appear most frequently",
                        "Use clear, recognizable names",
                        "Review suggestions carefully for accuracy",
                        "You can always make changes later",
                    ],
                },
                required=True,
                estimated_time_minutes=5,
                prerequisites=["first_scan"],
                completion_criteria={"people_named": ">=1", "tasks_completed": ">=1"},
            )
        )

        # Step 5: Advanced Features (conditional)
        if show_advanced or experience_level == "advanced":
            steps.append(
                OnboardingStepData(
                    step_id="advanced_features",
                    step_type=OnboardingStep.ADVANCED_FEATURES,
                    title="Advanced Features",
                    description="Explore powerful features for professional workflows",
                    content={
                        "advanced_features": [
                            {
                                "feature": "natural_language_search",
                                "title": "Natural Language Search",
                                "description": "Search using phrases like 'happy family photos from 2023'",
                                "demo_available": True,
                            },
                            {
                                "feature": "facial_attributes",
                                "title": "Facial Attribute Analysis",
                                "description": "Search by age, emotion, pose, and quality",
                                "demo_available": True,
                            },
                            {
                                "feature": "video_processing",
                                "title": "Video Face Tracking",
                                "description": "Track faces across video frames with timeline analysis",
                                "demo_available": False,
                            },
                            {
                                "feature": "smart_albums",
                                "title": "Smart Albums",
                                "description": "Automatically created albums based on face analysis",
                                "demo_available": True,
                            },
                        ],
                        "professional_tools": [
                            "Batch processing for large collections",
                            "Export capabilities with metadata",
                            "Performance optimization settings",
                            "Advanced privacy controls",
                        ],
                        "enable_features": True,
                    },
                    required=False,
                    estimated_time_minutes=4,
                    prerequisites=["person_identification"],
                    completion_criteria={"features_explored": ">=2"},
                )
            )

        # Step 6: Privacy Settings
        steps.append(
            OnboardingStepData(
                step_id="privacy_settings",
                step_type=OnboardingStep.PRIVACY_SETTINGS,
                title="Privacy Settings",
                description="Fine-tune your privacy preferences and data retention",
                content={
                    "privacy_controls": [
                        {
                            "setting": "data_retention",
                            "title": "Data Retention",
                            "description": "How long to keep face recognition data",
                            "options": ["1 year", "2 years", "5 years", "7 years", "Indefinite"],
                            "default": "7 years",
                            "required": True,
                        },
                        {
                            "setting": "sharing_controls",
                            "title": "Sharing Controls",
                            "description": "Control how face data is handled in shared photos",
                            "options": ["Always blur private faces", "Ask before sharing", "No restrictions"],
                            "default": "Ask before sharing",
                            "required": False,
                        },
                        {
                            "setting": "audit_logging",
                            "title": "Audit Logging",
                            "description": "Track all face recognition operations for transparency",
                            "options": ["Enabled", "Disabled"],
                            "default": "Enabled",
                            "required": False,
                        },
                    ],
                    "gdpr_compliance": {
                        "data_portability": "Export your data anytime",
                        "right_to_erasure": "Delete all face data on request",
                        "consent_withdrawal": "Withdraw consent and stop processing",
                    },
                },
                required=True,
                estimated_time_minutes=3,
                prerequisites=["person_identification"],
                completion_criteria={"settings_configured": True},
            )
        )

        # Step 7: Completion
        steps.append(
            OnboardingStepData(
                step_id="completion",
                step_type=OnboardingStep.COMPLETION,
                title="Setup Complete!",
                description="You're ready to start using face recognition",
                content={
                    "completion_message": "Congratulations! You've successfully set up face recognition.",
                    "next_steps": [
                        {
                            "action": "full_scan",
                            "title": "Scan Your Full Collection",
                            "description": "Process all your photos for complete face recognition",
                            "estimated_time": "Varies by collection size",
                        },
                        {
                            "action": "explore_search",
                            "title": "Try Advanced Search",
                            "description": "Use natural language to find specific photos",
                            "estimated_time": "2 minutes",
                        },
                        {
                            "action": "organize_people",
                            "title": "Organize Your People",
                            "description": "Review and refine person identifications",
                            "estimated_time": "10-15 minutes",
                        },
                    ],
                    "help_resources": [
                        {"type": "documentation", "title": "User Guide", "url": "/help/face-recognition"},
                        {"type": "video", "title": "Video Tutorials", "url": "/help/videos"},
                        {"type": "support", "title": "Contact Support", "url": "/support"},
                    ],
                    "feedback_request": True,
                },
                required=True,
                estimated_time_minutes=2,
                prerequisites=["privacy_settings"],
                completion_criteria={"feedback_provided": False},  # Optional
            )
        )

        return steps

    def start_onboarding(self, user_id: str) -> Dict[str, Any]:
        """Start onboarding flow for user"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Update flow status
                conn.execute(
                    """
                    UPDATE onboarding_flows
                    SET status = ?, started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND status = ?
                """,
                    (OnboardingStatus.IN_PROGRESS.value, user_id, OnboardingStatus.NOT_STARTED.value),
                )

                if conn.total_changes == 0:
                    raise ValueError("No onboarding flow found or already started")

            return {
                "status": "started",
                "message": "Onboarding flow started successfully",
                "started_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to start onboarding: {e}")
            raise

    def track_step_progress(
        self, user_id: str, step_id: str, action: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track user progress through onboarding steps"""
        try:
            progress_id = str(uuid.uuid4())

            with sqlite3.connect(str(self.db_path)) as conn:
                # Get current flow
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT flow_id, current_step FROM onboarding_flows
                    WHERE user_id = ? AND status = ?
                """,
                    (user_id, OnboardingStatus.IN_PROGRESS.value),
                )

                row = cursor.fetchone()
                if not row:
                    raise ValueError("No active onboarding flow found")

                flow_id, current_step = row

                # Record progress
                conn.execute(
                    """
                    INSERT INTO onboarding_progress
                    (progress_id, user_id, flow_id, step_id, status, interactions)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (progress_id, user_id, flow_id, step_id, action, json.dumps(data or {})),
                )

                # Update current step if progressing
                if action == "completed" and step_id == current_step:
                    next_step = self._get_next_step(flow_id, step_id)
                    if next_step:
                        conn.execute(
                            """
                            UPDATE onboarding_flows
                            SET current_step = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE flow_id = ?
                        """,
                            (next_step, flow_id),
                        )
                    else:
                        # Onboarding completed
                        conn.execute(
                            """
                            UPDATE onboarding_flows
                            SET status = ?, completed_at = CURRENT_TIMESTAMP,
                                progress_percentage = 100, updated_at = CURRENT_TIMESTAMP
                            WHERE flow_id = ?
                        """,
                            (OnboardingStatus.COMPLETED.value, flow_id),
                        )

                # Calculate progress percentage
                progress_percentage = self._calculate_progress(flow_id)
                conn.execute(
                    """
                    UPDATE onboarding_flows
                    SET progress_percentage = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE flow_id = ?
                """,
                    (progress_percentage, flow_id),
                )

            return {
                "status": "tracked",
                "progress_id": progress_id,
                "step_id": step_id,
                "action": action,
                "progress_percentage": progress_percentage,
            }

        except Exception as e:
            logger.error(f"Failed to track step progress: {e}")
            raise

    def get_onboarding_status(self, user_id: str) -> Dict[str, Any]:
        """Get current onboarding status for user"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get flow status
                cursor.execute(
                    """
                    SELECT flow_id, status, current_step, progress_percentage,
                           started_at, completed_at, personalization
                    FROM onboarding_flows
                    WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT 1
                """,
                    (user_id,),
                )

                flow_row = cursor.fetchone()
                if not flow_row:
                    return {"status": "not_started", "message": "No onboarding flow found for user"}

                # Get step progress
                cursor.execute(
                    """
                    SELECT step_id, status, completed_at, time_spent_seconds
                    FROM onboarding_progress
                    WHERE user_id = ? AND flow_id = ?
                    ORDER BY started_at
                """,
                    (user_id, flow_row["flow_id"]),
                )

                step_progress = [dict(row) for row in cursor.fetchall()]

                return {
                    "flow_id": flow_row["flow_id"],
                    "status": flow_row["status"],
                    "current_step": flow_row["current_step"],
                    "progress_percentage": flow_row["progress_percentage"],
                    "started_at": flow_row["started_at"],
                    "completed_at": flow_row["completed_at"],
                    "personalization": json.loads(flow_row["personalization"]) if flow_row["personalization"] else {},
                    "step_progress": step_progress,
                }

        except Exception as e:
            logger.error(f"Failed to get onboarding status: {e}")
            raise

    def provide_contextual_help(
        self, user_id: str, context: str, specific_issue: Optional[str] = None
    ) -> Dict[str, Any]:
        """Provide contextual help based on user's current situation"""
        try:
            help_content = {
                "face_detection_failed": {
                    "title": "No Faces Detected",
                    "explanation": "We couldn't find any faces in this photo. This might happen if:",
                    "reasons": [
                        "Faces are too small or blurry",
                        "Faces are partially obscured",
                        "Photo quality is too low",
                        "Faces are at extreme angles",
                    ],
                    "suggestions": [
                        "Try photos with clearer, larger faces",
                        "Ensure good lighting in photos",
                        "Use photos where faces are clearly visible",
                        "Check that the photo isn't corrupted",
                    ],
                    "next_steps": ["Try another photo", "Adjust quality settings", "Contact support"],
                },
                "low_confidence": {
                    "title": "Low Confidence Detection",
                    "explanation": "We detected faces but with lower confidence. This means:",
                    "reasons": [
                        "Face is partially obscured",
                        "Unusual lighting conditions",
                        "Face is at an angle",
                        "Photo resolution is low",
                    ],
                    "suggestions": [
                        "Review the detection manually",
                        "Use higher quality photos when possible",
                        "Confirm or reject the detection",
                        "The system will learn from your feedback",
                    ],
                    "next_steps": ["Review detection", "Provide feedback", "Continue with caution"],
                },
                "clustering_confusion": {
                    "title": "Understanding Face Clusters",
                    "explanation": "Face clusters group similar faces together. Here's how it works:",
                    "concepts": [
                        "Each cluster represents one person",
                        "Similar faces are automatically grouped",
                        "You can name clusters to identify people",
                        "Clusters can be merged, split, or reorganized",
                    ],
                    "actions": [
                        "Name your most frequent people first",
                        "Review cluster suggestions carefully",
                        "Merge clusters that are the same person",
                        "Split clusters that contain multiple people",
                    ],
                    "next_steps": ["Start naming people", "Review suggestions", "Organize clusters"],
                },
            }

            context_help = help_content.get(
                context,
                {
                    "title": "General Help",
                    "explanation": "We're here to help you with face recognition.",
                    "suggestions": ["Check the user guide", "Try the tutorial", "Contact support"],
                    "next_steps": ["Continue exploring", "Get more help"],
                },
            )

            # Add specific issue details if provided
            if specific_issue:
                context_help["specific_issue"] = specific_issue
                context_help["issue_guidance"] = self._get_issue_specific_guidance(specific_issue)

            return {
                "context": context,
                "help_content": context_help,
                "user_id": user_id,
                "provided_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to provide contextual help: {e}")
            raise

    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for personalization"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT experience_level, preferred_pace, show_advanced_features,
                           skip_basic_tutorials, enable_tooltips, preferences_json
                    FROM onboarding_preferences
                    WHERE user_id = ?
                """,
                    (user_id,),
                )

                row = cursor.fetchone()
                if row:
                    prefs = {
                        "experience_level": row[0],
                        "preferred_pace": row[1],
                        "show_advanced_features": bool(row[2]),
                        "skip_basic_tutorials": bool(row[3]),
                        "enable_tooltips": bool(row[4]),
                    }

                    if row[5]:
                        prefs.update(json.loads(row[5]))

                    return prefs

                # Default preferences for new users
                return {
                    "experience_level": "beginner",
                    "preferred_pace": "normal",
                    "show_advanced_features": False,
                    "skip_basic_tutorials": False,
                    "enable_tooltips": True,
                }

        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {}

    def _get_next_step(self, flow_id: str, current_step_id: str) -> Optional[str]:
        """Get the next step in the onboarding flow"""
        # This would typically query the flow definition
        # For now, using a simple step order
        step_order = [
            "welcome",
            "privacy_consent",
            "first_scan",
            "person_identification",
            "advanced_features",
            "privacy_settings",
            "completion",
        ]

        try:
            current_index = step_order.index(current_step_id)
            if current_index < len(step_order) - 1:
                return step_order[current_index + 1]
        except ValueError:
            pass

        return None

    def _calculate_progress(self, flow_id: str) -> float:
        """Calculate onboarding progress percentage"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Count completed steps
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT step_id) as completed_steps
                    FROM onboarding_progress
                    WHERE flow_id = ? AND status = 'completed'
                """,
                    (flow_id,),
                )

                completed = cursor.fetchone()[0] or 0

                # Total steps (hardcoded for now, should be dynamic)
                total_steps = 7

                return (completed / total_steps) * 100 if total_steps > 0 else 0

        except Exception as e:
            logger.error(f"Failed to calculate progress: {e}")
            return 0.0

    def _get_issue_specific_guidance(self, issue: str) -> Dict[str, Any]:
        """Get guidance for specific issues"""
        guidance_map = {
            "no_faces_detected": {
                "immediate_action": "Try a different photo with clearer faces",
                "troubleshooting": [
                    "Check photo quality and resolution",
                    "Ensure faces are well-lit and visible",
                    "Try photos with faces looking toward camera",
                ],
            },
            "too_many_clusters": {
                "immediate_action": "Review and merge duplicate person clusters",
                "troubleshooting": [
                    "Look for clusters with the same person",
                    "Use the merge function to combine duplicates",
                    "Adjust clustering sensitivity if needed",
                ],
            },
            "poor_recognition": {
                "immediate_action": "Provide feedback on incorrect identifications",
                "troubleshooting": [
                    "Confirm correct identifications",
                    "Reject incorrect matches",
                    "Add more photos of the person for better learning",
                ],
            },
        }

        return guidance_map.get(
            issue,
            {
                "immediate_action": "Contact support for assistance",
                "troubleshooting": ["Check the user guide", "Try restarting the process"],
            },
        )

    def complete_onboarding(self, user_id: str, feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Complete onboarding flow and collect feedback"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Update flow status
                conn.execute(
                    """
                    UPDATE onboarding_flows
                    SET status = ?, completed_at = CURRENT_TIMESTAMP,
                        progress_percentage = 100, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND status = ?
                """,
                    (OnboardingStatus.COMPLETED.value, user_id, OnboardingStatus.IN_PROGRESS.value),
                )

                if conn.total_changes == 0:
                    raise ValueError("No active onboarding flow found")

                # Record completion
                completion_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO tutorial_completions
                    (completion_id, user_id, tutorial_type, completion_score,
                     feedback_rating, feedback_comments)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        completion_id,
                        user_id,
                        "face_recognition_onboarding",
                        100.0,  # Full completion
                        feedback.get("rating") if feedback else None,
                        feedback.get("comments") if feedback else None,
                    ),
                )

            return {
                "status": "completed",
                "completion_id": completion_id,
                "message": "Onboarding completed successfully!",
                "completed_at": datetime.now().isoformat(),
                "next_steps": [
                    "Start your full photo scan",
                    "Explore advanced search features",
                    "Organize your people and albums",
                ],
            }

        except Exception as e:
            logger.error(f"Failed to complete onboarding: {e}")
            raise


def create_face_onboarding_service(db_path: str) -> FaceOnboardingService:
    """Factory function to create face onboarding service"""
    return FaceOnboardingService(db_path)
