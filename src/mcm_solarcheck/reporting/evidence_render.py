"""Render report evidence without modifying original flight imagery."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw
from .evidence import EvidenceImagePlan

@dataclass(frozen=True)
class RenderedEvidence:
    finding_id:str
    thermal_image:Path
    rgb_image:Path|None


def _crop_box(width:int,height:int,x:float,y:float,half_size:int)->tuple[int,int,int,int]:
    if half_size<=0:raise ValueError('half_size must be positive')
    left=max(0,int(round(x))-half_size);top=max(0,int(round(y))-half_size)
    right=min(width,int(round(x))+half_size);bottom=min(height,int(round(y))+half_size)
    if right<=left or bottom<=top:raise ValueError('marker lies outside source image')
    return left,top,right,bottom


def _render_crop(source:Path,marker:tuple[float,float],target:Path,half_size:int)->Path:
    with Image.open(source) as image:
        image.seek(0);rgb=image.convert('RGB');box=_crop_box(rgb.width,rgb.height,*marker,half_size)
        crop=rgb.crop(box);mx=marker[0]-box[0];my=marker[1]-box[1]
        draw=ImageDraw.Draw(crop);radius=max(5,min(crop.size)//30);width=max(2,radius//3)
        draw.ellipse((mx-radius,my-radius,mx+radius,my+radius),outline=(255,0,0),width=width)
        draw.line((mx-radius*2,my,mx+radius*2,my),fill=(255,0,0),width=width)
        draw.line((mx,my-radius*2,mx,my+radius*2),fill=(255,0,0),width=width)
        target.parent.mkdir(parents=True,exist_ok=True);crop.save(target,'JPEG',quality=92)
    return target


def render_evidence(plan:EvidenceImagePlan,output_dir:str|Path,*,thermal_half_size:int=120,rgb_half_size:int=500)->RenderedEvidence:
    """Render marked crops; RGB output exists only for a validated RGB marker."""
    output=Path(output_dir);safe=''.join(c if c.isalnum() or c in '-_' else '_' for c in plan.finding_id)
    thermal_target=output/f'{safe}_thermal.jpg'
    _render_crop(plan.thermal_source,(float(plan.thermal_pixel[0]),float(plan.thermal_pixel[1])),thermal_target,thermal_half_size)
    rgb_target=None
    if plan.rgb_source is not None and plan.rgb_marker is not None:
        rgb_target=output/f'{safe}_rgb.jpg';_render_crop(plan.rgb_source,plan.rgb_marker,rgb_target,rgb_half_size)
    return RenderedEvidence(plan.finding_id,thermal_target,rgb_target)
