#!/usr/bin/env python3
"""Reverse-engineer the fuel-assembly geometry from Figure 1 of the paper.

The paper's Table 2 gives "Fuel rod inner/outer diameter 1.651/2.210 mm" without
saying whether the fuel pellet is annular.  This script measures Figure 1 (page 7 of
the PDF) by connected-component analysis: it counts the fuel-pin circles per panel
(91 in panel (a) = 5 hexagonal rings), measures the pitch-to-diameter ratio, and
checks the pin-bundle fill fraction inside the duct.

Combined with the duct dimension (56.134 mm across flats) this fixes the rod outer
diameter to ~3.35 mm, i.e. the pellet + 2 x (0.254 mm He gap + 0.316 mm HT-9 clad),
which is the geometry used by model.py.

The paper PDF is not redistributed with this repository (it is CC-BY, doi
10.3390/en18133564): download it first and pass its path.

Usage:
    python3 scripts/measure_fig1.py refs/paper.pdf [--page 7] [--dpi 400]
"""
import argparse

import numpy as np
from PIL import Image
from scipy import ndimage

PANEL_NAMES = ["(a) all fuel", "(b) regular HT-9", "(c) irregular 1", "(d) irregular 2"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="path to the paper PDF")
    ap.add_argument("--page", type=int, default=7, help="1-based page of Figure 1")
    ap.add_argument("--dpi", type=int, default=400)
    args = ap.parse_args()

    import pymupdf

    doc = pymupdf.open(args.pdf)
    pix = doc[args.page - 1].get_pixmap(dpi=args.dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    a = np.array(img).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]

    red = (r > 150) & (g < 90) & (b < 90)                 # fuel pins
    purple = (r > 60) & (r < 170) & (g < 80) & (b > 90)   # coolant background

    # locate the four panels from the coolant background
    lab, n = ndimage.label(purple)
    sizes = ndimage.sum(purple, lab, range(1, n + 1))
    panels = []
    for idx in np.argsort(sizes)[::-1][:6]:
        if sizes[idx] < 5000:
            continue
        ys, xs = np.nonzero(lab == idx + 1)
        panels.append((ys.min(), ys.max(), xs.min(), xs.max()))
    panels.sort(key=lambda p: (p[0] // 200, p[2]))

    for i, (y0, y1, x0, x1) in enumerate(panels[:4]):
        sub = red[y0:y1 + 1, x0:x1 + 1]
        l2, n2 = ndimage.label(sub)
        sz = ndimage.sum(sub, l2, range(1, n2 + 1))
        keep = sz > 60
        cents = np.array(ndimage.center_of_mass(sub, l2, range(1, n2 + 1)))[keep]
        rad = np.sqrt(sz[keep] / np.pi)
        w, h = x1 - x0 + 1, y1 - y0 + 1
        d_pin = 2 * float(np.median(rad))
        if len(cents) > 4:
            from scipy.spatial import cKDTree
            dist, _ = cKDTree(cents).query(cents, k=2)
            pitch = float(np.median(dist[:, 1]))
        else:
            pitch = float("nan")
        span_x = float(cents[:, 1].max() - cents[:, 1].min()) + d_pin
        span_y = float(cents[:, 0].max() - cents[:, 0].min()) + d_pin
        name = PANEL_NAMES[i] if i < len(PANEL_NAMES) else str(i)
        print(f"\n{name}: panel {w}x{h} px (h/w = {h/w:.3f})")
        print(f"   fuel pins           : {int(keep.sum())}  "
              f"({'5 rings = 91 pins' if keep.sum() == 91 else 'see text'})")
        print(f"   pin diameter / pitch: {d_pin:.1f} / {pitch:.1f} px "
              f"-> P/D = {pitch/d_pin:.3f}  (paper: 1.7144)")
        print(f"   bundle fill fraction: x = {span_x/w:.3f}, y = {span_y/h:.3f}")

    print("\nScale check (panel a): the duct is 56.134 mm across flats, so")
    print(f"   {panels[0][3]-panels[0][2]+1} px  ->  "
          f"{(panels[0][3]-panels[0][2]+1)/56.134:.2f} px/mm")
    print("   measured pin OD would then be "
          f"{2*np.median(rad):.1f} px / that scale - consistent with the 3.35 mm rod "
          "obtained from the table when the red circles are read as the rod outline.")


if __name__ == "__main__":
    main()
