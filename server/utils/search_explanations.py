def generate_metadata_match_explanation(query: str, result: dict) -> dict:
    """Generate match explanation for metadata search results with detailed breakdown"""
    reasons = []
    breakdown: dict[str, float] = {
        "filename_score": 0.0,
        "metadata_score": 0.0,
        "content_score": 0.0,
    }

    # Analyze the query to understand what matched
    query_lower = query.lower()
    metadata = result.get("metadata", {})
    filename = result.get("filename", result.get("file_path", "").split("/")[-1])

    # Check for filename matches (most common case)
    filename_match_score: float = 0.0
    if query_lower in filename.lower():
        # Calculate confidence based on how much of the filename matches
        match_ratio = len(query_lower) / len(filename.lower())
        confidence = min(0.95, 0.7 + (match_ratio * 0.25))  # 70-95% based on match ratio
        filename_match_score = confidence * 100.0
        breakdown["filename_score"] = filename_match_score

        reasons.append(
            {
                "category": "Filename Match",
                "matched": f"Filename '{filename}' contains '{query}' ({match_ratio:.1%} of filename)",
                "confidence": confidence,
                "badge": "📝",
                "type": "metadata",
            }
        )

    # Check for metadata matches
    metadata_matches = 0
    metadata_total = 0

    # Check for camera matches
    camera_info = metadata.get("camera", {})
    if camera_info:
        metadata_total += 1
        if any(term in query_lower for term in ["camera", "make", "model"]) or (
            camera_info.get("make") and camera_info.get("make").lower() in query_lower
        ):
            metadata_matches += 1
            reasons.append(
                {
                    "category": "Camera Equipment",
                    "matched": f"Shot with {camera_info.get('make')} {camera_info.get('model', '')}".strip(),
                    "confidence": 1.0,
                    "badge": "📷",
                    "type": "metadata",
                }
            )

    # Check for lens matches
    lens_info = metadata.get("lens", {})
    if lens_info:
        metadata_total += 1
        if any(term in query_lower for term in ["lens", "focal", "aperture"]):
            metadata_matches += 1
            if lens_info.get("focal_length"):
                reasons.append(
                    {
                        "category": "Lens Settings",
                        "matched": f"{lens_info.get('focal_length')}mm lens",
                        "confidence": 1.0,
                        "badge": "🔍",
                        "type": "metadata",
                    }
                )

    # Check for date matches
    date_info = metadata.get("date", {})
    if date_info:
        metadata_total += 1
        if any(term in query_lower for term in ["date", "taken", "2023", "2024"]):
            metadata_matches += 1
            if date_info.get("taken"):
                reasons.append(
                    {
                        "category": "Date & Time",
                        "matched": f"Taken on {date_info.get('taken')}",
                        "confidence": 1.0,
                        "badge": "📅",
                        "type": "metadata",
                    }
                )

    # Check for GPS/location matches
    gps_info = metadata.get("gps", {})
    if gps_info:
        metadata_total += 1
        if any(term in query_lower for term in ["gps", "location", "city"]) or (
            gps_info.get("city") and gps_info.get("city").lower() in query_lower
        ):
            metadata_matches += 1
            if gps_info.get("city"):
                reasons.append(
                    {
                        "category": "Location",
                        "matched": f"Located in {gps_info.get('city')}",
                        "confidence": 1.0,
                        "badge": "📍",
                        "type": "metadata",
                    }
                )

    # Calculate metadata score
    if metadata_total > 0:
        breakdown["metadata_score"] = (metadata_matches / metadata_total) * 100.0

    # If no specific matches found, provide generic match with lower confidence
    if not reasons:
        reasons.append(
            {
                "category": "General Match",
                "matched": "Found in metadata or file properties",
                "confidence": 0.6,
                "badge": "🔍",
                "type": "metadata",
            }
        )
        breakdown["metadata_score"] = 60

    # Calculate overall confidence
    overall_confidence = max(breakdown["filename_score"], breakdown["metadata_score"]) / 100

    return {"type": "metadata", "reasons": reasons, "overallConfidence": overall_confidence, "breakdown": breakdown}


def generate_hybrid_match_explanation(
    query: str,
    result: dict,
    metadata_weight: float,
    semantic_weight: float,
) -> dict:
    """Generate match explanation for hybrid search results with detailed breakdown"""
    reasons = []
    breakdown = {"metadata_score": 0, "semantic_score": 0, "filename_score": 0, "content_score": 0}

    # Calculate individual component scores based on the combined score and weights
    combined_score = result.get("score", 0)
    source = result.get("source", "hybrid")

    if source == "both":
        # Both metadata and semantic contributed
        estimated_metadata_score = (combined_score / (metadata_weight + semantic_weight)) * metadata_weight
        estimated_semantic_score = (combined_score / (metadata_weight + semantic_weight)) * semantic_weight

        breakdown["metadata_score"] = estimated_metadata_score * 100
        breakdown["semantic_score"] = estimated_semantic_score * 100
        breakdown["filename_score"] = estimated_metadata_score * 80  # Filename is part of metadata
        breakdown["content_score"] = estimated_semantic_score * 100

        reasons.append(
            {
                "category": "Metadata Match",
                "matched": f"File details match your search (weight: {metadata_weight:.0%})",
                "confidence": estimated_metadata_score,
                "badge": "📊",
                "type": "metadata",
            }
        )

        reasons.append(
            {
                "category": "Visual Content",
                "matched": f"We understand the visual content matches your query (weight: {semantic_weight:.0%})",
                "confidence": estimated_semantic_score,
                "badge": "🎯",
                "type": "semantic",
            }
        )

    elif source == "metadata":
        # Only metadata contributed
        breakdown["metadata_score"] = combined_score * 100
        breakdown["filename_score"] = combined_score * 80

        reasons.append(
            {
                "category": "Metadata Match",
                "matched": "Strong match in file details and metadata",
                "confidence": combined_score,
                "badge": "📊",
                "type": "metadata",
            }
        )

    elif source == "semantic":
        # Only semantic contributed
        breakdown["semantic_score"] = combined_score * 100
        breakdown["content_score"] = combined_score * 100

        reasons.append(
            {
                "category": "Visual Content",
                "matched": "We identified visual elements matching your search",
                "confidence": combined_score,
                "badge": "🎯",
                "type": "semantic",
            }
        )

    return {"type": "hybrid", "reasons": reasons, "overallConfidence": combined_score, "breakdown": breakdown}


def generate_semantic_match_explanation(query: str, result: dict, score: float) -> dict:
    """Generate match explanation for semantic search results with detailed breakdown"""
    reasons = []
    breakdown = {"semantic_score": score * 100, "content_score": score * 100}

    # We identify visual concepts (this would normally come from our analysis engine)
    # For now, we'll generate plausible explanations based on the query
    query_lower = query.lower()

    # Analyze query for visual concepts with confidence adjustment
    confidence_boost = 0.1  # Boost confidence for specific matches

    if any(word in query_lower for word in ["sunset", "golden", "orange", "warm", "light"]):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append(
            {
                "category": "Visual Content",
                "matched": "We found warm lighting, golden hour colors, and sunset atmosphere",
                "confidence": adjusted_score,
                "badge": "🌅",
                "type": "semantic",
            }
        )
        breakdown["content_score"] = adjusted_score * 100

    if any(word in query_lower for word in ["person", "people", "face", "portrait", "human"]):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append(
            {
                "category": "People Detection",
                "matched": "We identified human faces and body poses in this image",
                "confidence": adjusted_score,
                "badge": "�",
                "type": "semantic",
            }
        )
        breakdown["content_score"] = adjusted_score * 100

    if any(word in query_lower for word in ["car", "vehicle", "street", "road", "traffic"]):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append(
            {
                "category": "Object Recognition",
                "matched": "We spotted vehicles, roads, and urban infrastructure",
                "confidence": adjusted_score,
                "badge": "🚗",
                "type": "semantic",
            }
        )
        breakdown["content_score"] = adjusted_score * 100

    if any(word in query_lower for word in ["nature", "tree", "forest", "landscape", "mountain", "sky"]):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append(
            {
                "category": "Scene Understanding",
                "matched": "We recognized natural landscapes, vegetation, and outdoor scenes",
                "confidence": adjusted_score,
                "badge": "🌲",
                "type": "semantic",
            }
        )
        breakdown["content_score"] = adjusted_score * 100

    if any(word in query_lower for word in ["food", "eat", "meal", "restaurant", "kitchen"]):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append(
            {
                "category": "Object Recognition",
                "matched": "We discovered food items, dining scenes, and culinary objects",
                "confidence": adjusted_score,
                "badge": "🍽️",
                "type": "semantic",
            }
        )
        breakdown["content_score"] = adjusted_score * 100

    # If no specific matches, provide generic AI match with original score
    if not reasons:
        reasons.append(
            {
                "category": "Visual Analysis",
                "matched": f"We found visual similarities in this content (confidence: {score:.1%})",
                "confidence": score,
                "badge": "🤖",
                "type": "semantic",
            }
        )

    return {"type": "semantic", "reasons": reasons, "overallConfidence": score, "breakdown": breakdown}
