from typing import List

from pydantic import BaseModel


class FaceClusterRequest(BaseModel):
    image_paths: List[str]
    eps: float = 0.6
    min_samples: int = 2


class ClusterLabelRequest(BaseModel):
    cluster_id: int
    label: str
