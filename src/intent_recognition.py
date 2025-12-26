"""
Intent Recognition System for Photo Search

This module provides intent detection for search queries to:
1. Improve hybrid search weighting
2. Provide search suggestions
3. Generate intent badges for UI
4. Enable smart search routing

12 Supported Intents:
1. Camera/Device Search (camera, device, make, model)
2. Date/Time Search (date, time, year, month, day)
3. Location/GPS Search (location, gps, place, city)
4. People/Face Search (person, face, people, family)
5. Object Search (object, thing, item)
6. Scene Search (scene, landscape, indoor, outdoor)
7. Event Search (event, wedding, birthday, vacation)
8. Technical Search (resolution, size, format, codec)
9. Color Search (color, red, blue, bright, dark)
10. Emotion Search (happy, sad, emotion, mood)
11. Activity Search (activity, action, sport, running)
12. Generic Search (fallback)

Usage:
    intent_detector = IntentDetector()
    intent = intent_detector.detect_intent("Canon camera beach vacation")
    # Returns: {'primary_intent': 'camera', 'secondary_intents': ['location', 'event'], 'confidence': 0.85}
"""

import re
from typing import Any, Dict, List, cast
from collections import defaultdict


class IntentDetector:
    """Detect search intent from user queries."""

    def __init__(self):
        # Define intent keywords and patterns
        self.intent_definitions = {
            "camera": {
                "keywords": [
                    "camera",
                    "device",
                    "make",
                    "model",
                    "canon",
                    "nikon",
                    "sony",
                    "iphone",
                    "samsung",
                ],
                "patterns": [r"\b(camera|device|make|model)\b"],
                "description": "Searching for specific camera or device information",
            },
            "date": {
                "keywords": [
                    "date",
                    "time",
                    "year",
                    "month",
                    "day",
                    "created",
                    "modified",
                    "recent",
                    "old",
                ],
                "patterns": [r"\b(\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|\d{1,2}/\d{1,2}/\d{4})\b"],
                "description": "Searching by date or time range",
            },
            "location": {
                "keywords": [
                    "location",
                    "gps",
                    "place",
                    "city",
                    "country",
                    "beach",
                    "mountain",
                    "park",
                ],
                "patterns": [r"\b(gps|location|place)\b"],
                "description": "Searching by geographic location or GPS data",
            },
            "people": {
                "keywords": [
                    "person",
                    "face",
                    "people",
                    "family",
                    "friend",
                    "group",
                    "portrait",
                ],
                "patterns": [r"\b(person|face|people|family)\b"],
                "description": "Searching for photos with people or faces",
            },
            "object": {
                "keywords": [
                    "object",
                    "thing",
                    "item",
                    "car",
                    "house",
                    "tree",
                    "animal",
                    "dog",
                    "cat",
                ],
                "patterns": [r"\b(object|thing|item)\b"],
                "description": "Searching for specific objects or items",
            },
            "scene": {
                "keywords": [
                    "scene",
                    "landscape",
                    "indoor",
                    "outdoor",
                    "sunset",
                    "sunrise",
                    "night",
                ],
                "patterns": [r"\b(scene|landscape|indoor|outdoor)\b"],
                "description": "Searching by scene type or environment",
            },
            "event": {
                "keywords": [
                    "event",
                    "wedding",
                    "birthday",
                    "vacation",
                    "party",
                    "celebration",
                    "trip",
                ],
                "patterns": [r"\b(event|wedding|birthday|vacation)\b"],
                "description": "Searching for specific events or occasions",
            },
            "technical": {
                "keywords": [
                    "resolution",
                    "size",
                    "format",
                    "codec",
                    "fps",
                    "quality",
                    "megapixel",
                ],
                "patterns": [r"\b(resolution|size|format|codec|fps)\b"],
                "description": "Searching by technical specifications",
            },
            "color": {
                "keywords": [
                    "color",
                    "red",
                    "blue",
                    "green",
                    "bright",
                    "dark",
                    "light",
                    "vibrant",
                ],
                "patterns": [r"\b(color|colour|bright|dark|light)\b"],
                "description": "Searching by color characteristics",
            },
            "emotion": {
                "keywords": [
                    "emotion",
                    "happy",
                    "sad",
                    "mood",
                    "smile",
                    "laugh",
                    "cry",
                    "angry",
                ],
                "patterns": [r"\b(happy|sad|emotion|mood)\b"],
                "description": "Searching by emotional content",
            },
            "activity": {
                "keywords": [
                    "activity",
                    "action",
                    "sport",
                    "running",
                    "jumping",
                    "playing",
                    "dancing",
                ],
                "patterns": [r"\b(activity|action|sport|running)\b"],
                "description": "Searching for specific activities or actions",
            },
            "generic": {
                "keywords": [],
                "patterns": [],
                "description": "General or unspecified search",
            },
        }

        # Initialize NLP components (simple keyword-based for now)
        self.stop_words = set(["the", "a", "an", "and", "or", "in", "on", "at", "to", "for"])

    def detect_intent(self, query: str) -> Dict:
        """
        Detect the primary intent of a search query.

        Args:
            query: User search query string

        Returns:
            Dictionary with intent information including primary intent,
            secondary intents, confidence scores, and suggestions
        """
        if not query or not query.strip():
            return {
                "primary_intent": "generic",
                "secondary_intents": [],
                "confidence": 0.0,
                "suggestions": [],
                "badges": [],
            }

        # Normalize query
        query_lower = query.lower().strip()

        # Remove stop words for better matching
        query_tokens = [word for word in query_lower.split() if word not in self.stop_words]
        query_clean = " ".join(query_tokens)

        # Score each intent
        intent_scores = defaultdict(float)

        for intent_name, intent_def in self.intent_definitions.items():
            score = 0.0

            # Keyword matching
            for keyword in intent_def["keywords"]:
                if keyword in query_clean:
                    # Slightly favor keyword matches to boost confidence for clear queries
                    score += 1.25

            # Pattern matching
            for pattern in intent_def["patterns"]:
                if re.search(pattern, query_clean):
                    score += 1.5  # Patterns get higher weight

            intent_scores[intent_name] = score

        # Boost camera confidence for brand keywords (e.g., 'canon', 'nikon')
        brand_keywords = {"canon", "nikon", "sony", "iphone", "samsung"}
        if any(b in query_clean for b in brand_keywords):
            intent_scores["camera"] += 1.5

        # Find primary intent (highest score)
        primary_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
        primary_score = intent_scores[primary_intent]

        # Calculate confidence (0-1 scale)
        total_score = sum(intent_scores.values())
        confidence = primary_score / max(total_score, 1.0) if total_score > 0 else 0.0

        # Find secondary intents (scores > 0 but < primary)
        secondary_intent_entries: List[Dict[str, Any]] = []
        for intent_name, score in intent_scores.items():
            if intent_name != primary_intent and score > 0:
                secondary_intent_entries.append(
                    {
                        "intent": intent_name,
                        "score": score,
                        "confidence": score / max(total_score, 1.0),
                    }
                )

        # Sort secondary intents by score
        secondary_intent_entries.sort(key=lambda x: cast(float, x["score"]), reverse=True)
        secondary_intents: List[str] = [cast(str, intent["intent"]) for intent in secondary_intent_entries]

        # Generate suggestions based on intent
        suggestions = self._generate_suggestions(primary_intent, query_clean)

        # Generate badges for UI
        badges = self._generate_badges(primary_intent, secondary_intents)

        return {
            "primary_intent": primary_intent,
            "secondary_intents": secondary_intents,
            "confidence": round(confidence, 3),
            "suggestions": suggestions,
            "badges": badges,
            "description": self.intent_definitions[primary_intent]["description"],
        }

    def _generate_suggestions(self, primary_intent: str, query: str) -> List[str]:
        """Generate search suggestions based on detected intent."""
        suggestions = []

        if primary_intent == "camera":
            suggestions.extend(
                [
                    f"{query} AND resolution>12MP",
                    f"{query} AND date>2023-01-01",
                    f"{query} AND location=beach",
                ]
            )

        elif primary_intent == "date":
            suggestions.extend(
                [
                    f"{query} AND camera=Canon",
                    f"{query} AND people=yes",
                    f"{query} AND scene=landscape",
                ]
            )

        elif primary_intent == "location":
            suggestions.extend(
                [
                    f"{query} AND date>2023-01-01",
                    f"{query} AND people=yes",
                    f"{query} AND event=vacation",
                ]
            )

        elif primary_intent == "people":
            suggestions.extend(
                [
                    f"{query} AND emotion=happy",
                    f"{query} AND event=wedding",
                    f"{query} AND date>2023-01-01",
                ]
            )

        elif primary_intent == "event":
            suggestions.extend(
                [
                    f"{query} AND people=yes",
                    f"{query} AND location=beach",
                    f"{query} AND date>2023-01-01",
                ]
            )

        else:
            # Generic suggestions
            suggestions.extend(
                [
                    f"{query} AND date>2023-01-01",
                    f"{query} AND camera=Canon",
                    f"{query} AND people=yes",
                ]
            )

        return suggestions[:3]  # Return top 3 suggestions

    def _generate_badges(self, primary_intent: str, secondary_intents: List[str]) -> List[Dict]:
        """Generate intent badges for UI display."""
        badges = []

        # Primary intent badge
        badges.append(
            {
                "intent": primary_intent,
                "type": "primary",
                "label": self._get_intent_label(primary_intent),
                "icon": self._get_intent_icon(primary_intent),
            }
        )

        # Secondary intent badges
        for intent in secondary_intents[:2]:  # Max 2 secondary badges
            badges.append(
                {
                    "intent": intent,
                    "type": "secondary",
                    "label": self._get_intent_label(intent),
                    "icon": self._get_intent_icon(intent),
                }
            )

        return badges

    def _get_intent_label(self, intent: str) -> str:
        """Get human-readable label for intent."""
        labels = {
            "camera": "📷 Camera",
            "date": "📅 Date",
            "location": "📍 Location",
            "people": "👥 People",
            "object": "📦 Object",
            "scene": "🌄 Scene",
            "event": "🎉 Event",
            "technical": "⚙️ Technical",
            "color": "🎨 Color",
            "emotion": "😊 Emotion",
            "activity": "🏃 Activity",
            "generic": "🔍 Search",
        }
        return labels.get(intent, intent)

    def _get_intent_icon(self, intent: str) -> str:
        """Get icon for intent (emoji-based for now)."""
        return self._get_intent_label(intent).split()[0]  # Extract first emoji

    def get_all_intents(self) -> Dict:
        """Get all supported intents with descriptions."""
        return {
            intent_name: {
                "description": intent_def["description"],
                "keywords": intent_def["keywords"],
                "label": self._get_intent_label(intent_name),
                "icon": self._get_intent_icon(intent_name),
            }
            for intent_name, intent_def in self.intent_definitions.items()
        }

    def get_search_badges(self, query: str) -> List[Dict]:
        """Get intent badges for a search query (simplified interface)."""
        intent_result = self.detect_intent(query)
        return intent_result["badges"]

    def get_search_suggestions(self, query: str) -> List[str]:
        """Get search suggestions for a query (simplified interface)."""
        intent_result = self.detect_intent(query)
        return intent_result["suggestions"]


def main():
    """CLI interface for testing intent detection."""
    import argparse

    parser = argparse.ArgumentParser(description="Intent Recognition System for Photo Search")
    parser.add_argument("--query", help="Test query for intent detection")
    parser.add_argument("--list", action="store_true", help="List all supported intents")

    args = parser.parse_args()

    detector = IntentDetector()

    if args.list:
        print("Supported Intents:")
        print("=" * 50)
        for intent_name, intent_info in detector.get_all_intents().items():
            print(f"{intent_info['icon']} {intent_name}: {intent_info['description']}")
            print(f"   Keywords: {', '.join(intent_info['keywords'][:5])}")
            print()

    elif args.query:
        result = detector.detect_intent(args.query)
        print(f"Query: '{args.query}'")
        print(f"Primary Intent: {result['primary_intent']} ({result['confidence']})")
        print(f"Description: {result['description']}")
        print(f"Secondary Intents: {', '.join(result['secondary_intents'])}")
        print(f"Badges: {[badge['label'] for badge in result['badges']]}")
        print(f"Suggestions: {result['suggestions']}")

    else:
        # Interactive mode
        print("Intent Recognition System - Interactive Mode")
        print("Enter queries to detect intent (Ctrl+C to exit)")

        while True:
            try:
                query = input("\nQuery: ")
                if not query:
                    continue

                result = detector.detect_intent(query)
                print(f"Intent: {result['primary_intent']} ({result['confidence']})")
                print(f"Badges: {[badge['label'] for badge in result['badges']]}")
                print(f"Suggestions: {result['suggestions']}")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break


if __name__ == "main":
    main()
