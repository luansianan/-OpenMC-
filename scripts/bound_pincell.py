#!/usr/bin/env python3
"""Upper bound on k for the paper's pin design.

Take the paper's pin (2.210 mm pellet, 0.254 mm He gap, 0.316 mm HT-9 clad =>
3.350 mm rod) and pack the rods as tightly as geometrically possible (pitch = rod
diameter, i.e. touching rods, reflective boundaries).  No hexagonal pin bundle can
have a higher fuel volume fraction than this, so the resulting k is an upper bound
for ANY assembly built from these pins at the same enrichment.

Usage:
    python3 scripts/bound_pincell.py [--enrichment 14.83] [--threads 12]
"""
import argparse
import importlib.util
import json
import math
import os

import openmc

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_model():
    """import model.py from the repository root"""
    spec = importlib.util.spec_from_file_location(
        "lfr_model", os.path.join(REPO, "model.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enrichment", type=float, default=14.83)
    ap.add_argument("--particles", type=int, default=5000)
    ap.add_argument("--batches", type=int, default=120)
    ap.add_argument("--inactive", type=int, default=20)
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--outdir", default=os.path.join(REPO, "runs", "bound_pincell"))
    args = ap.parse_args()

    m = load_model()
    d = args.outdir
    os.makedirs(d, exist_ok=True)
    os.chdir(d)

    mats = m.build_materials(args.enrichment / 100.0)
    openmc.Materials(list(mats.values())).export_to_xml()

    rod = 2 * m.R_CLAD_OUT                   # 0.335 cm
    pitch = rod                              # touching rods -> maximum packing
    f2f = pitch * (3 ** 0.5)                 # across flats of the unit cell hexagon
    region = m.hexagon_planes(f2f, "cell", boundary_type="reflective")

    s_pel = openmc.ZCylinder(r=m.R_PELLET)
    s_clad_in = openmc.ZCylinder(r=m.R_CLAD_IN)
    s_clad_out = openmc.ZCylinder(r=m.R_CLAD_OUT)
    pin_cells = [
        openmc.Cell(name="fuel", fill=mats["uo2"], region=-s_pel),
        openmc.Cell(name="gap", fill=mats["he"], region=+s_pel & -s_clad_in),
        openmc.Cell(name="clad", fill=mats["ht9"], region=+s_clad_in & -s_clad_out),
        openmc.Cell(name="coolant", fill=mats["lbe"], region=+s_clad_out),
    ]
    root = openmc.Universe(cells=[openmc.Cell(
        fill=openmc.Universe(cells=pin_cells), region=region)])
    openmc.Geometry(root).export_to_xml()

    s = openmc.Settings()
    s.run_mode = "eigenvalue"
    s.particles = args.particles
    s.batches = args.batches
    s.inactive = args.inactive
    s.temperature = {"method": "interpolation", "default": 293.6}
    src = openmc.IndependentSource()
    src.space = openmc.stats.Point((0.0, 0.0, 0.0))
    src.energy = openmc.stats.Discrete([2.0e6], [1.0])
    s.source = src
    s.export_to_xml()

    fuel_area = math.pi * m.R_PELLET ** 2
    cell_area = math.sqrt(3) / 2 * pitch ** 2
    vf = fuel_area / cell_area
    print(f"rod {rod*10:.3f} mm, pitch {pitch*10:.3f} mm (touching), "
          f"fuel volume fraction = {vf*100:.2f} %")

    openmc.run(threads=args.threads, output=False)
    sp = openmc.StatePoint(os.path.join(d, f"statepoint.{args.batches}.h5"))
    k = sp.keff
    sp.close()

    result = dict(case="bound_pincell", enrichment_pct=args.enrichment,
                  fuel_volume_fraction=vf, k_eff=float(k.nominal_value),
                  k_eff_std=float(k.std_dev), paper_k_eff=1.31181,
                  deviation_pcm=float((k.nominal_value - 1.31181) * 1e5),
                  particles=args.particles, batches=args.batches,
                  inactive=args.inactive, threads=args.threads)
    with open("summary_bound_pincell.json", "w") as fh:
        json.dump(result, fh, indent=2)

    print(f"\nUPPER BOUND (touching rods, {args.enrichment}% enrichment): "
          f"k_inf = {k.nominal_value:.5f} +/- {k.std_dev:.5f}")
    print("paper value at this enrichment: 1.31181")
    print("wrote", os.path.join(d, "summary_bound_pincell.json"))


if __name__ == "__main__":
    main()
