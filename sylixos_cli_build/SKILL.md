---
name: sylixos_cli_build
description: Use when building SylixOS companion projects from Linux CLI. Always discover the real base, compatibility layer, license SDK, and BSP directories first, then configure both config.mk and command-line overrides with absolute paths only.
---

# SylixOS CLI Build

Use this skill when a workspace contains a SylixOS base project plus companion projects such as a Linux compatibility layer, a license SDK, and a BSP.

Critical rule: all build paths must use absolute paths.

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

Preferred outcome: modify each companion project `config.mk` so the project can be built later with plain `make` from its own directory, without extra command-line variables.

All path variables must be absolute paths.

What to update:

- `SYLIXOS_BASE_PATH`
- `LINUX_COMPAT_LAYER_PATH` when present
- `LICENSE_SDK_PATH` when present
- `PLATFORMS`

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

## Command-Line Override Rule

If `config.mk` is not yet fixed, command-line overrides must also use absolute paths only.

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

After editing `config.mk`, verify that plain `make` works from each project directory without extra parameters:

```sh
make -C "$LICENSE" all -f "$MULTI_MK"
make -C "$COMPAT" all -f "$MULTI_MK"
make -C "$BSP" all -f "$MULTI_MK"
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

## Common Failures

- `config.mk` still contains `$(WORKSPACE_...)`: replace it with absolute paths.
- `config.mk` uses relative paths: replace them with absolute paths.
- Command-line overrides use relative paths: replace them with absolute paths.
- `PLATFORMS` does not match the real base layout: inspect `platforms.mk` and `libsylixos/build`.
- BSP cannot find compatibility layer or license SDK outputs: check absolute dependency paths and build order.
- `aarch64-sylixos-elf-gcc` not found: ensure the SylixOS toolchain is in `PATH`.
