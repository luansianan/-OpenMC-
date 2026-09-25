#!/usr/bin/env python3
"""Process the ENDF/B-VIII.0 files into an OpenMC HDF5 cross-section library.

ENDF-6 -> (NJOY 2016) -> ACE -> (openmc.data) -> HDF5 + cross_sections.xml

Notes learned the hard way (see docs/pitfalls.md):
  * NJOY's default RECONR tolerance (0.1 %) on the uranium isotopes needs far more
    resources than a small WSL1 instance can provide - the distro crashed twice
    (0xd00002fe) while processing U-235/U-238.  Those two nuclides are therefore
    processed with a 2 % tolerance, which was independently validated with the
    Godiva benchmark (k = 1.00071 +/- 0.00073, +71 pcm, `scripts/validate_godiva.py`).
  * U-238's PURR unresolved-resonance self-shielding step alone takes ~25 min, so
    the heavy nuclides are processed sequentially while the light ones run in parallel.

Usage:
    ENDF_DIR=/root/endf/raw XS_DIR=/root/xs python3 environment/build_xs.py [--workers 5]
"""
import argparse
import glob
import json
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor

import openmc.data

ENDF_DIR = os.environ.get("ENDF_DIR", "/root/endf/raw")
XS_DIR = os.environ.get("XS_DIR", "/root/xs")
TEMP = 293.6

# nuclides that must be processed with a looser reconstruction tolerance
LOOSE = {"U235": 0.02, "U238": 0.02}
DEFAULT_ERR = 0.001


def process(args):
    path, out_dir, temp = args
    base = os.path.basename(path)
    work = os.path.join("/tmp/njoy_work", base.replace(".", "_"))
    os.makedirs(work, exist_ok=True)
    os.chdir(work)

    # resolve the nuclide name first so we can pick its tolerance
    data = None
    try:
        stem = base.split("_")[-1].replace(".dat", "").replace(".endf", "")
        err = LOOSE.get(stem.replace("-", ""), DEFAULT_ERR)
        t0 = time.time()
        data = openmc.data.IncidentNeutron.from_njoy(
            path, temperatures=[temp], njoy_exec=shutil.which("njoy"), error=err)
        h5 = os.path.join(out_dir, data.name + ".h5")
        if os.path.exists(h5):
            os.remove(h5)
        data.export_to_hdf5(h5, "w")
        return (base, data.name, err, time.time() - t0,
                os.path.getsize(h5), "ok")
    except Exception as exc:                       # noqa: BLE001
        return (base, getattr(data, "name", ""), None, 0.0, 0, f"ERR {exc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=TEMP)
    args = ap.parse_args()

    os.makedirs(XS_DIR, exist_ok=True)
    files = sorted(sum((glob.glob(os.path.join(ENDF_DIR, ext))
                        for ext in ("*.dat", "*.endf", "*.endf6")), []))
    if not files:
        raise SystemExit(f"no ENDF files in {ENDF_DIR}")

    # heavy actinides first and alone (memory), then the rest in parallel
    heavy = [f for f in files if any(k in f for k in ("U-235", "U-238", "U_235", "U_238"))]
    light = [f for f in files if f not in heavy]

    print(f"processing {len(files)} ENDF files ({len(heavy)} heavy, sequential)")
    results, failed = [], []
    for path in heavy:
        r = process((path, XS_DIR, args.temperature))
        print(f"  {r[0]:<28} -> {r[1]:<8} err={r[2]} {r[3]:7.1f}s "
              f"{r[4]/1024:7.0f} kB {r[5]}", flush=True)
        (results if r[5] == "ok" else failed).append(r)

    if light:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            for r in ex.map(process, [(f, XS_DIR, args.temperature) for f in light]):
                print(f"  {r[0]:<28} -> {r[1]:<8} err={r[2]} {r[3]:7.1f}s "
                      f"{r[4]/1024:7.0f} kB {r[5]}", flush=True)
                (results if r[5] == "ok" else failed).append(r)

    lib = openmc.data.DataLibrary()
    for h5 in sorted(glob.glob(os.path.join(XS_DIR, "*.h5"))):
        lib.register_file(h5)
    xml = os.path.join(XS_DIR, "cross_sections.xml")
    lib.export_to_xml(xml)
    print(f"\nlibrary: {len(lib.libraries)} nuclides -> {xml}")

    with open(os.path.join(XS_DIR, "library_manifest.json"), "w") as fh:
        json.dump([{"source": r[0], "nuclide": r[1], "reconr_error": r[2],
                    "seconds": round(r[3], 1), "bytes": r[4], "status": r[5]}
                   for r in results + failed], fh, indent=2)
    if failed:
        print("FAILED:", failed)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
