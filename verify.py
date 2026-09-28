#!/usr/bin/env python3
"""Verify that a patched ISO differs from its clean source only where it should.

Patching in place is only worth anything if nothing else in the image moves, so this
checks exactly that:

  1. the patched image has a valid PVD and its size is exactly
     volume space size * 2048 (and a multiple of 2048);
  2. every byte of the clean ISO is still there, except
       - the PVD volume space size field (bytes 80-87 of sector 16)
       - the extent/size fields (bytes 2-17) of each target's directory record
     which proves PVD, path tables, root dir, EBOOT.BIN and every original file are
     untouched (a rebuilt image fails here);
  3. each target record sits at the same byte offset as in the clean ISO;
  4. with PATCH_DIR, the bytes stored at each target hash-match the local files.

Usage:
  python3 verify.py CLEAN_ISO PATCHED_ISO [PATCH_DIR]
  python3 verify.py CLEAN_ISO PATCHED_ISO PATCH_DIR \\
      -t PSP_GAME/USRDIR/data.cpk=data.cpk

Keep this file next to inplace_patch.py (it imports from it).
"""
import argparse
import hashlib
import os
import struct
import sys

from inplace_patch import BS, DEFAULT_TARGETS, build_targets, find_record

CHUNK = 4 * 1024 * 1024
PVD_VOLUME_SIZE = (80, 88)      # both-endian 32+32 "volume space size" in the PVD
RECORD_FIELDS = (2, 18)         # extent LE/BE (2-9) + size LE/BE (10-17)


def read_pvd(f, label):
    f.seek(16 * BS)
    pvd = f.read(BS)
    if len(pvd) < BS or pvd[0] != 1 or pvd[1:6] != b"CD001":
        sys.exit(f"{label}: no valid PVD at sector 16 — not a plain ISO image?")
    return pvd


def locate(f, components):
    """(offset, extent, size) of a path inside the image, or a clear error."""
    pvd = read_pvd(f, "image")
    extent = struct.unpack("<I", pvd[158:162])[0]
    size = struct.unpack("<I", pvd[166:170])[0]
    for i, comp in enumerate(components[:-1]):
        _, extent, size, flags = find_record(f, extent, size, comp)
        if extent is None:
            sys.exit(f"path not found: {'/'.join(components[:i + 1])} — this image "
                     f"has a different layout than expected")
        if not flags & 0x02:
            sys.exit(f"not a directory: {'/'.join(components[:i + 1])}")
    rec_off, extent, size, flags = find_record(f, extent, size, components[-1])
    if rec_off is None:
        sys.exit(f"path not found: {'/'.join(components)}")
    if flags & 0x02:
        sys.exit(f"is a directory, not a file: {'/'.join(components)}")
    return rec_off, extent, size


def md5_local(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_at(f, lba, size):
    h = hashlib.md5()
    f.seek(lba * BS)
    left = size
    while left > 0:
        chunk = f.read(min(CHUNK, left))
        if not chunk:
            sys.exit(f"unexpected end of image reading {size} bytes at LBA {lba}")
        h.update(chunk)
        left -= len(chunk)
    return h.hexdigest()


def load_targets(args):
    if args.patch_dir:
        return build_targets(args)          # also validates PATCH_DIR
    if args.target:
        out = []
        for spec in args.target:
            if "=" in spec:
                sys.exit("-t with a local file requires PATCH_DIR as third argument")
            path = spec.strip("/")
            if not path:
                sys.exit(f"invalid --target: {spec}")
            out.append((path.split("/"), None))
        return out
    return [(path.split("/"), None) for path, _ in DEFAULT_TARGETS]


def parse_args():
    p = argparse.ArgumentParser(
        description="Verify that a patched ISO differs from the clean source only at "
                    "the expected places (PVD volume size + the patched records).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python3 verify.py clean.iso translated.iso ./madoka-patch\n"
               "  python3 verify.py clean.iso translated.iso\n")
    p.add_argument("clean", metavar="CLEAN_ISO",
                   help="the original image the patch was applied to")
    p.add_argument("patched", metavar="PATCHED_ISO",
                   help="the image to check")
    p.add_argument("patch_dir", metavar="PATCH_DIR", nargs="?", default=None,
                   help="folder with the replacement files: also verifies contents")
    p.add_argument("-t", "--target", action="append", default=[],
                   metavar="ISO_PATH[=LOCAL_FILE]",
                   help="same targets passed to inplace_patch.py. Repeatable. "
                        "Default: the 4 Madoka Patch 4.0 targets")
    return p.parse_args()


def main():
    args = parse_args()
    for path, label in ((args.clean, "CLEAN_ISO"), (args.patched, "PATCHED_ISO")):
        if not os.path.isfile(path):
            sys.exit(f"{label} not found: {path}")
    targets = load_targets(args)

    clean_size = os.path.getsize(args.clean)
    patched_size = os.path.getsize(args.patched)
    if clean_size % BS:
        sys.exit(f"clean ISO size is not a multiple of 2048: {clean_size}")
    if patched_size % BS:
        sys.exit(f"patched image size is not a multiple of 2048: {patched_size}")
    if patched_size < clean_size:
        sys.exit("patched image is smaller than the clean ISO")

    with open(args.clean, "rb") as clean, open(args.patched, "rb") as patched:
        read_pvd(clean, "clean ISO")
        pvd = read_pvd(patched, "patched ISO")
        total = struct.unpack("<I", pvd[80:84])[0]
        total_be = struct.unpack(">I", pvd[84:88])[0]
        if total != total_be:
            sys.exit(f"patched PVD volume size is inconsistent: {total} != {total_be}")
        if patched_size != total * BS:
            sys.exit(f"size mismatch: file is {patched_size} bytes but the PVD "
                     f"declares {total} sectors = {total * BS} bytes")
        print(f"OK: patched PVD valid, size {patched_size} bytes = {total} * 2048")

        allowed = [(16 * BS + PVD_VOLUME_SIZE[0], 16 * BS + PVD_VOLUME_SIZE[1])]
        for components, local in targets:
            label = "/".join(components)
            c_off, c_ext, c_size = locate(clean, components)
            p_off, p_ext, p_size = locate(patched, components)
            if c_off != p_off:
                sys.exit(f"layout changed: the record for {label} is at byte {c_off} "
                         f"in the clean ISO and {p_off} in the patched one — this "
                         f"image was rebuilt, not patched in place")
            if (c_ext, c_size) == (p_ext, p_size):
                sys.exit(f"not patched: {label} still points at the original data "
                         f"(LBA {p_ext}, {p_size} bytes)")
            allowed.append((p_off + RECORD_FIELDS[0], p_off + RECORD_FIELDS[1]))
            note = ""
            if local is not None:
                want = md5_local(local)
                got = md5_at(patched, p_ext, p_size)
                if got != want:
                    sys.exit(f"content mismatch: {label}\n  in image: {got}\n"
                             f"  in file: {want}")
                note = f", content md5 {got} matches"
            print(f"OK: {label} -> LBA {p_ext} ({p_size} bytes){note}")

        # byte-for-byte over the whole clean ISO, skipping only the allowed spans
        allowed.sort()
        merged = []
        for start, end in allowed:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])

        pos = 0
        for start, end in merged + [[clean_size, clean_size]]:
            if start > pos:
                clean.seek(pos)
                patched.seek(pos)
                left = start - pos
                while left > 0:
                    n = min(CHUNK, left)
                    a = clean.read(n)
                    b = patched.read(n)
                    if a != b:
                        i = next(i for i in range(n) if a[i] != b[i])
                        sys.exit(f"unexpected difference at byte {pos + i}: the "
                                 f"patched image must be byte-identical to the clean "
                                 f"ISO outside the PVD volume size field and the "
                                 f"patched records")
                    left -= n
                    pos += n
            pos = max(pos, end)
        print(f"OK: byte-identical to the clean ISO outside the {len(allowed)} "
              f"expected locations")

    print(f"verified: {args.patched}")


if __name__ == "__main__":
    main()
