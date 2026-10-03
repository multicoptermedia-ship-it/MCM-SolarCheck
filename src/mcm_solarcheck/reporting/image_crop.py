"""Safe report-image crop geometry without inventing cross-sensor alignment."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class CropBox:
    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self):
        if any(isinstance(v,bool) or not isinstance(v,int) for v in (self.left,self.top,self.right,self.bottom)):
            raise ValueError("crop coordinates must be integers")
        if self.left < 0 or self.top < 0 or self.right <= self.left or self.bottom <= self.top:
            raise ValueError("invalid crop box")


def polygon_crop_box(polygon, width: int, height: int, *, padding_fraction: float=0.12) -> CropBox:
    """Return a clamped module crop. Polygon coordinates must belong to this exact frame."""
    if width <= 0 or height <= 0: raise ValueError("image dimensions must be positive")
    points=tuple(polygon)
    if len(points) < 3: raise ValueError("module polygon requires at least three points")
    xs=[]; ys=[]
    for point in points:
        if len(point)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(float(v)) for v in point):
            raise ValueError("module polygon must contain finite x/y coordinates")
        xs.append(float(point[0])); ys.append(float(point[1]))
    if not 0 <= padding_fraction <= 1: raise ValueError("padding_fraction must be between 0 and 1")
    x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
    pad_x=max(1.0,(x1-x0)*padding_fraction); pad_y=max(1.0,(y1-y0)*padding_fraction)
    left=max(0,int(x0-pad_x)); top=max(0,int(y0-pad_y))
    right=min(width,int(x1+pad_x+0.999999)); bottom=min(height,int(y1+pad_y+0.999999))
    if right <= left or bottom <= top: raise ValueError("module polygon is outside image bounds")
    return CropBox(left,top,right,bottom)
