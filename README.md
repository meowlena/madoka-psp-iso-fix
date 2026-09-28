# madoka-psp-iso-fix

Fix for **Mahou Shoujo Madoka Magica Portable (ULJS00430) + English Patch 4.0** showing a black screen in PPSSPP and returning to the menu after applying the patch on Linux.

This happens when the ISO is **rebuilt** with tools such as `xorriso`, `mkisofs`, `genisoimage`, or some GUI ISO editors. The patch files themselves are valid, but rebuilding the ISO changes its directory entries in a way that can prevent PPSSPP from finding files the game expects.

This project provides a small Python script that applies the patch **in place**, without rebuilding the ISO.

## Quick start

You need:

* A clean **Mahou Shoujo Madoka Magica Portable (Japan)** ISO
* **Madoka Magica Portable English Patch 4.0**
* Python 3
* About 4 GB of free disk space

The script does not require `pip`, additional Python packages, `sudo`, or an internet connection.

Run:

```bash
python3 inplace_patch.py CLEAN_ISO OUTPUT_ISO PATCH_DIR
```

For example:

```bash
python3 inplace_patch.py \
    "/home/you/Games/madoka-clean.iso" \
    "/home/you/Games/Madoka (Translated).iso" \
    "/home/you/Downloads/Madoka Magica Portable Patch 4.0"
```

The original ISO is never modified. A new translated ISO is created at `OUTPUT_ISO`.

Once it finishes, open the new ISO in PPSSPP.

---

## Step by step

### 1. Check that Python 3 is installed

Open a terminal and run:

```bash
python3 --version
```

If you see something like:

```text
Python 3.11.9
```

you are ready.

If Python is not installed:

**Fedora:**

```bash
sudo dnf install python3
```

**Ubuntu/Debian:**

```bash
sudo apt install python3
```

No additional Python packages are needed.

### 2. Download the script

Download `inplace_patch.py` from this repository and save it somewhere you can easily find.

You can download the file directly from GitHub by opening it and selecting **Raw**, then saving the file.

### 3. Prepare the files

You need two things.

#### The clean ISO

This must be the original, unpatched **Mahou Shoujo Madoka Magica Portable (Japan)** ISO.

The expected redump release has this MD5:

```text
c62edbc718367597feb3deced5032e4d
```

If you want to verify it on Linux:

```bash
md5sum "/path/to/madoka-clean.iso"
```

If the hash is different, stop and make sure you have the correct ISO.

> The script cannot repair an already rebuilt/broken translated ISO. It needs the original clean ISO as its input.

#### The English Patch 4.0 files

Extract the English Patch 4.0 so that you have a folder containing:

```text
archive.cpk
install.cpk
font.fnt
ICON0.png
```

You do not need to rename these files.

### 4. Run the script

The command has three paths, always in this order:

```text
CLEAN_ISO  OUTPUT_ISO  PATCH_DIR
```

| Parameter    | Meaning                                            |
| ------------ | -------------------------------------------------- |
| `CLEAN_ISO`  | Your original, unpatched ISO                       |
| `OUTPUT_ISO` | The new translated ISO that the script will create |
| `PATCH_DIR`  | The folder containing the four Patch 4.0 files     |

For example:

```bash
python3 inplace_patch.py \
    "/home/you/Games/madoka-clean.iso" \
    "/home/you/Games/Madoka (Translated).iso" \
    "/home/you/Downloads/Madoka Magica Portable Patch 4.0"
```

If a path contains spaces, put it inside quotes.

You can also drag files and folders from your file manager into the terminal to insert their paths automatically.

The script will copy the clean ISO and create the translated version. The original ISO is not modified.

### 5. Check the output

A successful run should end with something similar to:

```text
copying madoka-clean.iso -> /home/you/Games/Madoka (Translated).iso ...
root dir: extent=22 size=2048
PSP_GAME/ICON0.PNG: LBA 55724 (15097 B) -> 763696 (32261 B)
PSP_GAME/USRDIR/archive.cpk: LBA 558676 (65583400 B) -> 763712 (124555632 B)
PSP_GAME/USRDIR/install.cpk: LBA 590700 (93538040 B) -> 824531 (185947896 B)
PSP_GAME/USRDIR/Font/font.fnt: LBA 636373 (451920 B) -> 915326 (455952 B)
OK: /home/you/Games/Madoka (Translated).iso
sectors: 915549 (1875044352 bytes)
```

The exact LBAs and file sizes may differ depending on the input, but you should see `OK` at the end.

### 6. Play

Open the newly created ISO in PPSSPP.

Keep your clean ISO somewhere safe. It is the source for future runs of the script.

---

## Why does this happen?

The official English Patch 4.0 instructions use `WQSG_UMD.exe`, a Windows tool that modifies the ISO without rebuilding its filesystem.

On Linux, there is no commonly available equivalent. A natural workaround is to extract the ISO, replace the files, and rebuild it using a tool such as `xorriso`.

Unfortunately, this can change the filenames inside the ISO.

For example, the original ISO may contain:

```text
archive.cpk
Font/font.fnt
```

After rebuilding, they can become:

```text
ARCHIVE.CPK;1
FONT/FONT.FNT;1
```

PPSSPP's ISO filesystem lookup is case-sensitive for these paths. The game requests:

```text
PSP_GAME/USRDIR/archive.cpk
```

but the rebuilt ISO contains:

```text
PSP_GAME/USRDIR/ARCHIVE.CPK
```

As a result, the game cannot find the file and may return to the PPSSPP menu with a black screen.

The patch files are not the problem. **Rebuilding the ISO is.**

The script avoids this by keeping the original filesystem structure and filenames intact.

---

## What the script does

Instead of rebuilding the ISO, `inplace_patch.py`:

1. Copies the clean ISO byte-for-byte.
2. Appends the four patched files to the end of the copy.
3. Updates only the relevant directory records.
4. Updates the ISO volume size.
5. Pads the final sector to the required 2048-byte boundary.

The original directory structure, path table, root directory, and filenames remain unchanged.

This is essentially the same approach needed to reproduce the in-place modification performed by the Windows patching tool.

---

## Requirements

### Required

| Requirement      | Details                  |
| ---------------- | ------------------------ |
| Python 3.6+      | Standard library only    |
| Free disk space  | About 4 GB               |
| Operating system | Linux, macOS, or Windows |

There is no need to install Python packages:

```text
pip install ...
```

is **not** required.

There is also no need for:

* `sudo`
* root access
* mounting the ISO
* a PSP or custom firmware
* an internet connection
* `xorriso`
* `mkisofs`
* `genisoimage`
* a GUI ISO editor
* WQSG_UMD
* UMDGen
* Wine

In fact, rebuilding the ISO with the first group of tools is what causes the problem this script is designed to avoid.

---

## Using custom patch files

For Madoka Magica Portable English Patch 4.0, the four target files are built into the script, so you do not need any extra options.

The script can also be used with other files by specifying the targets manually with `-t`.

For example:

```bash
python3 inplace_patch.py clean.iso out.iso ./patch-files \
    -t PSP_GAME/ICON0.PNG=icon0.png \
    -t PSP_GAME/USRDIR/data.cpk=data.cpk
```

The left side is the path that already exists inside the ISO. The right side is the filename inside your patch directory.

---

## Troubleshooting

### `error: the following arguments are required: ...`

One or more of the three required paths is missing.

Make sure you provide:

```text
CLEAN_ISO OUTPUT_ISO PATCH_DIR
```

in that order.

### `CLEAN_ISO not found: ...`

The path to the clean ISO is incorrect.

Check the filename and path. If it contains spaces, use quotes:

```bash
"/home/you/Games/Madoka Magica.iso"
```

### `PATCH_DIR not found: ...`

The patch directory path is incorrect.

Make sure it points to the folder containing:

```text
archive.cpk
install.cpk
font.fnt
ICON0.png
```

### `'font.fnt' not found in ...`

The patch directory does not contain one of the expected files.

Check that you extracted **English Patch 4.0** correctly and that the files are present.

### `record not found: ...`

The clean ISO does not appear to be the expected redump release.

Check the MD5 of the ISO:

```bash
md5sum "/path/to/madoka-clean.iso"
```

It should be:

```text
c62edbc718367597feb3deced5032e4d
```

### `PVD not found at sector 16!`

The file provided as `CLEAN_ISO` is not a valid PSP UMD ISO.

Make sure you did not accidentally provide the already rebuilt/broken ISO.

### `OUTPUT_ISO must differ from CLEAN_ISO ...`

The input and output paths point to the same file.

Choose a different filename for the translated ISO.

### The new ISO still shows a black screen

First make sure PPSSPP is actually loading the ISO you just created.

You can also verify the output hash using the reference information below.

If the output does not match the expected result, check that:

1. You started with the correct clean ISO.
2. You used the correct Patch 4.0 files.
3. You did not rebuild or otherwise modify the output ISO after running the script.

---

## Verification

The reference files used during development have the following hashes.

### Patch 4.0 files

```text
ICON0.png   22e426d749c7686c91169b598f7f2497
archive.cpk eee2129b656a935435d7f8ea8027e634
install.cpk 7a0ee0709858bb5028a85df8fa987867
font.fnt    625452068059e6b9cbe81f732cd18098
```

### ISO images

| Image                  | MD5                                |            Size |
| ---------------------- | ---------------------------------- | --------------: |
| Clean redump ISO       | `c62edbc718367597feb3deced5032e4d` | 1,564,049,408 B |
| Broken xorriso rebuild | `5fa9b15529144f8c099c7a8f1faa0b8f` | 1,878,245,376 B |
| Fixed in-place patch   | `71a7820b7c6d892edfb02b0f80a1c68f` | 1,875,044,352 B |

The reference output was tested with **PPSSPP 1.20.4 on Fedora** and on an **R36S handheld**.

To calculate the MD5 of your output on Linux:

```bash
md5sum "/path/to/Madoka (Translated).iso"
```

The reference output has:

```text
71a7820b7c6d892edfb02b0f80a1c68f
```

A matching hash means your output is byte-for-byte identical to the reference image.

---

## Technical details

The clean redump ISO has its original directory records and mixed-case filenames preserved.

The rebuilt ISO produced during the investigation had a different directory structure, including uppercase ISO9660 names and `;1` version suffixes.

The script therefore does not recreate the ISO filesystem. It modifies only the directory records required to point to the four patched files appended to the image.

The resulting filesystem remains identical to the clean ISO except for the updated file extents, file sizes, and volume size.

Re-running the script with the same inputs reproduces the reference output byte-for-byte.

---

## AI assistance

This project was developed with assistance from **MiMo** (`mimo-v2.6-flash-free`) running inside OpenCode.

The diagnosis, investigation, `inplace_patch.py`, and documentation were AI-assisted. The resulting ISO was manually tested on PPSSPP 1.20.4 on Fedora and on an R36S handheld.

Because the code was AI-generated, the reference hashes are included so that the output can be independently verified rather than simply trusted.

Use the script at your own risk.

---

## License / Disclaimer

This project does not include the game ISO or the English patch files.

You must obtain the game and patch files separately and use them according to their respective licenses and terms.

The script only modifies files you provide locally. It does not download, distribute, or include copyrighted game or patch data.

---

## TL;DR

If the Madoka Magica Portable English Patch 4.0 works on the original ISO but your Linux-built translated ISO gives you a black screen in PPSSPP:

**Do not rebuild the ISO.**

Use the clean ISO and run:

```bash
python3 inplace_patch.py CLEAN_ISO OUTPUT_ISO PATCH_DIR
```

The script applies the patch without changing the original ISO filesystem structure.

Then play the resulting `OUTPUT_ISO` in PPSSPP.
