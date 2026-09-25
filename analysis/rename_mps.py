#!/usr/bin/env python3
"""
Rename .mps and .vnnlib files that contain long float representations in their filename,
e.g. mnist-net_256x2_6_0_0249999999999999.mps -> mnist-net_256x2_6_0_025.mps

Dry-run default. Set DRY_RUN=False to perform renames.
"""

import os
import re
from decimal import Decimal, InvalidOperation, getcontext

# ========== CONFIG ==========
BASE_PATH = "/home/annelot/WARMSTART_PROJECT/baseline_symphony_21-01-2026+15_00/tmp"  # <- change this to your base path
PRECISION = 3         # number of decimal places to keep when rounding epsilons
DRY_RUN = False        # True = only print what would be renamed. Set to False to actually rename.
# ============================

# increase decimal context precision so Decimal conversions keep accuracy
getcontext().prec = 20

# match filenames that have an epsilon fragment before the extension.
# We assume the epsilon is the last numeric fragment before the extension,
# possibly using "_" as decimal separator, e.g. "..._0_0249999999999999.mps"
EPS_PATTERN = re.compile(r"(?P<prefix>.*_)(?P<eps>\d+[._]\d+)(?P<suffix>\.\w+)$")

def canonical_epsilon_str(eps_float, precision=PRECISION):
    """
    Format epsilon as a canonical string:
      - round to `precision` decimals
      - remove trailing zeros (so 0.025000 -> 0.025)
      - convert '.' -> '_' for filename
    """
    # Use Decimal for stable rounding/formatting
    d = Decimal(str(eps_float)).quantize(Decimal(10) ** -precision)
    # Remove trailing zeros and possible trailing dot
    s = format(d.normalize(), 'f')  # 'f' gives fixed-point, normalize removes exponent
    # Edge-case: Decimal('0E-6').normalize() gives '0'
    # Convert decimal point to underscore for filename
    return s.replace('.', '_')

def find_and_rename(base_path):
    changes = []  # tuples (old_path, new_path)

    for root, dirs, files in os.walk(base_path):
        for fname in files:
            if not (fname.endswith('.mps') or fname.endswith('.vnnlib')):
                continue

            m = EPS_PATTERN.match(fname)
            if not m:
                # No epsilon-like fragment found — skip
                continue

            prefix = m.group('prefix')        # all up to last underscore before eps
            eps_text = m.group('eps')         # e.g. '0_0249999999999999' or '0.0249999'
            suffix = m.group('suffix')        # e.g. '.mps'

            # Normalize '_' -> '.' for parse
            eps_text_dot = eps_text.replace('_', '.')
            try:
                eps_float = float(eps_text_dot)
            except ValueError:
                # Can't parse to float — skip
                print(f"Warning: cannot parse epsilon '{eps_text}' in file {os.path.join(root, fname)}; skipping")
                continue

            # Build canonical epsilon string and new filename
            canon_eps_frag = canonical_epsilon_str(eps_float, PRECISION)
            new_fname = f"{prefix}{canon_eps_frag}{suffix}"
            old_path = os.path.join(root, fname)
            new_path = os.path.join(root, new_fname)

            # If new_path already exists and is the same file, skip
            if os.path.abspath(old_path) == os.path.abspath(new_path):
                continue

            # If colliding filename exists, warn & skip to avoid overwriting
            if os.path.exists(new_path):
                print(f"Conflict: target file exists, skipping rename: {new_path}")
                continue

            changes.append((old_path, new_path))

            # Also try to rename the paired file of the other extension (mps<->vnnlib) if present
            # Example: if current is ..._0_024... .mps, check for same prefix + eps + .vnnlib
            other_suffix = '.vnnlib' if suffix == '.mps' else '.mps'
            other_old = os.path.join(root, f"{prefix}{eps_text}{other_suffix}")
            other_new = os.path.join(root, f"{prefix}{canon_eps_frag}{other_suffix}")
            if os.path.exists(other_old):
                if not os.path.exists(other_new):
                    changes.append((other_old, other_new))
                else:
                    print(f"Conflict for associated file: {other_new} exists. Skipping associated rename.")

    # Print or apply changes
    if not changes:
        print("No files detected that match the epsilon pattern. Nothing to do.")
        return

    print("Proposed renames:")
    for oldp, newp in changes:
        print(f"  {oldp}  ->  {newp}")

    if DRY_RUN:
        print("\nDRY RUN enabled. No files were actually renamed.")
        print("If the proposed changes look correct, set DRY_RUN=False and run again.")
        return

    # apply renames
    for oldp, newp in changes:
        try:
            os.rename(oldp, newp)
        except Exception as e:
            print(f"Failed to rename {oldp} -> {newp}: {e}")

    print("Renaming complete.")

if __name__ == "__main__":
    print(f"Running rename on base path: {BASE_PATH}\nPRECISION={PRECISION}, DRY_RUN={DRY_RUN}\n")
    find_and_rename(BASE_PATH)
