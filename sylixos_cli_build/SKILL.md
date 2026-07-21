---
name: sylixos_cli_build
description: Use when building SylixOS companion projects from Linux CLI. Discover the real base, compatibility layer, license SDK, and BSP directories first, persist the required paths and platform settings into the current project's config.mk, then clean and rebuild only the project affected by the user's source changes. Do not modify unrelated repositories or replace unrelated library artifacts.
---

# SylixOS CLI Build

Use this skill when a workspace contains a SylixOS base project plus companion projects such as a Linux compatibility layer, a license SDK, and a BSP.

Critical rule: all build paths used in commands must be absolute paths.

Default behavior is discovery, current-project configuration, and a clean
rebuild. Write required absolute paths and platform settings into the current
project's `config.mk`; do not leave them as temporary command-line overrides.
Do not rewrite Base, compatibility-layer, license, or unrelated repository files
just to make the build command convenient. Do not manually replace unrelated
`*.a`, `*.so`, or other BSP library artifacts. A dependency repository may be
modified only when it is the requested target or a reproducible build failure
requires debugging there, and the reason must be stated before editing.

Do not use relative paths such as `../base_xxx` in build commands. Do not add
helper variables such as `CONFIG_MK_DIR` to project files.

For BSP builds, never use `-j`, `--jobs`, or `--load-average`. Invoke the BSP
build with inherited `MAKEFLAGS` and `MFLAGS` cleared:

```sh
env -u MAKEFLAGS -u MFLAGS make ...
```

This restriction applies only to the BSP project. Base, compatibility-layer,
license SDK, and other projects may retain their default parallel configuration
or use `-j` when it improves build time and does not conflict with that
project's build behavior.

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
3. if it is not a Git repository, record that fact; do not initialize Git automatically

When the component is already a Git repository, record its current state:

```sh
git status --short
git diff --binary -- <touched-paths> > docs/patches/<date>-before.patch
```

When no Git history exists, do not run Git commands or initialize a repository
automatically. Record that fact, preserve pre-change copies of the touched files,
and use `diff -ruN` to generate the rollback patch. Create a repository,
baseline commit, or tag only when the user explicitly authorizes it.

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

- If the base project actually corresponds to `ARM64_GENERIC`, use `ARM64_GENERIC` for this build command.
- If the old BSP value is `ARM64_A55` but the available base layout/output is `ARM64_GENERIC`, report the mismatch and update the current project's `config.mk` to `ARM64_GENERIC` before building.

For `ARM64_GENERIC`, the verified mapping is:

```text
TOOLCHAIN_PREFIX=aarch64-sylixos-elf-
CPU_TYPE=generic
FPU_TYPE=default
```

## Config Update Strategy

Inspect `config.mk`, then update the current project's configuration with the
absolute paths and platform settings required for the requested build. This is
the normal build preparation step, not a temporary workaround. Do not propagate
the change into Base, compatibility, license, or unrelated repositories.

What to update:

- `SYLIXOS_BASE_PATH`
- `LINUX_COMPAT_LAYER_PATH` when present
- `LICENSE_SDK_PATH` when present
- `PLATFORMS`
- project-specific path variables referenced by local makefiles, for example `WORKSPACE_libdrv_linux_compat`

Rules:

- Replace IDE variables such as `$(WORKSPACE_...)` with absolute paths in the
  current project's `config.mk`.
- Set `PLATFORMS` to the platform selected from the real Base layout.
- Keep existing `DEBUG_LEVEL`, `FPU_TYPE`, `AMP_CONFIG`, and other project
  options unchanged unless the requested build requires a change.

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

For the BSP project, use no parallel options and clear inherited parallel flags:

```sh
env -u MAKEFLAGS -u MFLAGS make all -f "$MULTI_MK"
```

For Base or other non-BSP projects, use the project's normal build entry and
retain its default parallel configuration; `-j` may be used when appropriate.

Use a dry run first when the build entry or project scope is uncertain:

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

## Build Scope And Order

After source changes, always clean and rebuild the affected project. Do not use
an incremental build. Clean only generated outputs through the supported make
target; never delete source or user files.

Use this scope decision:

| Changed input | Required build |
| --- | --- |
| BSP source, BSP headers, or BSP build files | Clean and rebuild BSP only |
| Compatibility layer, license SDK, or application source | Clean and rebuild that project only |
| Base source, Base headers, Base ABI, Base configuration, or Base generated libraries | Clean and rebuild Base, then clean and rebuild affected downstream projects |
| Documentation only | No build |

For a BSP-only change, the normal command is:

```sh
env -u MAKEFLAGS -u MFLAGS make -C "$BSP" clean -f "$MULTI_MK"
env -u MAKEFLAGS -u MFLAGS make -C "$BSP" all -f "$MULTI_MK"
```

Do not rebuild `"$BASE"`, `"$COMPAT"`, or `"$LICENSE"` for a BSP-only change.
Only add those projects after confirming that their source, headers, ABI,
configuration, toolchain, or linked outputs changed, and tell the user why.

### Library Artifact Rule

Do not manually copy, substitute, or overwrite existing BSP libraries such as
`*.a`, `*.so`, or driver archives when their source and dependency inputs have
not changed. If a normal clean build regenerates an artifact because it belongs
to the affected project, keep that result and record its path; do not replace
unrelated library artifacts from another Base, branch, or historical build.
If a library itself is broken or its source/dependencies changed, report the
reason and include that library in the affected build scope.

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

and the user explicitly asks for one board package, inspect the selected board
and use a command-line override such as `BOARD_LIST=tl3568_evm` when needed.
Do not rewrite the BSP `Makefile` merely to perform a build.

State the override in the build record so the command remains reproducible.

## Command-Line Override Rule

Use command-line overrides only as a fallback when the current project's
`config.mk` cannot express the required setting or when the user explicitly
requests a temporary experiment. All path values must be absolute. The normal
handoff state must retain the required configuration in `config.mk`.

Example shape:

```sh
env -u MAKEFLAGS -u MFLAGS make -C "$BSP" all -f "$MULTI_MK" \
  SYLIXOS_BASE_PATH="$BASE" \
  LINUX_COMPAT_LAYER_PATH="$COMPAT" \
  LICENSE_SDK_PATH="$LICENSE" \
  PLATFORMS=ARM64_GENERIC
```

Do not pass relative paths in command-line overrides. Do not add parallel
options to BSP build commands. For non-BSP projects, follow the project or Base
build configuration for parallelism.

## Modification Record And Patch

For every non-trivial debugging or code-change task, record the pre-change state
before editing:

```sh
mkdir -p docs/patches
git status --short
git branch --show-current
git rev-parse HEAD 2>/dev/null || true
git diff --binary -- <touched-paths> > docs/patches/<date>-before.patch
```

After editing, save the corresponding patch without staging or committing:

```sh
git diff --binary -- <touched-paths> > docs/patches/<date>-after.patch
```

For an untracked touched file, also record it explicitly with
`git diff --no-index --binary /dev/null <file>`; that command returns status 1
when differences exist, which is expected. If the repository was already dirty,
keep the before and after patch files so pre-existing changes can be separated
from the current task. If the directory is not a Git repository, save the
pre-change files under `docs/patches/<date>-before/` and generate the final
patch with `diff -ruN <before-dir> <working-tree> >
docs/patches/<date>-after.patch` instead of initializing Git.

The process document must list each current modification precisely: file path,
function or symbol, line location, old behavior, new behavior, reason, expected
effect, exact build command, and compile/runtime result. Do not write vague
entries such as “adapted PCI driver”.

## Validation

Validate only the project included in the build-scope decision. For a BSP-only
change, use a clean single-threaded build:

```sh
env -u MAKEFLAGS -u MFLAGS make -C "$BSP" clean -f "$MULTI_MK"
env -u MAKEFLAGS -u MFLAGS make -C "$BSP" all -f "$MULTI_MK"
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

- `config.mk` still contains `$(WORKSPACE_...)`: replace it with absolute paths in the current project's `config.mk`.
- `config.mk` uses relative paths: replace them with absolute paths in the current project's `config.mk`.
- Command-line overrides use relative paths: replace them with absolute paths before running the command.
- Plain `make clean` left `build/<PLATFORM>/Release` behind: rerun through
  `make clean -f "$MULTI_MK"` or add a local wrapper `Makefile`.
- `PLATFORMS` does not match the real base layout: inspect `platforms.mk` and `libsylixos/build`.
- BSP cannot find compatibility layer or license SDK outputs: check absolute dependency paths and build order, then report whether a dependency rebuild is actually required.
- `aarch64-sylixos-elf-gcc` not found: ensure the SylixOS toolchain is in `PATH`.
