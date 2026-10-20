"""
Face Blur Processor - Handles blurring of detected faces in images for privacy

Provides functionality to blur faces in photos during export based on detected
face bounding boxes from the face clustering database.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)


class FaceBlurProcessor:
    """Process and blur detected faces in images"""

    def __init__(self, face_db_path: str):
        """
        Initialize the face blur processor.

        Args:
            face_db_path: Path to the face clustering database
        """
        self.db_path = Path(face_db_path)

    def get_face_bounding_boxes(self, photo_path: str) -> list[dict]:
        """
        Get all detected face bounding boxes for a photo.

        Args:
            photo_path: Path to the photo

        Returns:
            List of bounding box dictionaries with x, y, width, height
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Query face detections for this photo
                cursor.execute(
                    """
                    SELECT bounding_box
                    FROM face_detections
                    WHERE photo_path = ?
                    """,
                    (photo_path,),
                )

                rows = cursor.fetchall()
                bounding_boxes = []

                for row in rows:
                    try:
                        import json

                        bbox_data = json.loads(row["bounding_box"])
                        if isinstance(bbox_data, dict) and all(
                            key in bbox_data for key in ["x", "y", "width", "height"]
                        ):
                            bounding_boxes.append(bbox_data)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        # Skip invalid bounding box data
                        continue

                return bounding_boxes

        except Exception as e:
            logger.error(f"Error retrieving face bounding boxes for {photo_path}: {e}")
            return []

    def blur_image(
        self,
        image_path: str,
        blur_strength: int = 10,
        output_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Apply face blur to an image and return the processed image bytes.

        Args:
            image_path: Path to the input image
            blur_strength: Blur radius (1-50, default 10)
            output_path: Optional path to save the blurred image

        Returns:
            Bytes of the blurred image, or None if processing failed
        """
        try:
            # Ensure blur strength is in valid range
            blur_strength = max(1, min(50, blur_strength))

            # Open the image
            with Image.open(image_path) as img:
                # Get image dimensions
                img_width, img_height = img.size

                # Get face bounding boxes
                bounding_boxes = self.get_face_bounding_boxes(image_path)

                if not bounding_boxes:
                    # No faces to blur, return original image
                    logger.info(f"No faces detected in {image_path}")
                    if output_path:
                        img.save(output_path)
                        with open(output_path, "rb") as f:
                            return f.read()
                    else:
                        import io

                        buffer = io.BytesIO()
                        img.save(buffer, format=img.format)
                        return buffer.getvalue()

                # Create a copy for processing
                blurred_img = img.copy()

                # Blur each detected face
                for bbox in bounding_boxes:
                    try:
                        # Convert normalized coordinates to pixel coordinates
                        x = max(0, int(bbox["x"] * img_width))
                        y = max(0, int(bbox["y"] * img_height))
                        width = max(1, int(bbox["width"] * img_width))
                        height = max(1, int(bbox["height"] * img_height))

                        # Ensure coordinates are within bounds
                        x2 = min(img_width, x + width)
                        y2 = min(img_height, y + height)

                        # Extract face region
                        face_region = blurred_img.crop((x, y, x2, y2))

                        # Apply Gaussian blur
                        blurred_face = face_region.filter(ImageFilter.GaussianBlur(radius=blur_strength))

                        # Paste the blurred face back
                        blurred_img.paste(blurred_face, (x, y))

                    except Exception as e:
                        logger.warning(f"Failed to blur face region: {e}")
                        continue

                # Save or return the blurred image
                if output_path:
                    blurred_img.save(output_path)
                    with open(output_path, "rb") as f:
                        return f.read()
                else:
                    import io

                    buffer = io.BytesIO()
                    blurred_img.save(buffer, format=img.format or "JPEG")
                    return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error blurring image {image_path}: {e}")
            return None

    def blur_image_inplace(self, image_path: str, blur_strength: int = 10) -> bool:
        """
        Apply face blur to an image in place, overwriting the original.

        Args:
            image_path: Path to the image to blur
            blur_strength: Blur radius (1-50)

        Returns:
            True if successful, False otherwise
        """
        try:
            blurred_bytes = self.blur_image(image_path, blur_strength)
            if blurred_bytes:
                Path(image_path).write_bytes(blurred_bytes)
                return True
            return False
        except Exception as e:
            logger.error(f"Error applying blur in place to {image_path}: {e}")
            return False
