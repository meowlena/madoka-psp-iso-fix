# madoka-psp-iso-fix

Fix for **Mahou Shoujo Madoka Magica Portable (ULJS00430) + English Patch 4.0** when the translated ISO shows a black screen in PPSSPP and returns to the menu after being created on Linux.

## The problem

The English Patch 4.0 was made to work with **WQSG_UMD**, which modifies the existing ISO without rebuilding its filesystem.

On Linux, the available ISO tools work differently. If you rebuild the ISO with tools such as `xorriso`, `mkisofs`, `genisoimage`, or some GUI ISO editors, parts of the ISO filesystem can be reorganized or renamed.

In my case, the patch files and the original ISO were correct, but the resulting ISO would show a black screen in PPSSPP and then return to the menu.

After investigating the problem with OpenCode, I found that the way the ISO was being rebuilt was the cause.

This project provides a small Python script that applies the patch **in place**, preserving the original ISO filesystem instead of rebuilding it.

## Requirements

You need:

* A clean **Mahou Shoujo Madoka Magica Portable (Japan)** ISO
* **Madoka Magica Portable English Patch 4.0**
* Python 3
* About 4 GB of free disk space

The script uses only Python's standard library. You do not need:

* `pip` or additional Python packages
* `sudo` or root access
* an internet connection
* `xorriso`, `mkisofs`, or `genisoimage`
* a GUI ISO editor
* WQSG_UMD or UMDGen
* Wine

The original ISO is never modified.

## Quick start

First, extract the English Patch 4.0 files so you have a folder containing:

```text
archive.cpk
install.cpk
font.fnt
ICON0.png
```

Then run it from the folder where you saved `inplace_patch.py`:

```bash
python3 inplace_patch.py CLEAN_ISO OUTPUT_ISO PATCH_DIR
```

For example:

```bash
cd /home/you/Downloads
python3 inplace_patch.py \
    "/home/you/Games/madoka-clean.iso" \
    "/home/you/Games/Madoka (Translated).iso" \
    "/home/you/Downloads/Madoka Magica Portable Patch 4.0"
```

The three arguments are:

| Argument     | Description                               |
| ------------ | ----------------------------------------- |
| `CLEAN_ISO`  | Your original, unpatched ISO              |
| `OUTPUT_ISO` | The new translated ISO to create          |
| `PATCH_DIR`  | The folder containing the Patch 4.0 files |

If a path contains spaces, put it inside quotes.

A successful run ends with `OK:` followed by the output path and a `sectors:` line (for example, `sectors: 915549 (1875044352 bytes)`).

When the script finishes, open `OUTPUT_ISO` in PPSSPP.

## Checking the clean ISO

The expected redump release has the following MD5:

```text
c62edbc718367597feb3deced5032e4d
```

On Linux:

```bash
md5sum "/path/to/madoka-clean.iso"
```

The script needs the **original clean ISO**. It cannot repair an ISO that has already been rebuilt.

## What the script does

The script:

1. Copies the clean ISO.
2. Adds the four translated files to the end of the copy.
3. Updates the corresponding ISO directory records to point to the new files.
4. Updates the ISO volume size.
5. Pads the final sector as required.

It does **not** rebuild the ISO filesystem.

This is important because rebuilding the ISO was the source of the problem in the first place.

## Custom targets

The default configuration is for the four files used by Madoka Magica Portable English Patch 4.0:

```text
PSP_GAME/ICON0.PNG
PSP_GAME/USRDIR/archive.cpk
PSP_GAME/USRDIR/install.cpk
PSP_GAME/USRDIR/Font/font.fnt
```

The script also supports custom files with `-t`:

```bash
python3 inplace_patch.py clean.iso out.iso ./patch-files \
    -t PSP_GAME/ICON0.PNG=icon0.png \
    -t PSP_GAME/USRDIR/data.cpk=data.cpk
```

The path on the left is the file already present in the ISO. The path on the right is the replacement file inside `PATCH_DIR`.

## Troubleshooting

### `python3: can't open file ...`

Make sure you are running the command from the folder containing `inplace_patch.py`, or provide the full path to the script:

```bash
python3 /path/to/inplace_patch.py CLEAN_ISO OUTPUT_ISO PATCH_DIR
```

### `CLEAN_ISO not found`

Check the path to your clean ISO. Remember to use quotes if the path contains spaces.

### `PATCH_DIR not found`

Check that the patch directory exists and contains the Patch 4.0 files.

### `'font.fnt' not found in ...`

Make sure you extracted the Patch 4.0 files correctly. The default configuration expects:

```text
archive.cpk
install.cpk
font.fnt
ICON0.png
```

### `record not found`

The ISO may not be the expected release. Check its MD5 against the value above.

### `PVD not found at sector 16!`

The input file is probably not a valid ISO9660 image. Make sure you are using the clean game ISO.

### `not a directory`, `target is a directory`, or `duplicate target`

These come from a `-t` option (see [Custom targets](#custom-targets)): the path goes through a file, points at a folder instead of a file, or the same record was passed twice — even a difference in capitalization counts as a duplicate.

### The ISO still shows a black screen

Make sure that:

1. You started with the original clean ISO.
2. You used the correct Patch 4.0 files.
3. You did not rebuild or modify the output ISO after running the script.
4. PPSSPP is loading the newly created ISO.

If the problem persists, feel free to [open an issue on GitHub](../../issues).

## Verification

A separate `verify.py` script is included to check the resulting ISO.

Run:

```bash
python3 verify.py CLEAN_ISO OUTPUT_ISO PATCH_DIR
```

The patch directory is optional. Without it, the script can still perform the structural checks.

The verifier checks that the output ISO is byte-for-byte identical to the clean ISO everywhere except the volume-size field and the four patched directory records, and that the patched files were written to the expected locations.

You can also check the whole file at once. The reference output has MD5 `71a7820b7c6d892edfb02b0f80a1c68f` (1,875,044,352 bytes); with the same inputs, yours should match:

```bash
md5sum "/path/to/Madoka (Translated).iso"
```

## Technical details

The clean redump ISO has its original directory records and mixed-case filenames preserved.

The rebuilt ISO produced during the investigation had a different directory structure, including uppercase ISO9660 names and `;1` version suffixes.

The script therefore does not recreate the ISO filesystem. It modifies only the directory records required to point to the four patched files appended to the image.

The resulting filesystem remains identical to the clean ISO except for the updated file extents, file sizes, and volume size.

Re-running the script with the same inputs reproduces the reference output byte-for-byte.


## AI assistance

This project was developed with assistance from **MiMo** (`mimo-v2.6-flash-free`) running through OpenCode.

The investigation, diagnosis, code, and documentation were AI-assisted. The resulting ISO was manually tested with PPSSPP on Linux and on an R36S handheld.

## Credits

**Carlitos** created the English translation patch and did the work that made this project possible.

Thank you for all your work in making Madoka Magica content accessible to people from different parts of the world.

## Disclaimer

This repository does not contain the game ISO or the English patch files.

You must obtain the game and patch files separately.

The script only modifies files provided locally by the user.

If you have any questions or run into problems with the script, feel free to [open an issue on GitHub](../../issues).
