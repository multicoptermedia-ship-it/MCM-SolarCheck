"""Bounded overlapping RGB tiles with native pixel coordinates and no stitching.

Only detections are transformed/filtered. Original RGB/GeoTIFF pixels, CRS and
thermal values are untouched. Several views of the same pixels are not
independent evidence and never increase confidence automatically.
"""
from dataclasses import dataclass
from math import floor,ceil
import numpy as np

from .detection import ModuleDetection
from .module_quality import assess_module_detection,filter_module_detections
from ..services.orthophoto_pv_modules import _polygon_mask

PROFILE=dict(id='rgb-fixed-grid-multiscale-overlap-2',input_size=256,
    source_tile_sizes=(1024,512),overlap_fraction=.5,internal_edge_margin=8,
    coordinate_mapping='(model_center+.5)*scale-.5+native_origin',
    confidence_boost=False,duplicate_iou=.5,source_pixels_modified=False)


@dataclass(frozen=True)
class ModuleTile:
    left:int
    top:int
    size:int


def tile_plan(width,height,*,sizes=(1024,512),maximum_tiles=4096):
    if (type(width) is not int or type(height) is not int or min(width,height)<1
            or max(width,height)>1_000_000 or type(sizes) is not tuple
            or not sizes or len(set(sizes))!=len(sizes)
            or any(type(s) is not int or s not in (256,512,1024) for s in sizes)
            or type(maximum_tiles) is not int or not 1<=maximum_tiles<=4096):
        raise ValueError('Bounded native image dimensions and explicit tile scales required')
    def positions(length,size):
        if length<=size:return (0,)
        steps, remainder = divmod(length-size, size//2)
        if steps+1+bool(remainder)>maximum_tiles:
            raise ValueError('Tile budget exceeded; no partial analysis result')
        return tuple(sorted(set((*range(0,length-size+1,size//2),length-size))))
    result=[]
    for size in sizes:
        xs,ys=positions(width,size),positions(height,size)
        if len(result)+len(xs)*len(ys)>maximum_tiles:
            raise ValueError('Tile budget exceeded; no partial analysis result')
        result.extend(ModuleTile(x,y,size) for y in ys for x in xs)
    return tuple(result)


def _input(rgb,tile):
    image=np.zeros((tile.size,tile.size,3),np.uint8)
    source=rgb[tile.top:tile.top+tile.size,tile.left:tile.left+tile.size]
    image[:source.shape[0],:source.shape[1]]=source
    if tile.size==256:return image
    # Preserve the existing half-up2xRGB reduction without touching its
    # source-bound public training adapter or asking for reference labels.
    factor=tile.size//256
    return ((image.reshape(256,factor,256,factor,3).astype(np.uint16).sum((1,3))
             +factor*factor//2)//(factor*factor)).astype(np.uint8)


def native_detection(detection,tile):
    scale=tile.size/256
    return ModuleDetection(tuple(((x+.5)*scale-.5+tile.left,
                                  (y+.5)*scale-.5+tile.top)
                                 for x,y in detection.polygon_px),detection.confidence,
                           detection.class_name)


def _supported(polygon,valid):
    height,width=valid.shape
    xs,ys=zip(*polygon)
    left,top=max(0,floor(min(xs))),max(0,floor(min(ys)))
    right,bottom=min(width,ceil(max(xs))+1),min(height,ceil(max(ys))+1)
    if right<=left or bottom<=top:return False
    footprint=_polygon_mask(polygon,width=right-left,height=bottom-top,left=left,top=top)
    return bool(np.any(footprint) and np.all(valid[top:bottom,left:right][footprint]))


def spatial_duplicates(detections,width,height,*,should_cancel=lambda:False,metric='iou'):
    """Reuse the existing polygon-IoU filter, querying only nearby kept objects."""
    if metric not in ('iou','ios'):raise ValueError('Explicit supported tile duplicate metric required')
    threshold=.5 if metric=='iou' else .8
    valid=[d for d in detections if d.class_name=='pv_module'
        and assess_module_detection(d,width,height,minimum_area_fraction=16/(width*height),
            maximum_area_fraction=1.).accepted]
    ordered=sorted(valid,key=lambda d:(-d.confidence,
        sum(x for x,_ in d.polygon_px)/len(d.polygon_px),
        sum(y for _,y in d.polygon_px)/len(d.polygon_px)))
    kept=[];bins={};rejected=len(detections)-len(valid)
    for detection in ordered:
        if should_cancel():raise KeyboardInterrupt
        xs,ys=zip(*detection.polygon_px)
        cells=[(x,y) for y in range(floor(min(ys)/256),floor(max(ys)/256)+1)
                     for x in range(floor(min(xs)/256),floor(max(xs)/256)+1)]
        neighbors=sorted({index for cell in cells for index in bins.get(cell,())})
        accepted=filter_module_detections(tuple(kept[i] for i in neighbors)+(detection,),width,height,
            duplicate_iou=threshold,minimum_area_fraction=16/(width*height),maximum_area_fraction=1.,duplicate_metric=metric)
        if not any(d is detection for d in accepted):
            rejected+=1;continue
        index=len(kept);kept.append(detection)
        for cell in cells:bins.setdefault(cell,[]).append(index)
    return tuple(kept),rejected


def detect_tiles(rgb,detector,*,valid_pixels=None,sizes=(1024,512),
                 maximum_tiles=4096,should_cancel=lambda:False,progress=lambda done,total:None,duplicate_metric='iou'):
    if (not isinstance(rgb,np.ndarray) or rgb.dtype!=np.uint8 or rgb.ndim!=3 or rgb.shape[2]!=3):
        raise ValueError('Native uint8 RGB required')
    height,width=rgb.shape[:2]
    if width*height>64_000_000:raise ValueError('Use a native window reader for larger source images')
    if valid_pixels is not None and (not isinstance(valid_pixels,np.ndarray) or valid_pixels.dtype!=np.bool_
            or valid_pixels.shape!=(height,width)):
        raise ValueError('Source validity mask must match native RGB, not reference labels')
    def read(window):
        left,top,w,h=window
        return (rgb[top:top+h,left:left+w],np.ones((h,w),bool) if valid_pixels is None
                else valid_pixels[top:top+h,left:left+w])
    return detect_tile_reader(width,height,read,detector,sizes=sizes,maximum_tiles=maximum_tiles,
        should_cancel=should_cancel,progress=progress,duplicate_metric=duplicate_metric)


def detect_tile_reader(width,height,reader,detector,*,sizes=(1024,512),maximum_tiles=4096,
                       should_cancel=lambda:False,progress=lambda done,total:None,duplicate_metric='iou'):
    """Read only bounded native windows, e.g. through the existing GeoTIFF reader.

    reader receives (left, top, width, height), returns native RGB and actual
    RGB validity. It never receives model/reference labels or changes the CRS.
    """
    if duplicate_metric not in ('iou','ios'):raise ValueError('Explicit supported tile duplicate metric required')
    plan=tile_plan(width,height,sizes=sizes,maximum_tiles=maximum_tiles)
    rows=[];candidates=[];totals=dict(returned=0,internal_edge=0,nodata_or_outside=0)
    for number,tile in enumerate(plan,1):
        if should_cancel():raise KeyboardInterrupt
        w,h=min(tile.size,width-tile.left),min(tile.size,height-tile.top)
        source=reader((tile.left,tile.top,w,h))
        if (not isinstance(source,tuple) or len(source)!=2
                or not isinstance(source[0],np.ndarray) or source[0].dtype!=np.uint8
                or source[0].shape!=(h,w,3) or not isinstance(source[1],np.ndarray)
                or source[1].dtype!=np.bool_ or source[1].shape!=(h,w)):
            raise ValueError('Native window RGB/validity dimensions differ')
        pixels,valid=source
        result=detector(_input(pixels,ModuleTile(0,0,tile.size)))
        if (not isinstance(result,tuple) or len(result)>300
                or any(not isinstance(d,ModuleDetection) for d in result)):
            raise ValueError('Bounded tuple of local module proposals required')
        totals['returned']+=len(result)
        if totals['returned']>50_000:raise ValueError('Candidate budget exceeded; no partial result')
        for detection in result:
            xs,ys=zip(*detection.polygon_px)
            if ((tile.left>0 and min(xs)<8) or (tile.top>0 and min(ys)<8)
                    or (tile.left+tile.size<width and max(xs)>247)
                    or (tile.top+tile.size<height and max(ys)>247)):
                totals['internal_edge']+=1;continue
            mapped=native_detection(detection,tile)
            local=tuple((x-tile.left,y-tile.top) for x,y in mapped.polygon_px)
            if (not assess_module_detection(mapped,width,height,minimum_area_fraction=16/(width*height),
                    maximum_area_fraction=1.).accepted or not _supported(local,valid)):
                totals['nodata_or_outside']+=1;continue
            candidates.append(mapped)
        rows.append(dict(left=tile.left,top=tile.top,size=tile.size,returned=len(result)))
        progress(number,len(plan))
    kept,suppressed=spatial_duplicates(tuple(candidates),width,height,
        should_cancel=should_cancel,metric=duplicate_metric)
    if should_cancel():raise KeyboardInterrupt
    return kept,dict(profile=dict(PROFILE,source_tile_sizes=sizes,duplicate_metric=duplicate_metric,
        duplicate_threshold=.5 if duplicate_metric=='iou' else .8),planned_tiles=len(plan),processed_tiles=len(rows),
        tiles=rows,**totals,duplicate_or_geometry_suppressed=suppressed,kept=len(kept),
        coverage_verified=False,accuracy_verified=False,physical_module_ids_confirmed=False)
