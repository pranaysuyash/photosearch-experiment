from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def patch_insightface_deprecations() -> None:
    try:
        import insightface.utils.face_align as face_align  # type: ignore[import-untyped]
        from skimage import transform as trans  # type: ignore[import-untyped]
    except Exception:
        return

    if getattr(face_align, "_patched_deprecations", False):
        return

    if not hasattr(trans.SimilarityTransform, "from_estimate"):
        return

    def estimate_norm(lmk, image_size=112, mode="arcface"):
        assert lmk.shape == (5, 2)
        assert image_size % 112 == 0 or image_size % 128 == 0
        if image_size % 112 == 0:
            ratio = float(image_size) / 112.0
            diff_x = 0
        else:
            ratio = float(image_size) / 128.0
            diff_x = 8.0 * ratio
        dst = face_align.arcface_dst * ratio
        dst[:, 0] += diff_x
        tform = trans.SimilarityTransform.from_estimate(lmk, dst)
        M = tform.params[0:2, :]
        return M

    face_align.estimate_norm = estimate_norm
    face_align._patched_deprecations = True
