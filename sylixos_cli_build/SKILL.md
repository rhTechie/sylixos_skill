---
name: sylixos_cli_build
description: Use when building SylixOS companion projects from Linux CLI. Always discover the real base, compatibility layer, license SDK, and BSP directories first, then persist all configurable build paths and platform variables into each project's config.mk with absolute paths. Keep command-line parameters only for items that cannot live in config.mk, such as -f <multi-platform.mk>.
---

# SylixOS CLI Build

Use this skill when a workspace contains a SylixOS base project plus companion projects such as a Linux compatibility layer, a license SDK, and a BSP.

Critical rule: all build paths must use absolute paths.

Critical rule: for every project handled with this skill, if a build variable can
be persisted in the project's `config.mk`, it must be written into `config.mk`
instead of relying on a command-line override.

This is a universal rule for all future projects built with this skill, not a
project-specific suggestion.

Keep command-line parameters only for values that cannot be stored in `config.mk`,
such as the `-f "$MULTI_MK"` build entry itself.

This applies to both:

- `config.mk` path variables
- command-line variable overrides passed to `make`

Do not use relative paths such as `../base_xxx`.
Do not add helper variables such as `CONFIG_MK_DIR` to derive paths.

## Discovery

Do not assume directory names are stable. Discover the current workspace layout every time.

Locate candidate projects first:

```sh
find . -maxdepth 4 -type f \( -name config.mk -o -name multi-platform.mk -o -name Makefile \) | sort
```

Typical identifiers:

- Base project: contains `libsylixos/SylixOS/mktemp/multi-platform.mk`
- Linux compatibility layer: directory name often contains `linux_compat`, usually has `src/` and `config.mk`
- License SDK: often under an `@...` package directory and contains `sdk/` plus `config.mk`
- BSP: has `SylixOS/`, `config.mk`, and a top-level `Makefile`

Useful checks:

```sh
find . -path '*libsylixos/SylixOS/mktemp/multi-platform.mk' -type f
find . -maxdepth 4 -type d \( -name '*linux_compat*' -o -name 'liblicense_sdk' -o -name 'bsp*' \) 2>/dev/null
```

After discovery, define shell variables with absolute paths, for example:

```sh
BASE=/abs/path/to/base_project
COMPAT=/abs/path/to/linux_compat_project
LICENSE=/abs/path/to/license_sdk_project
BSP=/abs/path/to/bsp_project
MULTI_MK="$BASE/libsylixos/SylixOS/mktemp/multi-platform.mk"
```

## Repository Hygiene Before Invasive Debugging

Before making risky multi-file changes in a component:

1. record the current code version for that component
2. if it is already a Git repository, note the branch, commit, or dirty state
3. if it is not a Git repository, initialize a local Git repository before invasive debugging so later diffs and rollback are manageable

Recommended minimum when no Git history exists:

```sh
git init
git add -A
git status --short
```

Create a baseline commit or tag only when the user permits it. Even without a commit, a fresh local repository still improves visibility of later edits.

## Platform Selection

Do not hardcode `PLATFORMS` from historical BSP settings. Choose it from the real base project layout.

Inspect base platform definitions:

```sh
sed -n '1,220p' "$BASE/platforms.mk"
```

Inspect actual generated base outputs:

```sh
find "$BASE/libsylixos/build" -maxdepth 2 -type d | sort
```

Rule:

- If the base project actually corresponds to `ARM64_GENERIC`, set `PLATFORMS := ARM64_GENERIC`.
- If the old BSP value is `ARM64_A55` but the available base layout/output is `ARM64_GENERIC`, change BSP `PLATFORMS` to `ARM64_GENERIC`.

For `ARM64_GENERIC`, the verified mapping is:

```text
TOOLCHAIN_PREFIX=aarch64-sylixos-elf-
CPU_TYPE=generic
FPU_TYPE=default
```

## Config Update Strategy

Preferred outcome: modify each companion project `config.mk` so the project can be
built later from its own directory with `make ... -f "$MULTI_MK"` and without
extra command-line variable overrides.

All path variables must be absolute paths.

If a variable can live in `config.mk`, do not leave it as a habitual command-line
override. Persist it in `config.mk` for later manual builds.

This applies to every follow-up project in the workspace as well:

- first fix `config.mk`
- then build with `-f "$MULTI_MK"`
- do not treat a command-line variable override as the finished solution if that variable could have been stored in `config.mk`

What to update:

- `SYLIXOS_BASE_PATH`
- `LINUX_COMPAT_LAYER_PATH` when present
- `LICENSE_SDK_PATH` when present
- `PLATFORMS`
- project-specific path variables referenced by local makefiles, for example `WORKSPACE_libdrv_linux_compat`

Rules:

- Replace IDE variables like `$(WORKSPACE_...)` with absolute paths.
- Do not use relative paths.
- Do not add `CONFIG_MK_DIR`, `realpath`, or other path-derivation variables into `config.mk`.
- Set `PLATFORMS` to the platform chosen from the real base layout.
- Keep existing `DEBUG_LEVEL`, `FPU_TYPE`, `AMP_CONFIG`, and other project options unless the build requires a change.

Example shape only:

```make
SYLIXOS_BASE_PATH := /abs/path/to/base_project
LINUX_COMPAT_LAYER_PATH = /abs/path/to/linux_compat_project
LICENSE_SDK_PATH = /abs/path/to/license_sdk_project
PLATFORMS := ARM64_GENERIC
```

The exact absolute path values must be taken from the current workspace, not copied from an old example.

## Build Entry

The multi-platform makefile is under the discovered base project:

```sh
MULTI_MK="$BASE/libsylixos/SylixOS/mktemp/multi-platform.mk"
```

The companion projects should be built with:

```sh
make all -f "$MULTI_MK"
```

Use a dry run first:

```sh
make -n all -f "$MULTI_MK"
```

Expected result: the recursive command should expand to the chosen `PLATFORM_NAME`, plus the toolchain, CPU type, and FPU type derived from `platforms.mk`.

## Local Makefile Behavior

Do not assume a companion project's local `Makefile` is a safe top-level entry
for plain `make` or `make clean`.

Verified SylixOS behavior:

- The outer multi-platform `all` and `clean` targets come from
  `libsylixos/SylixOS/mktemp/multi-platform.mk`.
- `multi-platform.mk` recurses with `PLATFORM_NAME=$(platform)`.
- The inner per-platform cleanup comes from
  `libsylixos/SylixOS/mktemp/end.mk`, which removes `$(TARGETS)`,
  `$(OBJPATH)`, and `$(DEPPATH)`.
- The real output root comes from `header.mk` as
  `build/$(PLATFORM_NAME)/$(Debug|Release)`.

Implication:

- If `PLATFORM_NAME` is empty, a local `Makefile` that directly includes
  `header.mk` and `end.mk` will usually resolve paths like `build//Release/...`.
- In that state, plain `make clean` may run, but it can clean the wrong path and
  leave `build/<PLATFORM>/Release/...` untouched.

Rule:

- Prefer `make all -f "$MULTI_MK"` and `make clean -f "$MULTI_MK"` for companion
  projects.
- Do not tell the user that plain `make clean` is correct unless the local
  `Makefile` explicitly delegates `all` and `clean` to `multi-platform.mk` when
  `PLATFORM_NAME` is empty.
- If you generate a standalone companion project for direct CLI use, either:
  1. document `make ... -f "$MULTI_MK"` as the required entry, or
  2. add a local wrapper `Makefile` target that forwards plain `make` and
     `make clean` into `multi-platform.mk`.

## Build Order

Build dependencies before BSP:

```sh
make -C "$LICENSE" all -f "$MULTI_MK"
make -C "$COMPAT" all -f "$MULTI_MK"
make -C "$BSP" all -f "$MULTI_MK"
```

Clean only when needed:

```sh
make -C "$LICENSE" clean -f "$MULTI_MK"
make -C "$COMPAT" clean -f "$MULTI_MK"
make -C "$BSP" clean -f "$MULTI_MK"
```

## BSP Board Selection

When the BSP project selects target boards through a checked-in top-level
`Makefile` list such as:

```make
BOARD_LIST :=
BOARD_LIST += lubancat
BOARD_LIST += adp
...
BOARD_LIST += tl3568_evm
```

and the user explicitly asks for one board package, prefer changing that
`BOARD_LIST` in the BSP `Makefile` to the requested board instead of using a
command-line override like `BOARD_LIST=tl3568_evm`.

Reason:

- in these projects, board package selection is a project-side build setting
- keeping it in the `Makefile` matches the user's normal manual build path
- it avoids leaving the real project state different from the command shown in
  the session

Use a command-line `BOARD_LIST=...` override only as a last-resort debugging
fallback or when the user explicitly asks not to modify the file.

## Command-Line Override Rule

If `config.mk` is not yet fixed, command-line overrides must also use absolute
paths only. This is fallback behavior, not the preferred steady state.

Do not keep passing variables on the command line once they can be written into
`config.mk`. The usual remaining command-line-only piece is the `-f "$MULTI_MK"`
selection.

For every project using this skill, the final handoff state must move all
persistable variables into `config.mk`. Do not leave the user with a build
procedure that still depends on command-line overrides for `SYLIXOS_BASE_PATH`,
`LINUX_COMPAT_LAYER_PATH`, `LICENSE_SDK_PATH`, `PLATFORMS`, or project-local
workspace path variables if those can be defined in `config.mk`.

Example shape:

```sh
make -C "$BSP" all -f "$MULTI_MK" \
  SYLIXOS_BASE_PATH="$BASE" \
  LINUX_COMPAT_LAYER_PATH="$COMPAT" \
  LICENSE_SDK_PATH="$LICENSE" \
  PLATFORMS=ARM64_GENERIC
```

Do not pass relative paths in command-line overrides.

## Validation

After editing `config.mk`, verify that the platform-aware entry works from each
project directory without extra variable parameters beyond the required
`-f "$MULTI_MK"` build entry:

```sh
make -C "$LICENSE" all -f "$MULTI_MK"
make -C "$LICENSE" clean -f "$MULTI_MK"
make -C "$COMPAT" all -f "$MULTI_MK"
make -C "$COMPAT" clean -f "$MULTI_MK"
make -C "$BSP" all -f "$MULTI_MK"
make -C "$BSP" clean -f "$MULTI_MK"
```

If you intentionally added a local wrapper `Makefile`, also verify:

```sh
make -C "$LICENSE" -n all
make -C "$LICENSE" -n clean
```

Confirm output directories match the chosen platform:

```sh
find "$LICENSE/build" -maxdepth 3 -type f | sort
find "$COMPAT/build" -maxdepth 3 -type f | sort
find "$BSP/build" -maxdepth 3 -type f | sort
```

Typical successful outputs include:

- License SDK archives under `build/<PLATFORM>/Release/`
- Compatibility layer `linuxcompat.ko` and `liblinuxcompat.a`
- BSP `*.elf`, `*.bin`, `*.dtb`, `*.siz`

When reporting BSP outputs, distinguish:

- outputs created by the current build
- pre-existing dirty or untracked files already present in the BSP tree

Do not describe a pre-existing untracked artifact as something newly added by
the current build unless the current build log proves it was generated in this
run.

## Common Failures

- `config.mk` still contains `$(WORKSPACE_...)`: replace it with absolute paths.
- `config.mk` uses relative paths: replace them with absolute paths.
- Command-line overrides use relative paths: replace them with absolute paths.
- Plain `make clean` left `build/<PLATFORM>/Release` behind: rerun through
  `make clean -f "$MULTI_MK"` or add a local wrapper `Makefile`.
- `PLATFORMS` does not match the real base layout: inspect `platforms.mk` and `libsylixos/build`.
- BSP cannot find compatibility layer or license SDK outputs: check absolute dependency paths and build order.
- `aarch64-sylixos-elf-gcc` not found: ensure the SylixOS toolchain is in `PATH`.
