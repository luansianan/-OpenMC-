#!/usr/bin/env python3
"""Hypothesis sweep: how far can the geometry / enrichment go towards the paper's k?

Each variant rebuilds the assembly with different pin / pitch / enrichment
assumptions, runs a short (low-statistics) eigenvalue calculation and records the
fuel volume fraction, so the trend with the fissile inventory is visible.

Usage:
    python3 scripts/sweep.py [--particles 2000] [--batches 24] [--threads 12]
"""
import argparse
import importlib.util
import json
import os

import numpy as np
import openmc

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER_K = 1.31181

# tag, enrichment [%], pellet OD, rod OD, pitch, n_rings, central-hole OD  (cm)
CASES = [
    ("sw_solid91", 14.83, 0.2210, 0.3350, 0.57432, 5, 0.0),
    ("sw_annular91", 14.83, 0.2210, 0.3350, 0.57432, 5, 0.1651),
    ("sw_tight91", 14.83, 0.4000, 0.5140, 0.56538, 5, 0.0),
    ("sw_pins127", 14.83, 0.2210, 0.2780, 0.47660, 6, 0.0),
    ("sw_enr30", 30.0, 0.2210, 0.3350, 0.57432, 5, 0.0),
    ("sw_enr45", 45.0, 0.2210, 0.3350, 0.57432, 5, 0.0),
]


def load_model():
    spec = importlib.util.spec_from_file_location(
        "lfr_model", os.path.join(REPO, "model.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_variant(m, args, tag, enr, pellet_od, rod_od, pitch, n_rings, hole_od):
    m.R_PELLET = pellet_od / 2
    m.R_HOLE = hole_od / 2
    m.R_CLAD_OUT = rod_od / 2
    m.R_CLAD_IN = rod_od / 2 - m.T_CLAD
    m.PITCH = pitch
    m.N_RINGS = n_rings

    d = os.path.join(REPO, "runs", tag)
    os.makedirs(d, exist_ok=True)
    os.chdir(d)

    mats = m.build_materials(enr / 100.0)
    openmc.Materials(list(mats.values())).export_to_xml()
    root, regions = m.build_geometry(mats, solid_pellet=(hole_od <= 0.0))
    openmc.Geometry(root).export_to_xml()

    s = openmc.Settings()
    s.run_mode = "eigenvalue"
    s.particles = args.particles
    s.batches = args.batches
    s.inactive = args.inactive
    s.temperature = {"method": "interpolation", "default": 293.6}
    src = openmc.IndependentSource()
    src.space = openmc.stats.Box((-0.2, -0.2, -0.001), (0.2, 0.2, 0.001))
    src.energy = openmc.stats.Discrete([2.0e6], [1.0])
    s.source = src
    s.export_to_xml()
    m.build_tallies(regions, n_energy=20).export_to_xml()

    openmc.run(threads=args.threads, output=False)
    sp = openmc.StatePoint(os.path.join(d, f"statepoint.{args.batches}.h5"))
    k = sp.keff
    sp.close()

    n_pins = 1 + 3 * n_rings * (n_rings + 1)
    duct_in = 5.4102                                     # cm, inner across-flats
    fuel_area = n_pins * np.pi * ((pellet_od / 2) ** 2 - (hole_od / 2) ** 2)
    cell_area = np.sqrt(3) / 2 * duct_in ** 2
    return dict(tag=tag, enrichment=enr, pellet_od_mm=pellet_od * 10,
                rod_od_mm=rod_od * 10, pitch_mm=pitch * 10, n_pins=n_pins,
                hole_od_mm=hole_od * 10, fuel_vf=float(fuel_area / cell_area),
                k=float(k.nominal_value), k_std=float(k.std_dev),
                dev_pcm=float((k.nominal_value - PAPER_K) * 1e5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--particles", type=int, default=2000)
    ap.add_argument("--batches", type=int, default=24)
    ap.add_argument("--inactive", type=int, default=8)
    ap.add_argument("--threads", type=int, default=12)
    args = ap.parse_args()

    m = load_model()
    out = []
    for case in CASES:
        try:
            res = run_variant(m, args, *case)
            out.append(res)
            print(f"{res['tag']:<14} enr={res['enrichment']:5.2f}% "
                  f"pins={res['n_pins']:3d} fuel_vf={res['fuel_vf']*100:5.2f}%  "
                  f"k={res['k']:.4f} +/- {res['k_std']:.4f} "
                  f"({res['dev_pcm']:+.0f} pcm)", flush=True)
        except Exception as exc:                          # noqa: BLE001
            print(f"{case[0]}: FAILED {type(exc).__name__}: {exc}", flush=True)

    path = os.path.join(REPO, "results", "tables", "sweep_results.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print("written", path)


if __name__ == "__main__":
    main()
