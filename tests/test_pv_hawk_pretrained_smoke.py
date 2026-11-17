"""Opt-in actual public RGB weights + synthetic GeoTIFFs; no customer images."""
import os
from pathlib import Path
import importlib.util
import sys

import pytest

PREFIX=os.environ.get('SOLARCHECK_PV_HAWK_PREFIX')
pytestmark=pytest.mark.skipif(not PREFIX,reason='Explicit isolated pretrained CPU pilot only')
# Python3.10 worker bootstrap must run before shared services import.
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hawk_worker',ROOT/'scripts/MCM_SolarCheck_PV_MODELLVERGLEICH.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
if PREFIX: worker.prepare_runtime()

from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source
from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_model_comparison as evaluation


@pytest.fixture
def pretrained_scene(scene):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.enums import ColorInterp
    from mcm_solarcheck.services import thermal_partial_comparison as comparison
    source,folder,rgb,thermal=scene
    with rasterio.open(thermal) as raster:tags=raster.tags()
    array=np.full((3,600,800),230,np.uint8)
    array[:,100:151,100:181]=np.array([40,70,120],np.uint8)[:,None,None]
    array[:,300:351,400:481]=np.array([40,70,120],np.uint8)[:,None,None]
    with rasterio.open(rgb,'w',driver='GTiff',width=800,height=600,count=3,dtype='uint8',crs='EPSG:25832',transform=from_origin(350000,5650000,.1,.1)) as target:
        target.write(array);target.colorinterp=(ColorInterp.red,ColorInterp.green,ColorInterp.blue)
    with rasterio.open(thermal,'w',driver='GTiff',width=400,height=300,count=3,dtype='uint8',crs='EPSG:25832',transform=from_origin(350000,5650000,.2,.2)) as target:
        target.write(np.full((3,300,400),100,np.uint8));target.update_tags(**tags)
        target.colorinterp=(ColorInterp.red,ColorInterp.green,ColorInterp.blue)
    value=comparison.open_partial_comparison(source,rgb)
    comparison.save_partial_comparison(value,opacity=50,zoom=1,verdict='looks_aligned',note='Synthetic CPU model test')
    return source,value


def test_pretrained_rgb_cpu_real_worker_saved_comparison_reopen_and_bad_hash(pretrained_scene):
    import subprocess
    source,value=pretrained_scene
    result=pv.detect_partial_pv_window(value,window=(20,20,760,560))
    region=pv.make_region(value,result)
    for e in region['entries']:e['status']='outline_ok'
    key=pv.region_key(result.rgb_window);pv.save_module_review(value,{key:region},key)
    originals={p:p.read_bytes() for p in (value.rgb_path,value.thermal_path,value.folder/pv.STATE,source/'job.json')}
    manifest=Path(PREFIX)/'pv-hawk-rgb.LOCAL.json'
    args=[sys.executable,str(ROOT/'scripts/MCM_SolarCheck_PV_MODELLVERGLEICH.py'),'--source',str(source),'--manifest',str(manifest),'--region',key]
    run=subprocess.run(args,capture_output=True,timeout=120)
    assert run.returncode==0
    record,found,references=evaluation.read_model_comparison(value)
    assert record['model']['provider']=='LukasBommes/PV-Hawk'
    assert record['model']['production_approved'] is False and record['accuracy_verified'] is False
    assert len(references)==2 and record['label']==value.label
    # A synthetic image is not a field accuracy benchmark; zero candidates valid.
    saved=(value.folder/evaluation.STATE).read_bytes()
    previous=manifest.read_bytes()
    try:
        manifest.write_text('{}')
        run=subprocess.run(args,capture_output=True,timeout=30)
        assert run.returncode==2 and (value.folder/evaluation.STATE).read_bytes()==saved
        assert evaluation.read_model_comparison(value)[0]==record  # no model load
    finally:manifest.write_bytes(previous)
    # Same single-process boundary as Qt: killing a real TF worker preserves
    # the previous accepted report and never starts a background child engine.
    import time
    cancelled=subprocess.Popen(args+['--run-token','a'*32],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        assert cancelled.poll() is None
        cancelled.kill();cancelled.wait(timeout=20)
    finally:
        if cancelled.poll() is None:cancelled.kill();cancelled.wait(timeout=20)
    assert (value.folder/evaluation.STATE).read_bytes()==saved
    assert not list(value.folder.glob('pv-model-comparison-*.LOCAL.json'))
    assert all(p.read_bytes()==before for p,before in originals.items())
