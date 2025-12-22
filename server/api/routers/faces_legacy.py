from fastapi import APIRouter, HTTPException, Depends

from server.models.schemas.faces import ClusterLabelRequest, FaceClusterRequest
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/faces/cluster")
async def cluster_faces_v1(request: FaceClusterRequest, state: AppState = Depends(get_state)):
    """
    Cluster faces in the specified images

    Args:
        request: FaceClusterRequest with image paths and clustering parameters

    Returns:
        Dictionary with clustering results
    """
    try:

        clusters = state.face_clusterer.cluster_faces(
            request.image_paths,
            eps=request.eps,
            min_samples=request.min_samples,
        )
        return {"status": "success", "clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faces/clusters")
async def get_all_clusters(limit: int = 100, offset: int = 0, state: AppState = Depends(get_state)):
    """
    Get all face clusters

    Args:
        limit: Maximum number of clusters to return
        offset: Pagination offset

    Returns:
        Dictionary with cluster information
    """
    try:

        clusters = state.face_clusterer.get_all_clusters(limit, offset)
        return {"status": "success", "clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faces/clusters/{cluster_id}")
async def get_cluster_details(cluster_id: int, state: AppState = Depends(get_state)):
    """
    Get details for a specific cluster

    Args:
        cluster_id: ID of the cluster

    Returns:
        Dictionary with cluster details
    """
    try:

        details = state.face_clusterer.get_cluster_details(cluster_id)
        return {"status": "success", "details": details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faces/image/{image_path:path}")
async def get_image_clusters(image_path: str, state: AppState = Depends(get_state)):
    """
    Get face clusters for a specific image

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with face cluster information for the image
    """
    try:

        clusters = state.face_clusterer.get_face_clusters(image_path)
        return {"status": "success", "clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/faces/clusters/{cluster_id}/label")
async def update_cluster_label(cluster_id: int, request: ClusterLabelRequest, state: AppState = Depends(get_state)):
    """
    Update the label for a cluster

    Args:
        cluster_id: ID of the cluster
        request: ClusterLabelRequest with new label

    Returns:
        Dictionary with update status
    """
    try:

        success = state.face_clusterer.update_cluster_label(cluster_id, request.label)
        return {"status": "success" if success else "failed", "updated": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/faces/clusters/{cluster_id}")
async def delete_cluster(cluster_id: int, state: AppState = Depends(get_state)):
    """
    Delete a face cluster

    Args:
        cluster_id: ID of the cluster to delete

    Returns:
        Dictionary with deletion status
    """
    try:

        success = state.face_clusterer.delete_cluster(cluster_id)
        return {"status": "success" if success else "failed", "deleted": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faces/stats")
async def get_face_stats_v1(state: AppState = Depends(get_state)):
    """
    Get statistics about face clusters

    Returns:
        Dictionary with face clustering statistics
    """
    try:

        stats = state.face_clusterer.get_cluster_statistics()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
