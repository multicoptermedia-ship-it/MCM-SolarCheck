"""Validate real DJI M3T RGB/Thermal pairing without modifying source imagery."""
from __future__ import annotations
import argparse, math, re
from pathlib import Path
from statistics import fmean
from mcm_solarcheck.importers.m3t_xmp import parse_m3t_xmp
_SEQ=re.compile(r'_(\d{4})_[VT]\.JPG$',re.I)
def seq(path):
    m=_SEQ.search(path.name)
    if not m: raise ValueError(f'Unsupported M3T filename: {path.name}')
    return int(m.group(1))
def distance_m(a,b):
    r=6371000.;p1=math.radians(a.position.latitude);p2=math.radians(b.position.latitude);dp=p2-p1;dl=math.radians(b.position.longitude-a.position.longitude)
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(h))
def validate(rgb_dir:Path,thermal_dir:Path)->int:
    rgb={seq(p):p for p in sorted(rgb_dir.glob('*_V.JPG'))};thermal={seq(p):p for p in sorted(thermal_dir.glob('*_T.JPG'))};common=sorted(rgb.keys()&thermal.keys())
    if not rgb or not thermal: print('FAIL: RGB or thermal files missing');return 2
    distances=[];times=[];heights=[];failures=[]
    for n in common:
        try:
            a=parse_m3t_xmp(rgb[n].read_bytes());b=parse_m3t_xmp(thermal[n].read_bytes())
            if a.position is None or b.position is None: raise ValueError('missing GPS position')
            distances.append(distance_m(a,b))
            if a.timestamp_utc and b.timestamp_utc: times.append(abs((a.timestamp_utc-b.timestamp_utc).total_seconds()))
            if a.position.altitude_m is not None and b.position.altitude_m is not None: heights.append(abs(a.position.altitude_m-b.position.altitude_m))
        except Exception as exc: failures.append((n,str(exc)))
    print(f'rgb={len(rgb)} thermal={len(thermal)} paired={len(common)} rgb_unpaired={len(rgb.keys()-thermal.keys())} thermal_unpaired={len(thermal.keys()-rgb.keys())} failed={len(failures)}')
    if distances: print(f'distance_mean_m={fmean(distances):.6f} distance_max_m={max(distances):.6f}')
    if times: print(f'time_delta_mean_s={fmean(times):.6f} time_delta_max_s={max(times):.6f}')
    if heights: print(f'altitude_delta_mean_m={fmean(heights):.6f} altitude_delta_max_m={max(heights):.6f}')
    for n,msg in failures: print(f'FAIL {n:04d}: {msg}')
    return 1 if failures else 0
def main():
    ap=argparse.ArgumentParser();ap.add_argument('rgb_dir',type=Path);ap.add_argument('thermal_dir',type=Path);a=ap.parse_args();return validate(a.rgb_dir,a.thermal_dir)
if __name__=='__main__': raise SystemExit(main())
