#!/usr/bin/env python3
"""
OpenMC model of the lead-bismuth-eutectic (LBE) cooled fast reactor fuel-assembly
benchmark of:

    J. Xiao, Y. Zhang, S. Li, L. Chen, J. Li, C. Zhang,
    "Research on Equivalent One-Dimensional Cylindrical Modeling Method for
     Lead-Bismuth Fast Reactor Fuel Assemblies",
    Energies 18 (2025) 3564,  doi:10.3390/en18133564

The reference values reproduced here are the "Before Equivalence" (i.e. the true
2-D heterogeneous assembly) OpenMC k_eff calculations of that paper, e.g.
     14.83 % enrichment, all-fuel-rod assembly : k_eff = 1.31181 +/- 0.00023
(Table 3 / Table 4 of the paper).

Geometry (paper Table 2):                  Material (paper Table 1):
  fuel pellet inner/outer dia 1.651/2.210 mm   UO2  5 % U235 / 28.3 % U238 / 66.7 % O (at%), 10.94 g/cm3
  helium gap thickness        0.254 mm         HT-9 70 % Fe / 11.5 % Cr / 1 % Mo (at%),        7.8 g/cm3
  shell (cladding) thickness  0.316 mm         LBE  44.3 % Pb / 55.7 % Bi (at%),             10.29 g/cm3
  lattice diameter ratio      1.7144  (P/D)
  component box thickness     1.016 mm
  component box side length   56.134 mm  (across flats, outer)

=> rod outer diameter = 2.210 + 2*(0.254+0.316) = 3.350 mm
=> triangular pitch    = 1.7144 * 3.350       = 5.7432 mm
=> 91 fuel pins in 5 concentric rings (1 + 3*5*6 = 91), which is the pin count
   visible in Figure 1(a) of the paper; the bundle (53.09 mm across flats) fits the
   duct inner across-flats (56.134 - 2*1.016 = 54.102 mm), as in the figure.
"""
import argparse
import json
import os

import numpy as np
import openmc

# ----------------------------------------------------------------------------
# benchmark constants (paper Tables 1 and 2)
# ----------------------------------------------------------------------------
D_PELLET_IN = 0.1651   # cm  annular UO2 pellet inner diameter (central hole)
D_PELLET_OUT = 0.2210  # cm  UO2 pellet outer diameter
T_GAP = 0.0254         # cm  helium gap thickness
T_CLAD = 0.0316        # cm  HT-9 cladding thickness
PD_RATIO = 1.7144      # pitch / rod outer diameter
DUCT_F2F = 5.6134      # cm  component box across-flats (outer)
T_DUCT = 0.1016        # cm  component box wall thickness
N_RINGS = 5            # -> 91 pins

RHO_UO2, RHO_HT9, RHO_LBE, RHO_HE = 10.94, 7.8, 10.29, 1.78e-4  # g/cm3

# natural isotopic abundances (atom fraction) - IUPAC
NAT = {
    "Pb": {204: 0.0140, 206: 0.2410, 207: 0.2210, 208: 0.5240},
    "Fe": {54: 0.05845, 56: 0.91754, 57: 0.02119, 58: 0.00282},
    "Cr": {50: 0.04345, 52: 0.83789, 53: 0.09501, 54: 0.02365},
    "Mo": {92: 0.14649, 94: 0.09187, 95: 0.15837, 96: 0.16673, 97: 0.09582,
           98: 0.24130, 100: 0.09942},
}

PITCH = PD_RATIO * (D_PELLET_OUT + 2 * (T_GAP + T_CLAD))   # 0.57432 cm
R_HOLE, R_PELLET, R_CLAD_IN, R_CLAD_OUT = (
    D_PELLET_IN / 2, D_PELLET_OUT / 2,
    D_PELLET_OUT / 2 + T_GAP, D_PELLET_OUT / 2 + T_GAP + T_CLAD)
DUCT_F2F_IN = DUCT_F2F - 2 * T_DUCT

MATERIALS = {}


def _mat(name, density, composition):
    m = openmc.Material(name=name)
    for nuclide, frac in composition.items():
        m.add_nuclide(nuclide, frac, percent_type="ao")
    m.set_density("g/cm3", density)
    return m


def _expand(element, element_fraction):
    """natural element -> {nuclide: atom fraction}"""
    return {f"{element}{a}": element_fraction * f for a, f in NAT[element].items()}


def build_materials(enrichment):
    """enrichment : U235/(U235+U238) atom ratio of the uranium"""
    mats = {}
    uo2 = {
        "U235": enrichment / 3.0,
        "U238": (1.0 - enrichment) / 3.0,
        "O16": 2.0 / 3.0,
    }
    mats["uo2"] = _mat("UO2", RHO_UO2, uo2)

    ht9 = {}
    for el, frac in (("Fe", 0.70), ("Cr", 0.115), ("Mo", 0.010)):
        ht9.update(_expand(el, frac))
    mats["ht9"] = _mat("HT9", RHO_HT9, ht9)

    lbe = {}
    lbe.update(_expand("Pb", 0.443))
    lbe["Bi209"] = 0.557
    mats["lbe"] = _mat("LBE", RHO_LBE, lbe)

    mats["he"] = _mat("Helium", RHO_HE, {"He4": 1.0})
    return mats


def hexagon_planes(f2f, prefix, boundary_type="transmission"):
    """Six planes forming a hexagon (flat top/bottom) of across-flats dimension f2f.

    OpenMC half-space '-' of ``a*x + b*y + c*z - d = 0`` is the side where the
    expression is negative, so |n.x| < a for each of the three normal directions
    gives the hexagon interior.
    """
    a = f2f / 2.0
    normals = [(1.0, 0.0), (0.5, np.sqrt(3) / 2), (-0.5, np.sqrt(3) / 2)]
    region = None
    for i, (nx, ny) in enumerate(normals):
        for sign, sfx in ((1.0, "p"), (-1.0, "n")):
            s = openmc.Plane(a=sign * nx, b=sign * ny, c=0.0, d=a,
                             name=f"{prefix}_{sfx}{i}", boundary_type=boundary_type)
            region = -s if region is None else region & -s
    return region


def build_geometry(mats, solid_pellet=False):
    # ---- pin cell (UO2 fuel, helium gap, HT-9 cladding) ----
    s_pellet = openmc.ZCylinder(r=R_PELLET)
    s_clad_in = openmc.ZCylinder(r=R_CLAD_IN)
    s_clad_out = openmc.ZCylinder(r=R_CLAD_OUT)

    if solid_pellet:
        c_hole = None
        c_fuel = openmc.Cell(name="UO2 fuel", fill=mats["uo2"], region=-s_pellet)
    else:
        s_hole = openmc.ZCylinder(r=R_HOLE)
        c_hole = openmc.Cell(name="central hole", fill=mats["he"], region=-s_hole)
        c_fuel = openmc.Cell(name="UO2 fuel", fill=mats["uo2"],
                             region=+s_hole & -s_pellet)
    c_gap = openmc.Cell(name="helium gap", fill=mats["he"],
                        region=+s_pellet & -s_clad_in)
    c_clad = openmc.Cell(name="HT9 cladding", fill=mats["ht9"],
                         region=+s_clad_in & -s_clad_out)
    # the region outside the cladding inside a lattice element must also be filled,
    # otherwise particles leaving the cladding are lost
    c_cool_pin = openmc.Cell(name="LBE coolant", fill=mats["lbe"],
                             region=+s_clad_out)
    cells = [c_fuel, c_gap, c_clad, c_cool_pin]
    if c_hole is not None:
        cells.insert(0, c_hole)
    pin = openmc.Universe(name="fuel pin", cells=cells)

    c_cool = openmc.Cell(name="LBE coolant (lattice outer)", fill=mats["lbe"])
    coolant_univ = openmc.Universe(name="coolant", cells=[c_cool])

    # ---- 91-pin hexagonal lattice, 5 rings, flat side on top (orientation 'y') ----
    lat = openmc.HexLattice(name="fuel assembly")
    lat.center = (0.0, 0.0)
    lat.pitch = [PITCH]
    lat.orientation = "y"
    rings = []
    for n in range(N_RINGS, 0, -1):          # outer ring first
        rings.append([pin] * (6 * n))
    rings.append([pin])                      # centre pin
    lat.universes = rings
    lat.outer = coolant_univ

    # ---- hexagonal component box (HT-9) with reflective outer boundary ----
    inner_hex = hexagon_planes(DUCT_F2F_IN, "box_in")
    outer_hex = hexagon_planes(DUCT_F2F, "box_out", boundary_type="reflective")

    c_inside = openmc.Cell(name="assembly interior", fill=lat, region=inner_hex)
    c_duct = openmc.Cell(name="HT9 duct", fill=mats["ht9"],
                         region=outer_hex & ~inner_hex)
    root = openmc.Universe(name="root", cells=[c_inside, c_duct])
    return root, dict(fuel=c_fuel, gap=c_gap, clad=c_clad, coolant=c_cool_pin,
                      coolant_outer=c_cool, duct=c_duct)


def build_tallies(regions, n_energy=40):
    tallies = openmc.Tallies()

    # fine 2-D mesh for the flux map / radial profile (post-processed)
    mesh = openmc.RegularMesh(name="xy mesh")
    half = DUCT_F2F / 2 + 0.05
    mesh.lower_left = (-half, -half, -1e-3)
    mesh.upper_right = (half, half, 1e-3)
    mesh.dimension = (120, 120, 1)
    mesh_filter = openmc.MeshFilter(mesh)
    t_mesh = openmc.Tally(name="mesh flux")
    t_mesh.filters = [mesh_filter]
    t_mesh.scores = ["flux"]
    tallies.append(t_mesh)

    # coarser mesh restricted to the fuel region -> clean radial fuel-flux profile
    mesh_f = openmc.RegularMesh(name="xy mesh fuel")
    mesh_f.lower_left = (-half, -half, -1e-3)
    mesh_f.upper_right = (half, half, 1e-3)
    mesh_f.dimension = (60, 60, 1)
    t_mesh_fuel = openmc.Tally(name="mesh flux fuel")
    t_mesh_fuel.filters = [openmc.MeshFilter(mesh_f),
                           openmc.CellFilter([regions["fuel"]])]
    t_mesh_fuel.scores = ["flux"]
    tallies.append(t_mesh_fuel)

    # region-averaged spectrum: one tally per region (unambiguous bin ordering)
    e_bounds = np.logspace(np.log10(1e-5), np.log10(2.0e7), n_energy + 1)
    for key, cell in regions.items():
        t_spec = openmc.Tally(name=f"spectrum_{key}")
        t_spec.filters = [openmc.CellFilter([cell]), openmc.EnergyFilter(e_bounds)]
        t_spec.scores = ["flux"]
        tallies.append(t_spec)

    # total flux per region (for volume-averaged comparisons)
    t_tot = openmc.Tally(name="region total flux")
    t_tot.filters = [openmc.CellFilter(list(regions.values()))]
    t_tot.scores = ["flux"]
    tallies.append(t_tot)
    return tallies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enrichment", type=float, default=15.02,
                    help="U235/(U235+U238) atom %% (5/33.3=15.02 %% = paper Table 1)")
    ap.add_argument("--particles", type=int, default=20000)
    ap.add_argument("--batches", type=int, default=500)
    ap.add_argument("--inactive", type=int, default=100)
    ap.add_argument("--outdir", default="run")
    ap.add_argument("--pellet", choices=["annular", "solid"], default="annular",
                    help="fuel pellet type: annular (inner hole 1.651 mm) or solid")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--threads", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    os.chdir(args.outdir)

    mats = build_materials(args.enrichment / 100.0)
    openmc.Materials(list(mats.values())).export_to_xml()

    root, regions = build_geometry(mats, solid_pellet=(args.pellet == "solid"))
    geometry = openmc.Geometry(root)
    geometry.export_to_xml()

    settings = openmc.Settings()
    settings.run_mode = "eigenvalue"
    settings.particles = args.particles
    settings.batches = args.batches
    settings.inactive = args.inactive
    settings.temperature = {"method": "interpolation", "default": 293.6}
    settings.verbosity = 5
    if args.threads:
        settings.threads = args.threads
    src = openmc.IndependentSource()
    src.space = openmc.stats.Box((-0.2, -0.2, -0.001), (0.2, 0.2, 0.001))
    src.energy = openmc.stats.Discrete([2.0e6], [1.0])
    settings.source = src
    settings.export_to_xml()

    build_tallies(regions).export_to_xml()

    meta = dict(enrichment_pct=args.enrichment, pitch_cm=PITCH,
                pellet=args.pellet,
                rod_outer_diameter_cm=2 * R_CLAD_OUT, n_pins=91,
                duct_f2f_cm=DUCT_F2F, duct_f2f_inner_cm=DUCT_F2F_IN,
                particles=args.particles, batches=args.batches,
                inactive=args.inactive)
    with open("model_meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)
    print("model written to", os.path.abspath("."))
    print(json.dumps(meta, indent=2))

    if args.run:
        openmc.run(threads=args.threads or None)


if __name__ == "__main__":
    main()
