"""One private multi-ZIP DJI RGB-series index, no extraction or customer GPS print."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcm_solarcheck.services.rgb_flight_zip_series import read_private_rgb_zip_series


def main(argv=None):
    parser=argparse.ArgumentParser(
        description="Read all DJI RGB ZIPs (even misnamed .tip); report aggregate EXIF/XMP coverage only",
    )
    parser.add_argument("--rgb-archive",action="append",required=True,
                        help="ZIP file path; repeat once per archive")
    parser.add_argument("--report",type=Path,
                        help="new LOCAL JSON summary; contains no GPS/filenames")
    args=parser.parse_args(argv)
    series=read_private_rgb_zip_series(tuple(Path(x) for x in args.rgb_archive))
    report=series.privacy_safe_summary()
    if args.report is not None:
        dest=args.report
        if (not dest.is_absolute() or dest.is_symlink() or dest.exists()
                or not dest.parent.is_dir() or dest.parent.is_symlink()):
            raise ValueError("new report path in existing local folder required")
        parents={Path(x).resolve().parent for x in args.rgb_archive}
        if dest.parent.resolve() in parents:
            raise ValueError("report cannot be written beside original RGB ZIP")
        with dest.open("x",encoding="utf-8") as fp:
            json.dump(report,fp,sort_keys=True,indent=2)
            fp.write("\n")
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
