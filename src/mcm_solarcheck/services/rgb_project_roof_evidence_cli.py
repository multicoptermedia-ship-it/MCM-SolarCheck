"""Project-bound independent roof survey screen for an ENU SfM candidate.

Read-only SQLite/images (no image decode), bounded local JSON/NPZ, writes only
a local review report. This NEVER elevates candidate geometry to verified
orthophoto or trusted surveyed-plane tile eligibility.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import zipfile
import numpy as np

from mcm_solarcheck.services.rgb_project_roof_evidence_gate import (
    screen_project_rgb_roof_geometry,
)
from mcm_solarcheck.services.rgb_project_roof_diagnostic_vertical import (
    render_unverified_project_roof_tiles,
)


def _local_file(path,limit):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size>limit:
        raise ValueError("bounded existing local evidence file required")
    return p


def main(argv=None):
    parser=argparse.ArgumentParser(description="Whole-project roof evidence screen; no verified orthophoto")
    parser.add_argument("--database",required=True)
    parser.add_argument("--project-id",required=True)
    parser.add_argument("--candidate-npz",required=True)
    parser.add_argument("--candidate-json",required=True)
    parser.add_argument("--gcp-survey-json",required=True)
    parser.add_argument("--roof-survey-json",required=True)
    parser.add_argument("--output-directory",required=True)
    parser.add_argument("--render-diagnostic-tiles",action="store_true",
                        help="Generate candidate-only PNG tiles/masks; NEVER verified ortho")
    args=parser.parse_args(argv)
    paths=[
        _local_file(args.candidate_npz,50_000_000),
        _local_file(args.candidate_json,1_000_000),
        _local_file(args.gcp_survey_json,2_000_000),
        _local_file(args.roof_survey_json,3_000_000),
    ]
    if len({p.resolve() for p in paths})!=4:
        raise ValueError("separate local project and survey evidence files required")
    out=Path(args.output_directory)
    if not out.is_dir() or out.is_symlink() or any(out.iterdir()):
        raise ValueError("existing empty output directory required")
    dest=out.resolve()
    db=Path(args.database).resolve(strict=True)
    if (dest==db.parent or dest in db.parents or
        any(dest==p.parent or dest in p.parents for p in (x.resolve() for x in paths))):
        raise ValueError("output cannot overlap input database or evidence source folders")
    manifest=json.loads(paths[1].read_text(encoding="utf-8"))
    if manifest.get("candidate_npz") != paths[0].name:
        raise ValueError("candidate NPZ and manifest must belong together")
    gcp=json.loads(paths[2].read_text(encoding="utf-8"))
    roof=json.loads(paths[3].read_text(encoding="utf-8"))
    with zipfile.ZipFile(paths[0]) as archive:
        members=archive.infolist()
        if (len(members)>10 or any(m.file_size>60_000_000 for m in members)
                or sum(m.file_size for m in members)>150_000_000):
            raise ValueError("untrusted oversized camera candidate NPZ")
    with np.load(paths[0],allow_pickle=False) as data:
        arrays={name:data[name] for name in data.files}
    if args.render_diagnostic_tiles:
        result=render_unverified_project_roof_tiles(
            args.database,args.project_id,manifest,arrays,gcp,roof,out,
        )
        print(json.dumps({"state":result.state,"frames":result.rgb_frame_count,
                          "orthophoto_verified":False},sort_keys=True))
        return 0
    audit=screen_project_rgb_roof_geometry(
        args.database,args.project_id,manifest,arrays,gcp,roof,
    )
    summary={
        "schema":"mcm.rgb_project_roof_evidence_screen.v1",
        "state":audit.state,
        "project_id":args.project_id,
        "imported_rgb_sources_checked":audit.source_count,
        "independent_roof_observations_checked":audit.rooftop_holdout_count,
        "p95_rooftop_error_m":audit.p95_rooftop_error_m,
        "max_rooftop_error_m":audit.largest_per_camera_error_m,
        "candidate_tile_count":audit.candidate_tile_count,
        "survey_authenticity_verified":False,
        "camera_calibration_independently_verified":False,
        "eligible_for_verified_roof_tiles":False,
        "metric_scale_verified":False,
        "georeferencing_verified":False,
        "orthophoto_verified":False,
        "pv_module_detection_performed":False,
        "thermal_registration_verified":False,
    }
    output=out/"rgb-project-roof-evidence-unverified.json"
    with output.open("x",encoding="utf-8") as f:
        json.dump(summary,f,sort_keys=True,indent=2)
        f.write("\n")
    print(json.dumps({"state":audit.state,"frames":audit.source_count,
                      "orthophoto_verified":False},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
