#!/usr/bin/env python3
"""Patch a PSP ISO in place (WQSG_UMD style) instead of rebuilding it.

Steps:
  1. copy the clean (redump) ISO byte for byte
  2. move nothing: PVD, path table and root dir keep their original offsets
  3. append the replacement files at the end of the image (aligned to 2048-byte sectors)
  4. rewrite ONLY those files' directory records (extent + size)
  5. update the PVD volume space size and pad the final sector

Why: 
    rebuilding the image with xorriso/mkisofs or a GUI ISO editor rewrites the
    ISO9660 directory with strict names (UPPERCASE + ";1" version suffix). PPSSPP matches
    paths case-sensitively (confirmed in PPSSPP's ISOFileSystem.cpp), so the game's
    disc0:/PSP_GAME/USRDIR/archive.cpk no longer matches ARCHIVE.CPK;1 -> file not found
    -> black screen. Patching in place keeps the original names the game asks for.

Usage:
  python3 inplace_patch.py CLEAN_ISO OUTPUT_ISO PATCH_DIR
  python3 inplace_patch.py CLEAN_ISO OUTPUT_ISO PATCH_DIR \\
      -t PSP_GAME/USRDIR/data.cpk=local/data.cpk

Without -t, the four files that Madoka Magica Portable English Patch 4.0 replaces are
used (these paths belong to that patch, not to ISO9660 in general); each is looked up
inside PATCH_DIR by name, case-insensitively.

verify.py checks the result: same folder, no extra dependencies.
"""
import argparse
import os
import shutil
import struct
import sys

BS = 2048
ISO9660_MAX = 0xFFFFFFFF   # extent and size fields are 32-bit
FLAG_DIRECTORY = 0x02      # ISO9660 file flags: bit 1 = directory

# The four files English Patch 4.0 replaces — specific to Madoka Magica Portable,
# not a generic property of this tool. Override with -t for another game.
DEFAULT_TARGETS = [
    ("PSP_GAME/ICON0.PNG", "ICON0.png"),
    ("PSP_GAME/USRDIR/archive.cpk", "archive.cpk"),
    ("PSP_GAME/USRDIR/install.cpk", "install.cpk"),
    ("PSP_GAME/USRDIR/Font/font.fnt", "font.fnt"),
]


def norm(name: bytes) -> str:
    """Normalize a primary ISO9660 name for case/version-insensitive lookup."""
    if name in (b"\x00", b"\x01"):
        return ""
    name = name.split(b";", 1)[0]
    return name.decode("latin1").upper()


def read_at(f, lba, size):
    f.seek(lba * BS)
    return f.read(size)


def find_record(f, dir_extent, dir_size, wanted: str):
    """Return (absolute offset, extent, size, flags) of `wanted` in this directory,
    or (None, None, None, None) when not found. Exits with a clear message on a
    malformed record instead of reading past its end."""
    data = read_at(f, dir_extent, dir_size)
    off = 0
    while off < len(data):
        ln = data[off]
        if ln == 0:  # end of this sector's records
            off = ((off // BS) + 1) * BS
            continue
        if ln < 34 or off + ln > len(data):
            sys.exit(f"invalid ISO9660 directory record at byte "
                     f"{dir_extent * BS + off} (length {ln}): this does not look "
                     f"like a valid ISO image")
        rec = data[off:off + ln]
        namelen = rec[32]
        if 33 + namelen > ln:
            sys.exit(f"invalid ISO9660 file identifier length at byte "
                     f"{dir_extent * BS + off}")
        extent = struct.unpack("<I", rec[2:6])[0]
        size = struct.unpack("<I", rec[10:14])[0]
        flags = rec[25]
        rawname = rec[33:33 + namelen]
        if norm(rawname) == wanted.upper():
            return dir_extent * BS + off, extent, size, flags
        off += ln
    return None, None, None, None


def resolve_local(patch_dir, filename):
    """find filename inside patch_dir, case-insensitively."""
    entries = sorted(os.listdir(patch_dir))
    for entry in entries:
        if entry.lower() == filename.lower():
            return os.path.join(patch_dir, entry)
    listing = ", ".join(entries) or "(empty)"
    sys.exit(f"'{filename}' not found in {patch_dir}\nAvailable files: {listing}")


def parse_args():
    p = argparse.ArgumentParser(
        description="Patch a PSP ISO in place instead of rebuilding it (fixes the "
                    "PPSSPP black screen caused by uppercase ISO9660 file names).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python3 inplace_patch.py clean.iso translated.iso ./madoka-patch\n"
               "  python3 inplace_patch.py clean.iso out.iso ./patch \\\n"
               "      -t PSP_GAME/ICON0.PNG=icon0.png \\\n"
               "      -t PSP_GAME/USRDIR/data.cpk=data.cpk\n")
    p.add_argument("src", metavar="CLEAN_ISO",
                   help="clean (redump) ISO, copied byte for byte")
    p.add_argument("dst", metavar="OUTPUT_ISO",
                   help="path of the patched ISO to write")
    p.add_argument("patch_dir", metavar="PATCH_DIR",
                   help="folder with the replacement files")
    p.add_argument("-t", "--target", action="append", default=[],
                   metavar="ISO_PATH[=LOCAL_FILE]",
                   help="file to patch: path inside the ISO, optionally = local file "
                        "(relative to PATCH_DIR). Repeatable. Default: the 4 Madoka "
                        "Patch 4.0 targets")
    return p.parse_args()


def build_targets(args):
    if not os.path.isdir(args.patch_dir):
        sys.exit(f"PATCH_DIR not found: {args.patch_dir}")

    targets = []
    if args.target:
        for spec in args.target:
            if "=" in spec:
                isopath, local = spec.split("=", 1)
                if not os.path.isabs(local):
                    candidate = os.path.join(args.patch_dir, local)
                    local = candidate if os.path.isfile(candidate) else local
            else:
                isopath, local = spec, None
            isopath = isopath.strip("/")
            if not isopath:
                sys.exit(f"invalid --target: {spec}")
            if local is None:
                local = resolve_local(args.patch_dir, isopath.rsplit("/", 1)[-1])
            if not os.path.isfile(local):
                sys.exit(f"replacement file not found: {local}")
            targets.append((isopath.split("/"), local))
    else:
        for isopath, name in DEFAULT_TARGETS:
            targets.append((isopath.split("/"), resolve_local(args.patch_dir, name)))
    return targets


def check_duplicates(targets):
    """Two -t flags resolving to the same record would silently patch it twice."""
    seen = set()
    for components, _ in targets:
        key = "/".join(part.split(";")[0].upper() for part in components)
        if key in seen:
            sys.exit(f"duplicate target: {'/'.join(components)}")
        seen.add(key)


def main():
    args = parse_args()
    if not os.path.isfile(args.src):
        sys.exit(f"CLEAN_ISO not found: {args.src}")
    if os.path.abspath(args.src) == os.path.abspath(args.dst):
        sys.exit("OUTPUT_ISO must differ from CLEAN_ISO (the source is copied, "
                 "not modified)")
    targets = build_targets(args)
    check_duplicates(targets)

    print(f"copying {os.path.basename(args.src)} -> {args.dst} ...")
    shutil.copyfile(args.src, args.dst)

    with open(args.dst, "r+b") as f:
        # --- PVD ---
        f.seek(16 * BS)
        pvd = bytearray(f.read(BS))
        if pvd[1:6] != b"CD001" or pvd[0] != 1:
            sys.exit("PVD not found at sector 16!")
        # root dir record in the PVD (offset 156, 34 bytes)
        root_extent = struct.unpack("<I", pvd[156 + 2:156 + 6])[0]
        root_size = struct.unpack("<I", pvd[156 + 10:156 + 14])[0]
        print(f"root dir: extent={root_extent} size={root_size}")

        # current image size (end of data) -> append from there
        end = os.path.getsize(args.dst)
        if end % BS:
            sys.exit("source ISO does not end on a sector boundary")

        for components, patchfile in targets:
            # walk down to the parent directory, checking each step is a directory
            extent, size = root_extent, root_size
            for i, comp in enumerate(components[:-1]):
                _, extent, size, flags = find_record(f, extent, size, comp)
                if extent is None:
                    sys.exit(f"directory not found: {'/'.join(components[:i + 1])}")
                if not flags & FLAG_DIRECTORY:
                    sys.exit(f"not a directory: {'/'.join(components[:i + 1])} "
                             f"(cannot descend into a file)")

            leaf = components[-1]
            rec_off, old_extent, old_size, flags = find_record(f, extent, size, leaf)
            if rec_off is None:
                sys.exit(f"record not found: {'/'.join(components)} "
                         f"(ISO9660 names may be shorter than the real path)")
            if flags & FLAG_DIRECTORY:
                sys.exit(f"target is a directory, not a file: {'/'.join(components)}")

            # `end` always points at the next free sector here
            new_lba = end // BS
            if new_lba > ISO9660_MAX:
                sys.exit("patched image would exceed the ISO9660 32-bit extent limit")
            with open(patchfile, "rb") as pf:
                data = pf.read()
            new_size = len(data)
            if new_size > ISO9660_MAX:
                sys.exit(f"replacement file is too large for ISO9660 (> 4 GB): "
                         f"{patchfile}")

            f.seek(end)
            f.write(data)
            end += new_size
            if end % BS:
                end += BS - (end % BS)

            # patch the record IN PLACE (same record length)
            f.seek(rec_off)
            len_dr = f.read(1)[0]
            f.seek(rec_off)
            rec = bytearray(f.read(len_dr))
            struct.pack_into("<I", rec, 2, new_lba)    # extent LE
            struct.pack_into(">I", rec, 6, new_lba)    # extent BE
            struct.pack_into("<I", rec, 10, new_size)  # size LE
            struct.pack_into(">I", rec, 14, new_size)  # size BE
            f.seek(rec_off)
            f.write(rec)

            print(f"{'/'.join(components)}: LBA {old_extent} ({old_size} B) -> "
                  f"{new_lba} ({new_size} B)")

        # --- update the volume space size in the PVD ---
        total_sectors = end // BS
        if total_sectors > ISO9660_MAX:
            sys.exit("volume space size would exceed the ISO9660 32-bit limit")
        struct.pack_into("<I", pvd, 80, total_sectors)
        struct.pack_into(">I", pvd, 84, total_sectors)
        f.seek(16 * BS)
        f.write(pvd)
        # pad the final sector: image size must be exactly sectors * 2048
        f.truncate(total_sectors * BS)

        f.flush()
        os.fsync(f.fileno())

    print(f"OK: {args.dst}")
    print(f"sectors: {total_sectors} ({total_sectors * BS} bytes)")


if __name__ == "__main__":
    main()
