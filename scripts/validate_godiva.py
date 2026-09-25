#!/usr/bin/env python3
"""Independent validation of the cross-section chain: bare HEU sphere (Godiva).

Godiva is a classic critical benchmark: bare highly enriched uranium metal sphere,
radius 8.741 cm, rho = 18.74 g/cm3, composition U234/U235/U238 = 1.02/93.71/5.27 wt%.
Experimental k_eff = 1.0000.  If the ENDF/B-VIII.0 + NJOY chain is sound, OpenMC
must reproduce k = 1.000 +/- 0.001.

Note: U-234 is not part of the small benchmark library, so its 1 wt% is taken over
by U-238 - it changes k by only a few tens of pcm.

Usage:
    python3 scripts/validate_godiva.py [--threads 12] [--outdir runs/godiva]
"""
import argparse
import json
import os
import sys

import openmc

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(REPO, "runs", "godiva"))
    ap.add_argument("--particles", type=int, default=10000)
    ap.add_argument("--batches", type=int, default=120)
    ap.add_argument("--inactive", type=int, default=20)
    ap.add_argument("--threads", type=int, default=12)
    args = ap.parse_args()

    d = args.outdir
    os.makedirs(d, exist_ok=True)
    os.chdir(d)

    heu = openmc.Material(name="HEU")
    heu.add_nuclide("U235", 94.73, percent_type="wo")
    heu.add_nuclide("U238", 5.27, percent_type="wo")
    heu.set_density("g/cm3", 18.74)
    openmc.Materials([heu]).export_to_xml()

    sph = openmc.Sphere(r=8.741, boundary_type="vacuum")
    openmc.Geometry(openmc.Universe(
        cells=[openmc.Cell(fill=heu, region=-sph)])).export_to_xml()

    s = openmc.Settings()
    s.run_mode = "eigenvalue"
    s.particles = args.particles
    s.batches = args.batches
    s.inactive = args.inactive
    s.temperature = {"method": "interpolation", "default": 293.6}
    src = openmc.IndependentSource()
    src.space = openmc.stats.Point((0.0, 0.0, 0.0))
    src.energy = openmc.stats.Discrete([1.0e6], [1.0])
    s.source = src
    s.export_to_xml()

    openmc.run(threads=args.threads, output=False)

    sp = openmc.StatePoint(os.path.join(d, f"statepoint.{args.batches}.h5"))
    k = sp.keff
    sp.close()

    result = dict(case="godiva", k_eff=float(k.nominal_value),
                  k_eff_std=float(k.std_dev), reference_k_eff=1.0,
                  deviation_pcm=float((k.nominal_value - 1.0) * 1e5),
                  particles=args.particles, batches=args.batches,
                  inactive=args.inactive, threads=args.threads)
    with open("summary_godiva.json", "w") as fh:
        json.dump(result, fh, indent=2)

    print(f"\nGODIVA: k_eff = {k.nominal_value:.5f} +/- {k.std_dev:.5f}  "
          f"(experimental 1.0000, deviation {(k.nominal_value-1.0)*1e5:+.0f} pcm)")
    print("wrote", os.path.join(d, "summary_godiva.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
