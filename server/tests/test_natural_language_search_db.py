from pathlib import Path

from server.face_clustering_db import FaceClusteringDB


def test_search_photos_by_natural_language_filters(tmp_path):
    db_path = tmp_path / "face_clusters.db"
    face_db = FaceClusteringDB(Path(db_path))

    john_id = face_db.add_face_cluster(label="John")
    mary_id = face_db.add_face_cluster(label="Mary")

    photo_one = "/unit/test/photo_one.jpg"
    photo_two = "/unit/test/photo_two.jpg"

    detection_one = face_db.add_face_detection(
        photo_path=photo_one,
        bounding_box={"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
        embedding=[0.1] * 8,
        quality_score=0.9,
        age_estimate=30,
        emotion="happy",
        emotion_confidence=0.9,
    )
    detection_two = face_db.add_face_detection(
        photo_path=photo_one,
        bounding_box={"x": 0.4, "y": 0.1, "width": 0.2, "height": 0.2},
        embedding=[0.2] * 8,
        quality_score=0.85,
        age_estimate=28,
        emotion="happy",
        emotion_confidence=0.85,
    )
    detection_three = face_db.add_face_detection(
        photo_path=photo_two,
        bounding_box={"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
        embedding=[0.3] * 8,
        quality_score=0.8,
        age_estimate=35,
        emotion="sad",
        emotion_confidence=0.9,
    )

    face_db.associate_person_with_photo(photo_one, john_id, detection_one, 0.95)
    face_db.associate_person_with_photo(photo_one, mary_id, detection_two, 0.92)
    face_db.associate_person_with_photo(photo_two, john_id, detection_three, 0.88)

    result = face_db.search_photos_by_natural_language(
        include_names=["John"],
        emotions=["happy"],
        limit=10,
        offset=0,
    )

    assert result["total"] == 1
    assert result["photos"][0]["photo_path"] == photo_one

    group_result = face_db.search_photos_by_natural_language(
        exact_people=2,
        limit=10,
        offset=0,
    )

    assert group_result["total"] == 1
    assert group_result["photos"][0]["photo_path"] == photo_one

    exclude_result = face_db.search_photos_by_natural_language(
        include_names=["John"],
        exclude_names=["Mary"],
        limit=10,
        offset=0,
    )

    assert exclude_result["total"] == 1
    assert exclude_result["photos"][0]["photo_path"] == photo_two
