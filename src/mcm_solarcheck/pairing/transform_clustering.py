"""Cluster numerically different homographies by their projected image geometry."""
from __future__ import annotations
from dataclasses import dataclass
from math import hypot
from .grid_hypothesis_validation import GridHypothesisEstimate
from .registration import project_homography

@dataclass(frozen=True)
class TransformCluster:
    representative:GridHypothesisEstimate
    members:tuple[GridHypothesisEstimate,...]

def _probe_points(width:float,height:float):
    if width<=0 or height<=0:raise ValueError('image dimensions must be positive')
    # Corners, edge midpoints and centre make translation, scale, rotation and
    # perspective differences observable across the full thermal image.
    return ((0.,0.),(width,0.),(width,height),(0.,height),
            (width/2,0.),(width,height/2),(width/2,height),(0.,height/2),
            (width/2,height/2))

def _matrix(e):
    m=e.estimate.transform.matrix
    return None if m is None else tuple(v for row in m for v in row)

def transform_distance_px(a:GridHypothesisEstimate,b:GridHypothesisEstimate,width:float,height:float)->float:
    """Maximum projection separation over deterministic full-image probes."""
    ma,mb=_matrix(a),_matrix(b)
    if ma is None or mb is None:return float('inf')
    distances=[]
    for x,y in _probe_points(width,height):
        ax,ay=project_homography(ma,x,y);bx,by=project_homography(mb,x,y)
        distances.append(hypot(ax-bx,ay-by))
    return max(distances)

def cluster_grid_transforms(estimates:tuple[GridHypothesisEstimate,...],width:float,height:float,*,maximum_projection_difference_px:float=3.0)->tuple[TransformCluster,...]:
    """Group only transforms that agree over the complete thermal image.

    Complete-link membership prevents chaining several individually-close
    transforms into one physically broad cluster.
    """
    if maximum_projection_difference_px<=0:raise ValueError('maximum_projection_difference_px must be positive')
    _probe_points(width,height)  # validate dimensions even for empty input
    clusters=[]
    for estimate in estimates:
        placed=False
        for i,cluster in enumerate(clusters):
            if all(transform_distance_px(estimate,m,width,height)<=maximum_projection_difference_px for m in cluster.members):
                clusters[i]=TransformCluster(cluster.representative,cluster.members+(estimate,))
                placed=True;break
        if not placed:clusters.append(TransformCluster(estimate,(estimate,)))
    return tuple(clusters)
