"""
Metadata Mapper - Convert raw EXIF/metadata to structured database columns

This module maps raw metadata from metadata_extractor.py to the structured
searchable columns in the enhanced database schema. It handles normalization,
unit conversion, and composite field generation for professional photography workflows.

Key Features:
- Camera make/model normalization (Canon vs CANON vs canon)
- Exposure settings parsing and validation
- Lens information extraction and normalization
- Composite field generation (exposure triangle, searchable text)
- Unit conversion and data type validation

Author: PhotoSearch Metadata Completion System
Date: 2025-12-29
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from fractions import Fraction

logger = logging.getLogger(__name__)


class CameraNormalizer:
    """Normalize camera make and model names for consistent searchability."""

    # Common camera make normalizations
    MAKE_NORMALIZATIONS = {
        "canon": "Canon",
        "nikon": "Nikon",
        "sony": "Sony",
        "fujifilm": "Fujifilm",
        "fuji": "Fujifilm",
        "olympus": "Olympus",
        "panasonic": "Panasonic",
        "leica": "Leica",
        "pentax": "Pentax",
        "ricoh": "Ricoh",
        "hasselblad": "Hasselblad",
        "mamiya": "Mamiya",
        "phase one": "Phase One",
        "apple": "Apple",
        "samsung": "Samsung",
        "huawei": "Huawei",
        "google": "Google",
        "oneplus": "OnePlus",
        "xiaomi": "Xiaomi",
        "dji": "DJI",
        "gopro": "GoPro",
    }

    def normalize_make(self, make: str) -> Optional[str]:
        """
        Normalize camera make to consistent format.

        Args:
            make: Raw camera make string

        Returns:
            Normalized make or None if invalid
        """
        if not make or not isinstance(make, str):
            return None

        # Clean and normalize
        make_clean = make.strip().lower()

        # Direct lookup
        if make_clean in self.MAKE_NORMALIZATIONS:
            return self.MAKE_NORMALIZATIONS[make_clean]

        # Partial matching for complex names
        for key, normalized in self.MAKE_NORMALIZATIONS.items():
            if key in make_clean or make_clean in key:
                return normalized

        # If no match found, return title case of original
        return make.strip().title()

    def normalize_model(self, model: str) -> Optional[str]:
        """
        Normalize camera model to consistent format.

        Args:
            model: Raw camera model string

        Returns:
            Normalized model or None if invalid
        """
        if not model or not isinstance(model, str):
            return None

        # Clean up common model name issues
        model_clean = model.strip()

        # Remove redundant manufacturer names from model
        for make in self.MAKE_NORMALIZATIONS.values():
            if model_clean.lower().startswith(make.lower()):
                model_clean = model_clean[len(make) :].strip()

        # Clean up common prefixes/suffixes
        model_clean = re.sub(r"^(EOS|PowerShot|Cyber-shot|ILCE|NEX|Alpha|D|Z)\s*", "", model_clean, flags=re.IGNORECASE)

        return model_clean.strip() if model_clean else None


class LensNormalizer:
    """Normalize lens make and model names for consistent searchability."""

    def normalize_make(self, make: str) -> Optional[str]:
        """Normalize lens make using camera normalizer."""
        normalizer = CameraNormalizer()
        return normalizer.normalize_make(make)

    def normalize_model(self, model: str) -> Optional[str]:
        """
        Normalize lens model to consistent format.

        Args:
            model: Raw lens model string

        Returns:
            Normalized model or None if invalid
        """
        if not model or not isinstance(model, str):
            return None

        # Clean up lens model
        model_clean = model.strip()

        # Standardize common lens notation
        # Convert "24-70mm f/2.8" variations to consistent format
        model_clean = re.sub(r"(\d+)-(\d+)\s*mm\s*[fF]/(\d+\.?\d*)", r"\1-\2mm f/\3", model_clean)
        model_clean = re.sub(r"(\d+)\s*mm\s*[fF]/(\d+\.?\d*)", r"\1mm f/\2", model_clean)

        # Clean up manufacturer names that might be duplicated
        for make in ["Canon", "Nikon", "Sony", "Sigma", "Tamron", "Tokina"]:
            if model_clean.startswith(make):
                model_clean = model_clean[len(make) :].strip()

        return model_clean if model_clean else None


class MetadataMapper:
    """
    Maps raw EXIF/metadata to structured database columns.
    Handles normalization, unit conversion, and composite field generation.
    """

    def __init__(self):
        self.camera_normalizer = CameraNormalizer()
        self.lens_normalizer = LensNormalizer()

    def map_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map raw metadata to structured searchable fields.

        Args:
            raw_metadata: Raw metadata from metadata_extractor

        Returns:
            Dictionary of normalized searchable fields
        """
        mapped = {}

        try:
            # Map camera metadata
            camera_data = self._map_camera_metadata(raw_metadata)
            mapped.update(camera_data)

            # Map lens metadata
            lens_data = self._map_lens_metadata(raw_metadata)
            mapped.update(lens_data)

            # Map exposure metadata
            exposure_data = self._map_exposure_metadata(raw_metadata)
            mapped.update(exposure_data)

            # Map image quality metadata
            quality_data = self._map_image_quality_metadata(raw_metadata)
            mapped.update(quality_data)

            # Map software metadata
            software_data = self._map_software_metadata(raw_metadata)
            mapped.update(software_data)

            # Map copyright metadata
            copyright_data = self._map_copyright_metadata(raw_metadata)
            mapped.update(copyright_data)

            # Map IPTC metadata (override EXIF when present)
            iptc_data = self._map_iptc_metadata(raw_metadata)
            mapped = self._merge_mapped_fields(mapped, iptc_data, prefer_existing=False)

            # Map XMP metadata (fill missing IPTC/EXIF data)
            xmp_data = self._map_xmp_metadata(raw_metadata)
            mapped = self._merge_mapped_fields(mapped, xmp_data, prefer_existing=True)

            # Generate composite fields
            composite_data = self._generate_composite_fields(mapped, raw_metadata)
            mapped.update(composite_data)

        except Exception as e:
            logger.error(f"Error mapping metadata: {e}")

        return mapped

    def _map_camera_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize camera-specific fields from raw metadata."""
        camera_data = {}

        # Get EXIF data
        exif = raw_metadata.get("exif", {})
        image_exif = exif.get("image", {}) if exif else {}

        # Camera make
        make = image_exif.get("Make", "")
        if make:
            camera_data["camera_make"] = self.camera_normalizer.normalize_make(make)

        # Camera model
        model = image_exif.get("Model", "")
        if model:
            camera_data["camera_model"] = self.camera_normalizer.normalize_model(model)

        # Camera serial number
        serial = image_exif.get("BodySerialNumber") or image_exif.get("SerialNumber")
        if serial:
            camera_data["camera_serial"] = str(serial).strip()

        return camera_data

    def _map_lens_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize lens-specific fields from raw metadata."""
        lens_data = {}

        # Get EXIF data
        exif = raw_metadata.get("exif", {})
        exif_data = exif.get("exif", {}) if exif else {}

        # Lens model
        lens_model = exif_data.get("LensModel") or exif_data.get("LensInfo")
        if lens_model:
            lens_data["lens_model"] = self.lens_normalizer.normalize_model(str(lens_model))

        # Lens make (often not available, try to infer from camera make)
        lens_make = exif_data.get("LensMake")
        if lens_make:
            lens_data["lens_make"] = self.lens_normalizer.normalize_make(str(lens_make))
        elif lens_data.get("lens_model"):
            # Try to infer lens make from model string
            model = lens_data["lens_model"]
            for make in ["Canon", "Nikon", "Sony", "Sigma", "Tamron", "Tokina", "Zeiss"]:
                if make.lower() in model.lower():
                    lens_data["lens_make"] = make
                    break

        # Lens serial number
        lens_serial = exif_data.get("LensSerialNumber")
        if lens_serial:
            lens_data["lens_serial"] = str(lens_serial).strip()

        return lens_data

    def _map_exposure_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize exposure-specific fields from raw metadata."""
        exposure_data = {}

        # Get EXIF data
        exif = raw_metadata.get("exif", {})
        exif_data = exif.get("exif", {}) if exif else {}

        # ISO
        iso = exif_data.get("ISOSpeedRatings") or exif_data.get("ISO")
        if iso:
            exposure_data["iso"] = self._parse_iso(iso)

        # Aperture (f-number)
        aperture = exif_data.get("FNumber") or exif_data.get("ApertureValue")
        if aperture:
            exposure_data["aperture"] = self._parse_aperture(aperture)

        # Shutter speed
        shutter = exif_data.get("ExposureTime") or exif_data.get("ShutterSpeedValue")
        if shutter:
            shutter_display, shutter_decimal = self._parse_shutter_speed(shutter)
            if shutter_display:
                exposure_data["shutter_speed"] = shutter_display
                exposure_data["shutter_speed_decimal"] = shutter_decimal

        # Exposure compensation
        exp_comp = exif_data.get("ExposureCompensation") or exif_data.get("ExposureBiasValue")
        if exp_comp:
            exposure_data["exposure_compensation"] = self._parse_exposure_compensation(exp_comp)

        # Exposure mode
        exp_mode = exif_data.get("ExposureMode") or exif_data.get("ExposureProgram")
        if exp_mode:
            exposure_data["exposure_mode"] = self._parse_exposure_mode(exp_mode)

        # Metering mode
        metering = exif_data.get("MeteringMode")
        if metering:
            exposure_data["metering_mode"] = self._parse_metering_mode(metering)

        # Focal length
        focal_length = exif_data.get("FocalLength")
        if focal_length:
            exposure_data["focal_length"] = self._parse_focal_length(focal_length)

        # 35mm equivalent focal length
        focal_35mm = exif_data.get("FocalLengthIn35mmFilm")
        if focal_35mm:
            exposure_data["focal_length_35mm"] = self._parse_focal_length_35mm(focal_35mm)

        # Flash
        flash = exif_data.get("Flash")
        if flash is not None:
            flash_used, flash_mode = self._parse_flash(flash)
            exposure_data["flash_used"] = flash_used
            if flash_mode:
                exposure_data["flash_mode"] = flash_mode

        # White balance
        wb = exif_data.get("WhiteBalance")
        if wb:
            exposure_data["white_balance"] = self._parse_white_balance(wb)

        # Color temperature
        color_temp = exif_data.get("ColorTemperature")
        if color_temp:
            exposure_data["color_temperature"] = self._parse_color_temperature(color_temp)

        return exposure_data

    def _map_image_quality_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract image quality and format information."""
        quality_data = {}

        # Get image properties
        image = raw_metadata.get("image", {})
        if image:
            # Image format
            format_name = image.get("format")
            if format_name:
                quality_data["image_quality"] = str(format_name).upper()

        # Get EXIF data for color space
        exif = raw_metadata.get("exif", {})
        exif_data = exif.get("exif", {}) if exif else {}

        # Color space
        color_space = exif_data.get("ColorSpace")
        if color_space:
            quality_data["color_space"] = self._parse_color_space(color_space)

        # Bit depth (try to infer from image mode)
        if image:
            mode = image.get("mode")
            if mode:
                quality_data["bit_depth"] = self._infer_bit_depth(mode)

        return quality_data

    def _map_software_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract software and processing information."""
        software_data = {}

        # Get EXIF data
        exif = raw_metadata.get("exif", {})
        image_exif = exif.get("image", {}) if exif else {}

        # Software used to create/edit image
        software = image_exif.get("Software")
        if software:
            software_data["software"] = str(software).strip()

        # Processing software (sometimes in different fields)
        processing = image_exif.get("ProcessingSoftware") or image_exif.get("HostComputer")
        if processing and processing != software:
            software_data["edit_software"] = str(processing).strip()

        return software_data

    def _map_copyright_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract copyright and attribution information."""
        copyright_data = {}

        # Get EXIF data
        exif = raw_metadata.get("exif", {})
        image_exif = exif.get("image", {}) if exif else {}

        # Copyright
        copyright_info = image_exif.get("Copyright")
        if copyright_info:
            copyright_data["copyright"] = str(copyright_info).strip()

        # Creator/Artist
        creator = image_exif.get("Artist") or image_exif.get("Creator")
        if creator:
            copyright_data["creator"] = str(creator).strip()

        # Creator tool
        creator_tool = image_exif.get("CreatorTool")
        if creator_tool:
            copyright_data["creator_tool"] = str(creator_tool).strip()

        return copyright_data

    def _get_metadata_fields(self, raw_metadata: Dict[str, Any], key: str) -> Dict[str, Any]:
        """Extract normalized metadata fields from a section."""
        section = raw_metadata.get(key) or {}
        if isinstance(section, dict):
            fields = section.get("fields")
            if isinstance(fields, dict):
                return fields
            return section
        return {}

    def _coerce_text(self, value: Any) -> Optional[str]:
        """Coerce a single metadata value to trimmed text."""
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            for item in value:
                text = self._coerce_text(item)
                if text:
                    return text
            return None
        text = str(value).strip()
        return text or None

    def _split_list_value(self, value: Any) -> List[str]:
        """Split list-like metadata values into a normalized list."""
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            items: List[str] = []
            for item in value:
                items.extend(self._split_list_value(item))
            return items
        if isinstance(value, str):
            parts = [part.strip() for part in value.replace(";", ",").split(",")]
            return [part for part in parts if part]
        text = str(value).strip()
        return [text] if text else []

    def _join_list_value(self, values: List[str]) -> Optional[str]:
        """Join list values into a comma-separated string without duplicates."""
        if not values:
            return None
        seen = set()
        ordered: List[str] = []
        for item in values:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ", ".join(ordered) if ordered else None

    def _merge_mapped_fields(
        self, base: Dict[str, Any], updates: Dict[str, Any], prefer_existing: bool
    ) -> Dict[str, Any]:
        """Merge mapped fields with simple conflict resolution."""
        list_fields = {"keywords", "subject_code", "scene_code", "creator"}
        for key, value in updates.items():
            if value in (None, "", []):
                continue
            if key in list_fields:
                existing = base.get(key)
                merged = self._join_list_value(self._split_list_value(existing) + self._split_list_value(value))
                if merged:
                    base[key] = merged
                continue
            if prefer_existing and base.get(key) not in (None, "", []):
                continue
            base[key] = value
        return base

    def _map_iptc_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract IPTC fields for searchability."""
        iptc_fields = self._get_metadata_fields(raw_metadata, "iptc")
        if iptc_fields.get("available") is False:
            return {}
        if not iptc_fields:
            return {}

        data: Dict[str, Any] = {}

        title = self._coerce_text(iptc_fields.get("title"))
        if title:
            data["title"] = title

        headline = self._coerce_text(iptc_fields.get("headline"))
        if headline:
            data["headline"] = headline

        description = self._coerce_text(iptc_fields.get("description"))
        if description:
            data["description"] = description

        keywords = self._join_list_value(self._split_list_value(iptc_fields.get("keywords")))
        if keywords:
            data["keywords"] = keywords

        creator = self._join_list_value(self._split_list_value(iptc_fields.get("creator")))
        if creator:
            data["creator"] = creator

        credit_line = self._coerce_text(iptc_fields.get("credit_line"))
        if credit_line:
            data["credit_line"] = credit_line

        source = self._coerce_text(iptc_fields.get("source"))
        if source:
            data["source"] = source

        instructions = self._coerce_text(iptc_fields.get("instructions"))
        if instructions:
            data["instructions"] = instructions

        rights = self._coerce_text(iptc_fields.get("rights_usage_terms"))
        if rights:
            data["rights_usage_terms"] = rights

        copyright_info = self._coerce_text(iptc_fields.get("copyright"))
        if copyright_info:
            data["copyright"] = copyright_info

        city = self._coerce_text(iptc_fields.get("location_city"))
        if city:
            data["location_city"] = city

        state = self._coerce_text(iptc_fields.get("location_state"))
        if state:
            data["location_state"] = state

        country = self._coerce_text(iptc_fields.get("location_country"))
        if country:
            data["location_country"] = country

        country_code = self._coerce_text(iptc_fields.get("location_country_code"))
        if country_code:
            data["location_country_code"] = country_code

        sublocation = self._coerce_text(iptc_fields.get("location_sublocation"))
        if sublocation:
            data["location_sublocation"] = sublocation

        event = self._coerce_text(iptc_fields.get("event"))
        if event:
            data["event"] = event

        subject_code = self._join_list_value(self._split_list_value(iptc_fields.get("subject_code")))
        if subject_code:
            data["subject_code"] = subject_code

        scene_code = self._join_list_value(self._split_list_value(iptc_fields.get("scene_code")))
        if scene_code:
            data["scene_code"] = scene_code

        genre = self._coerce_text(iptc_fields.get("intellectual_genre"))
        if genre:
            data["intellectual_genre"] = genre

        return data

    def _map_xmp_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract XMP fields for searchability."""
        xmp_fields = self._get_metadata_fields(raw_metadata, "xmp")
        if xmp_fields.get("available") is False:
            return {}
        if not xmp_fields:
            return {}

        data: Dict[str, Any] = {}

        title = self._coerce_text(xmp_fields.get("title"))
        if title:
            data["title"] = title

        headline = self._coerce_text(xmp_fields.get("headline"))
        if headline:
            data["headline"] = headline

        description = self._coerce_text(xmp_fields.get("description"))
        if description:
            data["description"] = description

        keywords = self._join_list_value(self._split_list_value(xmp_fields.get("keywords")))
        if keywords:
            data["keywords"] = keywords

        creator = self._join_list_value(self._split_list_value(xmp_fields.get("creator")))
        if creator:
            data["creator"] = creator

        credit_line = self._coerce_text(xmp_fields.get("credit_line"))
        if credit_line:
            data["credit_line"] = credit_line

        source = self._coerce_text(xmp_fields.get("source"))
        if source:
            data["source"] = source

        instructions = self._coerce_text(xmp_fields.get("instructions"))
        if instructions:
            data["instructions"] = instructions

        rights = self._coerce_text(xmp_fields.get("rights_usage_terms"))
        if rights:
            data["rights_usage_terms"] = rights

        creator_tool = self._coerce_text(xmp_fields.get("creator_tool"))
        if creator_tool:
            data["creator_tool"] = creator_tool

        city = self._coerce_text(xmp_fields.get("location_city"))
        if city:
            data["location_city"] = city

        state = self._coerce_text(xmp_fields.get("location_state"))
        if state:
            data["location_state"] = state

        country = self._coerce_text(xmp_fields.get("location_country"))
        if country:
            data["location_country"] = country

        country_code = self._coerce_text(xmp_fields.get("location_country_code"))
        if country_code:
            data["location_country_code"] = country_code

        sublocation = self._coerce_text(xmp_fields.get("location_sublocation"))
        if sublocation:
            data["location_sublocation"] = sublocation

        event = self._coerce_text(xmp_fields.get("event"))
        if event:
            data["event"] = event

        subject_code = self._join_list_value(self._split_list_value(xmp_fields.get("subject_code")))
        if subject_code:
            data["subject_code"] = subject_code

        scene_code = self._join_list_value(self._split_list_value(xmp_fields.get("scene_code")))
        if scene_code:
            data["scene_code"] = scene_code

        genre = self._coerce_text(xmp_fields.get("intellectual_genre"))
        if genre:
            data["intellectual_genre"] = genre

        return data

    def _generate_composite_fields(self, mapped_data: Dict[str, Any], raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate composite fields for enhanced searchability."""
        composite = {}

        # Generate exposure triangle
        iso = mapped_data.get("iso")
        aperture = mapped_data.get("aperture")
        shutter = mapped_data.get("shutter_speed")

        if iso and aperture and shutter:
            composite["exposure_triangle"] = f"ISO {iso}, f/{aperture}, {shutter}"

        # Generate searchable text field
        searchable_parts = []

        # Add camera info
        if mapped_data.get("camera_make"):
            searchable_parts.append(mapped_data["camera_make"])
        if mapped_data.get("camera_model"):
            searchable_parts.append(mapped_data["camera_model"])

        # Add lens info
        if mapped_data.get("lens_model"):
            searchable_parts.append(mapped_data["lens_model"])

        # Add exposure info
        if composite.get("exposure_triangle"):
            searchable_parts.append(composite["exposure_triangle"])

        # Add software info
        if mapped_data.get("software"):
            searchable_parts.append(mapped_data["software"])

        # Add copyright info
        if mapped_data.get("creator"):
            searchable_parts.append(mapped_data["creator"])

        # Add IPTC/XMP content info
        for field in ["title", "headline", "keywords", "location_city", "location_state", "location_country", "event"]:
            value = mapped_data.get(field)
            if value:
                searchable_parts.append(str(value))

        if searchable_parts:
            composite["searchable_text"] = " ".join(searchable_parts)

        return composite

    # Helper methods for parsing specific EXIF values

    def _parse_iso(self, iso_value: Any) -> Optional[int]:
        """Parse ISO value to integer."""
        try:
            if isinstance(iso_value, (list, tuple)) and len(iso_value) > 0:
                iso_value = iso_value[0]
            return int(float(str(iso_value)))
        except (ValueError, TypeError):
            return None

    def _parse_aperture(self, aperture_value: Any) -> Optional[float]:
        """Parse aperture value to float."""
        try:
            if isinstance(aperture_value, str):
                # Handle fraction format like "28/10"
                if "/" in aperture_value:
                    fraction = Fraction(aperture_value)
                    return float(fraction)
                return float(aperture_value)
            return float(aperture_value)
        except (ValueError, TypeError):
            return None

    def _parse_shutter_speed(self, shutter_value: Any) -> Tuple[Optional[str], Optional[float]]:
        """Parse shutter speed to display format and decimal value."""
        try:
            if isinstance(shutter_value, str):
                # Handle fraction format like "1/250"
                if "/" in shutter_value:
                    fraction = Fraction(shutter_value)
                    decimal = float(fraction)
                    # Format for display
                    if decimal >= 1:
                        display = f"{decimal:.1f}s"
                    else:
                        # Convert back to fraction for display
                        display = shutter_value
                    return display, decimal
                else:
                    decimal = float(shutter_value)
                    display = f"{decimal:.3f}s" if decimal >= 1 else f"1/{int(1/decimal)}"
                    return display, decimal
            else:
                decimal = float(shutter_value)
                if decimal >= 1:
                    display = f"{decimal:.1f}s"
                else:
                    display = f"1/{int(1/decimal)}"
                return display, decimal
        except (ValueError, TypeError):
            return None, None

    def _parse_exposure_compensation(self, exp_comp_value: Any) -> Optional[float]:
        """Parse exposure compensation to float."""
        try:
            if isinstance(exp_comp_value, str) and "/" in exp_comp_value:
                fraction = Fraction(exp_comp_value)
                return float(fraction)
            return float(exp_comp_value)
        except (ValueError, TypeError):
            return None

    def _parse_focal_length(self, focal_value: Any) -> Optional[float]:
        """Parse focal length to float (in mm)."""
        try:
            if isinstance(focal_value, str) and "/" in focal_value:
                fraction = Fraction(focal_value)
                return float(fraction)
            return float(focal_value)
        except (ValueError, TypeError):
            return None

    def _parse_focal_length_35mm(self, focal_35mm_value: Any) -> Optional[int]:
        """Parse 35mm equivalent focal length to integer."""
        try:
            return int(float(str(focal_35mm_value)))
        except (ValueError, TypeError):
            return None

    def _parse_exposure_mode(self, mode_value: Any) -> Optional[str]:
        """Parse exposure mode to readable string."""
        mode_map = {
            "0": "Auto",
            "1": "Manual",
            "2": "Aperture Priority",
            "3": "Shutter Priority",
            "4": "Creative Program",
            "5": "Action Program",
            "6": "Portrait Program",
            "7": "Landscape Program",
        }

        mode_str = str(mode_value).strip()
        return mode_map.get(mode_str, mode_str)

    def _parse_metering_mode(self, metering_value: Any) -> Optional[str]:
        """Parse metering mode to readable string."""
        metering_map = {
            "0": "Unknown",
            "1": "Average",
            "2": "Center-weighted",
            "3": "Spot",
            "4": "Multi-spot",
            "5": "Multi-segment",
            "6": "Partial",
        }

        metering_str = str(metering_value).strip()
        return metering_map.get(metering_str, metering_str)

    def _parse_flash(self, flash_value: Any) -> Tuple[bool, Optional[str]]:
        """Parse flash information to boolean and mode string."""
        try:
            flash_int = int(str(flash_value))
            flash_used = (flash_int & 0x01) != 0  # Bit 0 indicates if flash fired

            # Determine flash mode based on other bits
            if flash_int & 0x08:  # Bit 3
                mode = "Compulsory"
            elif flash_int & 0x10:  # Bit 4
                mode = "Compulsory (no flash)"
            elif flash_int & 0x18:  # Bits 3 and 4
                mode = "Auto"
            else:
                mode = "Auto" if flash_used else "No flash"

            return flash_used, mode
        except (ValueError, TypeError):
            return False, None

    def _parse_white_balance(self, wb_value: Any) -> Optional[str]:
        """Parse white balance to readable string."""
        wb_map = {
            "0": "Auto",
            "1": "Manual",
            "2": "Daylight",
            "3": "Cloudy",
            "4": "Tungsten",
            "5": "Fluorescent",
            "6": "Flash",
        }

        wb_str = str(wb_value).strip()
        return wb_map.get(wb_str, wb_str)

    def _parse_color_temperature(self, temp_value: Any) -> Optional[int]:
        """Parse color temperature to integer (Kelvin)."""
        try:
            return int(float(str(temp_value)))
        except (ValueError, TypeError):
            return None

    def _parse_color_space(self, color_space_value: Any) -> Optional[str]:
        """Parse color space to readable string."""
        cs_map = {"1": "sRGB", "2": "Adobe RGB", "65535": "Uncalibrated"}

        cs_str = str(color_space_value).strip()
        return cs_map.get(cs_str, cs_str)

    def _infer_bit_depth(self, image_mode: str) -> Optional[int]:
        """Infer bit depth from PIL image mode."""
        mode_map = {
            "1": 1,  # 1-bit pixels, black and white
            "L": 8,  # 8-bit pixels, black and white
            "P": 8,  # 8-bit pixels, mapped to any other mode using a color palette
            "RGB": 8,  # 3x8-bit pixels, true color
            "RGBA": 8,  # 4x8-bit pixels, true color with transparency mask
            "CMYK": 8,  # 4x8-bit pixels, color separation
            "YCbCr": 8,  # 3x8-bit pixels, color video format
            "LAB": 8,  # 3x8-bit pixels, the L*a*b* color space
            "HSV": 8,  # 3x8-bit pixels, Hue, Saturation, Value color space
            "I": 32,  # 32-bit signed integer pixels
            "F": 32,  # 32-bit floating point pixels
        }

        return mode_map.get(image_mode)


def map_metadata_to_searchable_fields(raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to map raw metadata to searchable fields.

    Args:
        raw_metadata: Raw metadata from metadata_extractor

    Returns:
        Dictionary of normalized searchable fields
    """
    mapper = MetadataMapper()
    return mapper.map_metadata(raw_metadata)


if __name__ == "__main__":
    # Test the mapper with sample data
    import json

    sample_metadata = {
        "exif": {
            "image": {
                "Make": "CANON",
                "Model": "Canon EOS R5",
                "Software": "Adobe Lightroom Classic 11.0",
                "Artist": "John Photographer",
                "Copyright": "© 2024 John Photographer",
            },
            "exif": {
                "LensModel": "RF24-70mm F2.8 L IS USM",
                "ISOSpeedRatings": "400",
                "FNumber": "28/10",
                "ExposureTime": "1/250",
                "FocalLength": "50/1",
                "Flash": "16",
                "WhiteBalance": "0",
                "ExposureMode": "1",
            },
        },
        "image": {"format": "JPEG", "mode": "RGB"},
    }

    mapper = MetadataMapper()
    result = mapper.map_metadata(sample_metadata)

    print("Mapped metadata:")
    print(json.dumps(result, indent=2))
