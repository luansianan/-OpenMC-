#!/usr/bin/env python3
"""Download the ENDF/B-VIII.0 neutron sub-library files used by the model.

Source: IAEA Nuclear Data Services (https://www-nds.iaea.org/public/download-endf/),
which serves the evaluated ENDF-6 files as per-nuclide ZIP archives and - unlike the
ANL Box / NNDC / TENDL mirrors - is reachable and scriptable.

The 24 nuclides below are those needed for UO2 fuel, Pb-Bi eutectic coolant,
HT-9 structure (Fe/Cr/Mo expanded into natural isotopes) and the helium gap.

Usage:
    python3 environment/fetch_endf.py            # into /root/endf
    ENDF_DIR=/somewhere python3 environment/fetch_endf.py
"""
import os
import re
import time
import urllib.request
import zipfile

BASE = "https://www-nds.iaea.org/public/download-endf/ENDF-B-VIII.0/n/"
OUT = os.environ.get("ENDF_DIR", "/root/endf")
RAW = os.path.join(OUT, "raw")
UA = {"User-Agent": "Mozilla/5.0"}

WANT = [
    ("U", 235), ("U", 238), ("O", 16),                     # UO2 fuel
    ("Pb", 204), ("Pb", 206), ("Pb", 207), ("Pb", 208),    # natural Pb
    ("Bi", 209),                                           # LBE
    ("Fe", 54), ("Fe", 56), ("Fe", 57), ("Fe", 58),        # natural Fe (HT-9)
    ("Cr", 50), ("Cr", 52), ("Cr", 53), ("Cr", 54),        # natural Cr (HT-9)
    ("Mo", 92), ("Mo", 94), ("Mo", 95), ("Mo", 96),
    ("Mo", 97), ("Mo", 98), ("Mo", 100),                   # natural Mo (HT-9)
    ("He", 4),                                             # helium gap
]


def main():
    os.makedirs(RAW, exist_ok=True)
    print("fetching directory listing ...")
    html = urllib.request.urlopen(
        urllib.request.Request(BASE, headers=UA), timeout=120
    ).read().decode("utf-8", "ignore")

    index = {}
    for f in re.findall(r'href="(n_[^"]+\.zip)"', html):
        m = re.match(r"n_(\d+)_(\d+)-([A-Za-z]+)-(\d+)M?\.zip$", f)
        if m:
            index[(m.group(3), int(m.group(4)))] = f
    print(f"{len(index)} entries in listing")

    missing = [w for w in WANT if w not in index]
    if missing:
        print("MISSING:", missing)

    for sym, a in WANT:
        fname = index.get((sym, a))
        if not fname:
            continue
        dest = os.path.join(OUT, fname)
        if not (os.path.exists(dest) and os.path.getsize(dest) > 1000):
            try:
                data = urllib.request.urlopen(
                    urllib.request.Request(BASE + fname, headers=UA), timeout=180
                ).read()
                with open(dest, "wb") as fh:
                    fh.write(data)
                time.sleep(3)                    # be polite / avoid HTTP 403
            except Exception as exc:             # noqa: BLE001
                print(f"ERR {sym}-{a}: {exc}")
                time.sleep(5)
                continue
        with zipfile.ZipFile(dest) as zf:
            zf.extractall(RAW)
        print(f"OK  {sym}-{a:<4} {fname:<28} {os.path.getsize(dest)/1024:8.0f} kB")

    print("\nENDF files in", RAW)
    for f in sorted(os.listdir(RAW)):
        print("  ", f)


if __name__ == "__main__":
    main()
