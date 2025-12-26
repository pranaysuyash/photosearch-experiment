"""
Smart Albums

Auto-generated albums based on rules and metadata.
"""

import os
from typing import List, Dict, Any
from datetime import datetime, timedelta


class SmartAlbumRule:
    """Base class for smart album rules."""

    def __init__(self, rule_config: Dict[str, Any]):
        self.config = rule_config

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        """Check if photo matches this rule."""
        raise NotImplementedError


class FilenameContainsRule(SmartAlbumRule):
    """Match photos where filename contains a string."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        value = self.config.get("value", "")
        case_sensitive = self.config.get("case_sensitive", False)

        filename = os.path.basename(photo_path)

        if not case_sensitive:
            return value.lower() in filename.lower()
        return value in filename


class FileExtensionRule(SmartAlbumRule):
    """Match photos with specific extension."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        extensions = self.config.get("extensions", [])
        if isinstance(extensions, str):
            extensions = [extensions]

        ext = os.path.splitext(photo_path)[1].lower()
        return ext in [e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions]


class FileSizeRule(SmartAlbumRule):
    """Match photos by file size."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        operator = self.config.get("operator", ">")
        size_bytes = self.config.get("size_bytes", 0)

        fs_meta = photo_metadata.get("filesystem", {})
        file_size = fs_meta.get("size_bytes", 0)

        if operator == ">":
            return file_size > size_bytes
        elif operator == "<":
            return file_size < size_bytes
        elif operator == ">=":
            return file_size >= size_bytes
        elif operator == "<=":
            return file_size <= size_bytes
        elif operator == "==":
            return file_size == size_bytes

        return False


class DateRangeRule(SmartAlbumRule):
    """Match photos within a date range."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        from_date = self.config.get("from_date")
        to_date = self.config.get("to_date")

        fs_meta = photo_metadata.get("filesystem", {})
        created = fs_meta.get("created")

        if not created:
            return False

        try:
            photo_date = datetime.fromisoformat(created.replace("Z", "+00:00"))

            if from_date:
                from_dt = datetime.fromisoformat(from_date)
                if photo_date < from_dt:
                    return False

            if to_date:
                to_dt = datetime.fromisoformat(to_date)
                if photo_date > to_dt:
                    return False

            return True
        except:
            return False


class NoGPSRule(SmartAlbumRule):
    """Match photos without GPS data."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        gps = photo_metadata.get("gps", {})
        has_gps = bool(gps.get("latitude") and gps.get("longitude"))
        return not has_gps


class HasGPSRule(SmartAlbumRule):
    """Match photos with GPS data."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        gps = photo_metadata.get("gps", {})
        return bool(gps.get("latitude") and gps.get("longitude"))


class CameraModelRule(SmartAlbumRule):
    """Match photos from specific camera."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        models = self.config.get("models", [])
        if isinstance(models, str):
            models = [models]

        exif = photo_metadata.get("exif", {})
        camera_model = exif.get("image", {}).get("Model", "")

        return any(model.lower() in camera_model.lower() for model in models)


class RecentPhotosRule(SmartAlbumRule):
    """Match photos from last N days."""

    def matches(self, photo_metadata: Dict[str, Any], photo_path: str) -> bool:
        days = self.config.get("days", 30)

        fs_meta = photo_metadata.get("filesystem", {})
        created = fs_meta.get("created")

        if not created:
            return False

        try:
            photo_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
            cutoff = datetime.now() - timedelta(days=days)
            return photo_date >= cutoff
        except:
            return False


# Rule registry
RULE_TYPES: Dict[str, type] = {
    "filename_contains": FilenameContainsRule,
    "file_extension": FileExtensionRule,
    "file_size": FileSizeRule,
    "date_range": DateRangeRule,
    "no_gps": NoGPSRule,
    "has_gps": HasGPSRule,
    "camera_model": CameraModelRule,
    "recent_photos": RecentPhotosRule,
}


class SmartAlbumEngine:
    """Evaluate smart album rules and populate albums."""

    @staticmethod
    def create_rule(rule_config: Dict[str, Any]) -> SmartAlbumRule:
        """Create a rule instance from config."""
        rule_type = rule_config.get("type")
        rule_class = RULE_TYPES.get(rule_type)

        if not rule_class:
            raise ValueError(f"Unknown rule type: {rule_type}")

        return rule_class(rule_config)

    @staticmethod
    def evaluate_rules(
        rules: List[Dict[str, Any]], photo_metadata: Dict[str, Any], photo_path: str, match_all: bool = True
    ) -> bool:
        """
        Evaluate all rules for a photo.

        Args:
            rules: List of rule configurations
            photo_metadata: Photo metadata dict
            photo_path: Path to photo file
            match_all: If True, all rules must match (AND). If False, any rule matches (OR).

        Returns:
            True if photo matches the rules
        """
        if not rules:
            return False

        rule_instances = [SmartAlbumEngine.create_rule(r) for r in rules]

        if match_all:
            return all(rule.matches(photo_metadata, photo_path) for rule in rule_instances)
        else:
            return any(rule.matches(photo_metadata, photo_path) for rule in rule_instances)


# Predefined smart albums
PREDEFINED_SMART_ALBUMS = [
    {
        "id": "screenshots",
        "name": "Screenshots",
        "description": "All screenshots",
        "rules": [{"type": "filename_contains", "value": "screenshot", "case_sensitive": False}],
    },
    {
        "id": "large_videos",
        "name": "Large Videos",
        "description": "Videos larger than 100MB",
        "rules": [
            {"type": "file_extension", "extensions": [".mp4", ".mov", ".avi", ".mkv"]},
            {"type": "file_size", "operator": ">", "size_bytes": 100 * 1024 * 1024},
        ],
    },
    {
        "id": "no_location",
        "name": "No Location",
        "description": "Photos without GPS data",
        "rules": [{"type": "no_gps"}],
    },
    {
        "id": "recent_30_days",
        "name": "Recent (30 days)",
        "description": "Photos from the last 30 days",
        "rules": [{"type": "recent_photos", "days": 30}],
    },
    {
        "id": "with_location",
        "name": "With Location",
        "description": "Photos with GPS data",
        "rules": [{"type": "has_gps"}],
    },
]


def initialize_predefined_smart_albums(albums_db):
    """Create predefined smart albums if they don't exist."""
    existing_albums = {album.id: album for album in albums_db.list_albums()}

    for smart_album_config in PREDEFINED_SMART_ALBUMS:
        album_id = smart_album_config["id"]

        if album_id not in existing_albums:
            albums_db.create_album(
                album_id=album_id,
                name=smart_album_config["name"],
                description=smart_album_config["description"],
                is_smart=True,
                smart_rules={
                    "rules": smart_album_config["rules"],
                    "match_all": True,  # AND logic by default
                },
            )


def populate_smart_album(albums_db, album_id: str, all_photos_with_metadata: List[tuple]):
    """
    Populate a smart album based on its rules.

    Args:
        albums_db: AlbumsDB instance
        album_id: Album ID to populate
        all_photos_with_metadata: List of (photo_path, metadata_dict) tuples
    """
    album = albums_db.get_album(album_id)

    if not album or not album.is_smart or not album.smart_rules:
        return

    rules = album.smart_rules.get("rules", [])
    match_all = album.smart_rules.get("match_all", True)

    # Find matching photos
    matching_paths = []
    for photo_path, metadata in all_photos_with_metadata:
        if SmartAlbumEngine.evaluate_rules(rules, metadata, photo_path, match_all):
            matching_paths.append(photo_path)

    # Clear existing photos (smart albums are fully recomputed)
    existing_paths = albums_db.get_album_photos(album_id, limit=999999)
    if existing_paths:
        albums_db.remove_photos_from_album(album_id, existing_paths)

    # Add matching photos
    if matching_paths:
        albums_db.add_photos_to_album(album_id, matching_paths)
