#!/usr/bin/env python3
"""Post-process an OpenMC statepoint: k_eff, flux map, radial profiles, spectrum."""
import argparse
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openmc

PAPER_KEFF = {"14.83": (1.31181, 0.00023), "15.02": (1.31181, 0.00023)}


def load_statepoint(run_dir):
    sp_files = sorted(glob.glob(os.path.join(run_dir, "statepoint.*.h5")),
                      key=lambda p: int(p.split(".")[-2]))
    if not sp_files:
        raise SystemExit(f"no statepoint in {run_dir}")
    return openmc.StatePoint(sp_files[-1])


def mesh_arrays(tally, nx, ny):
    """return (mean, std) arrays shaped (ny, nx)"""
    m = np.asarray(tally.mean, dtype=float).reshape(nx, ny, -1)[:, :, 0].T
    s = np.asarray(tally.std_dev, dtype=float).reshape(nx, ny, -1)[:, :, 0].T
    return m, s


def energy_edges(filt):
    """energy bin edges from an EnergyFilter (handles (n,2) style bins)"""
    raw = np.asarray(filt.bins, dtype=float)
    if raw.ndim == 2 and raw.shape[1] == 2:
        return raw[:, 0], raw[:, 1]
    return raw[:-1], raw[1:]


def radial_profile(flux, err, xs, ys, nbins=56):
    """volume-averaged flux in concentric annuli (equal-area mesh cells -> plain mean)"""
    X, Y = np.meshgrid(xs, ys)
    R = np.sqrt(X ** 2 + Y ** 2)
    rmax = np.sqrt(xs.max() ** 2 + ys.max() ** 2)
    edges = np.linspace(0.0, rmax, nbins + 1)
    rc, fm, fe = [], [], []
    for i in range(nbins):
        sel = (R >= edges[i]) & (R < edges[i + 1])
        if sel.sum() > 3:
            rc.append(0.5 * (edges[i] + edges[i + 1]))
            fm.append(flux[sel].mean())
            fe.append(np.sqrt((err[sel] ** 2).mean()))
    return np.array(rc), np.array(fm), np.array(fe)


def mesh_axes(tally):
    """bin-centre coordinates of a mesh-filtered tally"""
    m = tally.find_filter(openmc.MeshFilter).mesh
    nx, ny, _ = m.dimension
    ll, ur = m.lower_left, m.upper_right

    def centres(a, b, n):
        edges = np.linspace(a, b, n + 1)
        return 0.5 * (edges[:-1] + edges[1:])

    return nx, ny, centres(ll[0], ur[0], nx), centres(ll[1], ur[1], ny)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?", default="run")
    ap.add_argument("--enrichment", default="15.02")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    sp = load_statepoint(args.run_dir)
    k = sp.keff
    summary = {
        "statepoint": os.path.basename(sp._f.filename),
        "k_eff": k.nominal_value,
        "k_eff_std": k.std_dev,
        "enrichment_pct": float(args.enrichment),
        "n_particles": int(getattr(sp, "n_particles", 0) or 0),
        "n_batches": int(getattr(sp, "n_batches", 0) or 0),
    }
    ref, ref_std = PAPER_KEFF.get(args.enrichment, PAPER_KEFF["14.83"])
    summary["paper_k_eff"] = ref
    summary["paper_k_eff_std"] = ref_std
    summary["delta_k_pcm"] = (k.nominal_value - ref) * 1e5
    summary["delta_k_pct"] = (k.nominal_value - ref) / ref * 100.0
    print(f"k_eff = {k.nominal_value:.5f} +/- {k.std_dev:.5f}")
    print(f"paper k_eff = {ref:.5f} +/- {ref_std:.5f}  ->  "
          f"delta = {summary['delta_k_pcm']:+.0f} pcm ({summary['delta_k_pct']:+.3f} %)")

    t_all = sp.get_tally(name="mesh flux")
    nx, ny, xs, ys = mesh_axes(t_all)
    ll = (xs[0] - (xs[1] - xs[0]) / 2, ys[0] - (ys[1] - ys[0]) / 2)
    ur = (xs[-1] + (xs[1] - xs[0]) / 2, ys[-1] + (ys[1] - ys[0]) / 2)

    tag = args.tag or args.enrichment.replace(".", "p")
    out = os.path.join(args.run_dir)

    # ---- 1. 2-D flux map ----
    t = t_all.get_slice(scores=["flux"])
    flux, ferr = mesh_arrays(t, nx, ny)
    rel = np.divide(ferr, flux, out=np.zeros_like(ferr), where=flux > 0)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0))
    im0 = axes[0].imshow(flux, origin="lower", extent=(ll[0], ur[0], ll[1], ur[1]),
                         cmap="inferno")
    axes[0].set_title("neutron flux  (2-D assembly cross section)")
    axes[0].set_xlabel("x [cm]"); axes[0].set_ylabel("y [cm]")
    fig.colorbar(im0, ax=axes[0], label="flux [n/cm$^2$ per source n]")
    im1 = axes[1].imshow(np.clip(rel, 0, 0.02), origin="lower",
                         extent=(ll[0], ur[0], ll[1], ur[1]), cmap="viridis")
    axes[1].set_title("relative statistical error of the flux")
    axes[1].set_xlabel("x [cm]"); axes[1].set_ylabel("y [cm]")
    fig.colorbar(im1, ax=axes[1], label=r"$\sigma_\phi/\phi$")
    fig.suptitle(f"OpenMC LBE fuel-assembly benchmark - k$_{{eff}}$ = "
                 f"{k.nominal_value:.5f} $\\pm$ {k.std_dev:.5f}", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"flux_map_{tag}.png"), dpi=150)
    plt.close(fig)

    # ---- 2. radial profiles ----
    rc, fm, fe = radial_profile(flux, ferr, xs, ys)
    tf = sp.get_tally(name="mesh flux fuel").get_slice(scores=["flux"])
    nxf, nyf, xsf, ysf = mesh_axes(tf)
    ffuel, efuel = mesh_arrays(tf, nxf, nyf)
    rcf, fmf, fef = radial_profile(ffuel, efuel, xsf, ysf)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    axes[0].plot(rc, fm, "o-", ms=3, label="annulus-averaged (all materials)")
    axes[0].plot(rcf, fmf, "s-", ms=3, label="fuel region only")
    axes[0].set_xlabel("radius r [cm]"); axes[0].set_ylabel("flux [arb. units]")
    axes[0].set_title("radial neutron flux distribution")
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[0].axvline(2.7051, ls="--", c="grey", lw=1)  # duct inner across-flats/2
    axes[1].errorbar(rc, fm, yerr=fe, fmt="o", ms=3, label="all materials")
    axes[1].errorbar(rcf, fmf, yerr=fef, fmt="s", ms=3, label="fuel")
    axes[1].set_xlabel("radius r [cm]"); axes[1].set_ylabel("flux [arb. units]")
    axes[1].set_title("radial profile with 1$\\sigma$ statistical error bars")
    axes[1].legend(); axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"flux_radial_{tag}.png"), dpi=150)
    plt.close(fig)

    # ---- 3. energy spectrum per region ----
    labels = {"fuel": "UO2 fuel", "gap": "helium gap", "clad": "HT9 cladding",
              "coolant": "LBE coolant", "coolant_outer": "LBE coolant (outer)",
              "duct": "HT9 duct"}
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    spec = []
    ec_all = None
    for key, lab in labels.items():
        t = sp.get_tally(name=f"spectrum_{key}")
        lo, hi = energy_edges(t.find_filter(openmc.EnergyFilter))
        ec = np.sqrt(lo * hi)
        de = hi - lo
        v = np.asarray(t.mean, dtype=float).reshape(-1)[:len(ec)]
        y = np.divide(ec * v, de)                 # flux per unit lethargy
        ax.plot(ec, y, "-o", ms=2.5, label=lab)
        spec.append(dict(region=lab, e_center_eV=ec.tolist(),
                         flux_per_lethargy=y.tolist()))
        ec_all = ec
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("energy [eV]"); ax.set_ylabel("flux per unit lethargy [arb. units]")
    ax.set_title("neutron spectrum by region")
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"spectrum_{tag}.png"), dpi=150)
    plt.close(fig)

    # ---- 4. region-averaged quantities ----
    tt = sp.get_tally(name="region total flux")
    tt_vals = np.asarray(tt.mean, dtype=float).reshape(-1)
    summary["region_flux"] = {labels[k]: float(tt_vals[i])
                              for i, k in enumerate(labels)}
    summary["radial_profile"] = dict(r_cm=rc.tolist(), flux=fm.tolist(), std=fe.tolist(),
                                     r_fuel_cm=rcf.tolist(), flux_fuel=fmf.tolist())
    with open(os.path.join(out, f"summary_{tag}.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print("wrote plots + summary to", out)
    sp.close()


if __name__ == "__main__":
    main()
