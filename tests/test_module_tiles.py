"""Generated full-image grid, native coordinates, seam recovery and cancellation."""
import numpy as np
import pytest

from mcm_solarcheck.vision.module_tiles import (
    ModuleTile,tile_plan,native_detection,detect_tiles,detect_tile_reader,spatial_duplicates,_input)
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_quality import filter_module_detections


def detection(x=40,y=40,w=80,h=40,score=.9):
    return ModuleDetection(((x,y),(x+w,y),(x+w,y+h),(x,y+h)),score)


@pytest.mark.parametrize('shape',[(512,512),(777,413),(2048,1024),(300,180)])
def test_fixed_grid_covers_rectangular_image_without_source_changes(shape):
    width,height=shape;plan=tile_plan(width,height)
    covered=np.zeros((height,width),bool)
    for tile in plan:covered[tile.top:tile.top+tile.size,tile.left:tile.left+tile.size]=True
    assert covered.all()
    assert len(plan)==len(set(plan))
    assert all(t.left>=0 and t.top>=0 and t.left<width and t.top<height for t in plan)


def test_half_pixel_mapping_preserves_the_original_native_pixel_centers():
    local=detection(10,20)
    coarse=native_detection(local,ModuleTile(128,256,512))
    assert coarse.polygon_px[0]==(148.5,296.5)
    fine=native_detection(local,ModuleTile(128,256,256))
    assert fine.polygon_px[0]==(138.,276.)
    assert coarse.confidence==fine.confidence==local.confidence


def test_2x_reduction_retains_existing_half_up_pixel_rounding():
    rgb=np.zeros((512,512,3),np.uint8);rgb[0,0]=1;rgb[1,0]=1
    assert np.all(_input(rgb,ModuleTile(0,0,512))[0,0]==1)
    assert rgb[0,0,0]==rgb[1,0,0]==1


def test_padding_never_distorts_a_rectangular_source_or_leaks_outside():
    rgb=np.full((180,300,3),77,np.uint8);original=rgb.copy()
    result,report=detect_tiles(rgb,lambda image:(),sizes=(256,))
    assert result==() and report['processed_tiles']==2
    assert np.array_equal(rgb,original)


def test_seam_fragment_is_deferred_to_neighboring_overlapping_tile():
    rgb=np.zeros((256,384,3),np.uint8);calls=[]
    def model(image):
        calls.append(1)
        return (detection(190,50,63,50),) if len(calls)==1 else (detection(62,50,80,50),)
    result,report=detect_tiles(rgb,model,sizes=(256,))
    assert len(result)==1 and result[0].polygon_px[0]==(190.,50.)
    assert report['internal_edge']==1


def test_overlap_duplicates_do_not_inflate_confidence_or_module_count():
    rgb=np.zeros((256,384,3),np.uint8);calls=[]
    def model(image):
        calls.append(1)
        return (detection(150,50,60,40,.8),) if len(calls)==1 else (detection(22,50,60,40,.9),)
    result,report=detect_tiles(rgb,model,sizes=(256,))
    assert len(result)==1 and result[0].confidence==.9
    assert report['duplicate_or_geometry_suppressed']==1
    assert report['coverage_verified'] is False and report['physical_module_ids_confirmed'] is False


def test_actual_nodata_blocks_proposals_and_reference_masks_are_not_model_inputs():
    rgb=np.zeros((256,256,3),np.uint8);valid=np.ones((256,256),bool);valid[50,50]=False
    calls=[]
    def model(image):
        calls.append(image.shape)
        return (detection(),)
    result,report=detect_tiles(rgb,model,valid_pixels=valid,sizes=(256,))
    assert result==() and report['nodata_or_outside']==1 and calls==[(256,256,3)]


def test_source_pixels_are_not_mutated_even_by_a_mutating_detector():
    rgb=np.full((256,256,3),88,np.uint8)
    def model(image):image[:]=0;return ()
    detect_tiles(rgb,model,sizes=(256,))
    assert np.all(rgb==88)


def test_spatial_duplicate_index_matches_existing_global_polygon_filter():
    detections=tuple(detection(x=20+(i%8)*100,y=20+(i//8)*60,score=.9-(i%3)*.1) for i in range(40))
    detections+=tuple(detection(x=21+(i%8)*100,y=21+(i//8)*60,score=.7) for i in range(40))
    expected=filter_module_detections(detections,1024,512,duplicate_iou=.5,
        minimum_area_fraction=16/(1024*512),maximum_area_fraction=1.)
    actual,rejected=spatial_duplicates(detections,1024,512)
    assert actual==expected and len(actual)+rejected==len(detections)


def test_budget_is_checked_before_any_model_runs_or_large_plan_is_allocated():
    with pytest.raises(ValueError,match='budget'):tile_plan(1_000_000,1,sizes=(256,))
    with pytest.raises(ValueError,match='budget'):
        detect_tiles(np.zeros((512,512,3),np.uint8),lambda _:pytest.fail('Started partial analysis'),maximum_tiles=1)


def test_cancel_returns_no_partial_detections_and_reports_only_progress_counts():
    ticks=[]
    with pytest.raises(KeyboardInterrupt):
        detect_tiles(np.zeros((512,512,3),np.uint8),lambda _:(detection(),),
            sizes=(512,256),should_cancel=lambda:bool(ticks),progress=lambda done,total:ticks.append((done,total)))
    assert ticks==[(1,10)]


@pytest.mark.parametrize('bad',[(0,512),(512,-1),(True,512)])
def test_bad_image_format_rejected(bad):
    with pytest.raises(ValueError):tile_plan(*bad)


def test_reader_supports_large_formats_without_allocating_the_whole_source():
    windows=[]
    def reader(window):
        windows.append(window);_,_,width,height=window
        return np.zeros((height,width,3),np.uint8),np.ones((height,width),bool)
    result,report=detect_tile_reader(12000,6000,reader,lambda _:(),sizes=(1024,))
    assert result==() and len(windows)==report['processed_tiles']
    assert all(1<=w<=1024 and 1<=h<=1024 for _,_,w,h in windows)


def test_reader_and_array_paths_produce_identical_native_results():
    rgb=np.zeros((350,600,3),np.uint8)
    def read(window):
        left,top,w,h=window
        return rgb[top:top+h,left:left+w],np.ones((h,w),bool)
    model=lambda _:(detection(),)
    direct,first=detect_tiles(rgb,model,sizes=(512,256))
    streamed,second=detect_tile_reader(600,350,read,model,sizes=(512,256))
    assert direct==streamed and first==second


def test_bad_window_reader_stops_before_model_without_partial_result():
    with pytest.raises(ValueError,match='dimensions'):
        detect_tile_reader(512,512,lambda window:(np.zeros((1,1,3),np.uint8),np.ones((1,1),bool)),
            lambda _:pytest.fail('Model saw wrong source window'),sizes=(512,))


def test_nested_tile_suppression_is_explicit_and_keeps_original_confidence():
    whole=detection(40,40,180,80,.95);fragment=detection(45,45,60,60,.9)
    default,_=spatial_duplicates((whole,fragment),512,512)
    nested,_=spatial_duplicates((whole,fragment),512,512,metric='ios')
    assert default==(whole,fragment) and nested==(whole,) and nested[0].confidence==.95


def test_neighboring_modules_are_not_combined_by_nested_tile_suppression():
    left=detection(40,40,80,40,.9);right=detection(122,40,80,40,.8)
    assert spatial_duplicates((left,right),512,512,metric='ios')[0]==(left,right)


def test_fourfold_rgb_reduction_uses_the_same_native_center_mapping():
    rgb=np.full((1024,1024,3),255,np.uint8)
    assert np.all(_input(rgb,ModuleTile(0,0,1024))==255)
    assert native_detection(detection(0,0),ModuleTile(128,256,1024)).polygon_px[0]==(129.5,257.5)


def test_native_offsets_retain_existing_geotiff_affine_even_with_rotation():
    from affine import Affine
    original=Affine(0.08,0.01,1000,-0.02,-0.08,2000)
    tile=ModuleTile(128,256,1024)
    local=detection(10,20)
    native=native_detection(local,tile)
    window=original*Affine.translation(tile.left,tile.top)*Affine.scale(4,4)
    for (x,y),(nx,ny) in zip(local.polygon_px,native.polygon_px):
        assert original*(nx+.5,ny+.5)==pytest.approx(window*(x+.5,y+.5))
