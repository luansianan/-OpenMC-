#!/usr/bin/env python3
"""Generate the summary figures used in the README (no OpenMC required).

Reads the JSON tables in results/tables and writes PNGs into results/figures.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = os.path.join(ROOT, "results", "tables")
FIG = os.path.join(ROOT, "results", "figures")
os.makedirs(FIG, exist_ok=True)

# paper Table 3 ("Before Equivalence", 2-D OpenMC), Energies 18 (2025) 3564
PAPER = {4.94: 0.78269, 7.91: 0.98595, 9.89: 1.09578,
         12.36: 1.21061, 14.83: 1.31181, 17.81: 1.40993}
PAPER_K = PAPER[14.83]


def load(name, default=None):
    path = os.path.join(TAB, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def k_vs_enrichment():
    ana = load("analysis.json", {})
    solid = load("summary_prod_solid.json", {})
    annular = load("summary_prod_annular.json", {})
    bound = ana.get("bound", [1.07243, 0.00087])
    sweep = {r["enrichment"]: r for r in ana.get("sweep", [])}

    # this work, solid pellet, as-specified geometry
    enr, k, ek = [], [], []
    for e, s in ((14.83, solid),):
        if s:
            enr.append(e); k.append(s["k_eff"]); ek.append(s["k_eff_std"])
    for e in (22.0, 24.0, 26.0):
        s = load(f"summary_enr_{str(e).replace('.', 'p')}.json")
        if s:
            enr.append(e); k.append(s["k_eff"]); ek.append(s["k_eff_std"])
    for e in (30.0, 45.0):
        r = sweep.get(e)
        if r:
            enr.append(e); k.append(r["k"]); ek.append(r["k_std"])
    order = np.argsort(enr)
    enr = np.array(enr)[order]; k = np.array(k)[order]; ek = np.array(ek)[order]

    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    p_e = np.array(sorted(PAPER)); p_k = np.array([PAPER[e] for e in p_e])
    ax.plot(p_e, p_k, "s-", color="#1f77b4", ms=6, lw=1.8,
            label="paper (Energies 18, 3564, Table 3)")
    if len(enr):
        ax.errorbar(enr, k, yerr=ek, fmt="o-", color="#d62728", ms=6, lw=1.8,
                    capsize=3, label="this work (solid pellet, as-specified geometry)")
    if annular:
        ax.errorbar([14.83], [annular["k_eff"]], yerr=[annular["k_eff_std"]],
                    fmt="D", color="#2ca02c", ms=8, capsize=3,
                    label="this work (annular pellet reading)")
    ax.errorbar([14.83], [bound[0]], yerr=[bound[1]], fmt="^", color="#9467bd",
                ms=9, capsize=3, label="upper bound (touching rods, 39.5 % fuel)")

    ax.axhline(PAPER_K, color="#1f77b4", ls=":", lw=1.2)
    ax.annotate(f"paper reference $k_{{eff}}$ = {PAPER_K:.5f}",
                xy=(25.5, PAPER_K + 0.012), color="#1f77b4", fontsize=9)
    if len(enr):
        i24 = int(np.argmin(np.abs(enr - 24.0)))
        ax.annotate(f"{enr[i24]:.0f} % $\\rightarrow$ {k[i24]:.5f}\n"
                    f"(only {abs(k[i24]-PAPER_K)*1e5:.0f} pcm below the paper)",
                    xy=(enr[i24], k[i24]), xytext=(28, 1.16), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="0.4"))
    ax.set_xlabel("$^{235}$U enrichment [%]")
    ax.set_ylabel("$k_{eff}$")
    ax.set_title("LBE fuel-assembly benchmark: this work vs. the literature reference")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8.5, loc="lower right")
    fig.tight_layout()
    out = os.path.join(FIG, "k_vs_enrichment.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)


def k_vs_fuel_fraction():
    ana = load("analysis.json", {})
    sweep = ana.get("sweep", [])
    if not sweep:
        return
    vf = np.array([r["fuel_vf"] * 100 for r in sweep])
    kk = np.array([r["k"] for r in sweep])
    lbl = [r["tag"] for r in sweep]
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    ax.scatter(vf, kk, c="#d62728", s=55, zorder=3)
    for x, y, t in zip(vf, kk, lbl):
        ax.annotate(t.replace("sw_", ""), (x, y), textcoords="offset points",
                    xytext=(6, 4), fontsize=8)
    ax.axhline(PAPER_K, color="#1f77b4", ls=":", lw=1.2)
    ax.annotate("paper reference", xy=(5, PAPER_K + 0.01), color="#1f77b4", fontsize=9)
    ax.set_xlabel("fuel volume fraction [%]")
    ax.set_ylabel("$k_{eff}$")
    ax.set_title("Geometry / enrichment hypothesis sweep")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIG, "k_vs_fuel_fraction.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    k_vs_enrichment()
    k_vs_fuel_fraction()
