---
name: sylixos_ftp_upload
description: Use when uploading SylixOS project files, apps, drivers, libraries, or rootfs content to a target board via FTP. Resolve board IP and upload targets from .reproject when available, otherwise accept explicit local and remote paths. Prefer the bundled ftp_sylixos_upload.py script so upload, remote chmod 755, and final sync are handled consistently.
---

# SylixOS FTP Upload

Use this skill when the user asks to upload or deploy SylixOS artifacts to a
board.

If the user also wants board-side runtime verification, hand off to
`sylixos_telnet_test` after upload succeeds.

## Use The Bundled Script

Default to the bundled script instead of rewriting FTP logic inline:

- Script: `sylixos_ftp_upload/scripts/ftp_sylixos_upload.py`
- Purpose:
  parse `.reproject`, resolve upload paths, upload files, apply remote
  `chmod 755`, and run one final remote `sync`

Use ad hoc Python only when you are patching or debugging the script itself.

## Required Inputs

Prefer `.reproject`-driven upload when the project has metadata.

Read from `.reproject`:

- `DeviceSetting/@DevName`: board IP
- `DeviceSetting/@WorkDir`: default board working directory
- `UploadPath/PairItem`: upload source and destination pairs
- `OutputSetting`: output alias mapping used by RealEvo-style projects

If `.reproject` is absent, fall back to an explicit deploy tuple:

- board IP
- local artifact path or directory
- remote destination path

Do not block on missing `.reproject` for one-off validation binaries.
When creating a new reusable SylixOS project, generate `.reproject` at project
creation time instead of normalizing permanent ad hoc upload flows.

## Default Behavior

Before upload:

- verify the board is reachable with `ping -c 3 <board_ip>`
- verify FTP is reachable with `nc -vz -w 3 <board_ip> 21`

Credentials:

- default username: `root`
- default password: `root`
- override them if the user provides other credentials

Permission handling:

- after every uploaded file, set remote permission to `755` by default
- apply the same default permission to newly created remote directories when the
  script creates them
- after all uploads finish, execute one remote `sync`

Do not silently skip the permission step. This fixes the known issue where
uploaded files arrive without execute permission.

## BSP Boot Image Replacement

When the uploaded artifact is a BSP boot image such as:

- `*.bin`
- `*.dtb`

and the user intends the board to boot from the new image, use this stricter flow:

1. identify the real boot directory, typically `/boot`
2. before overwrite, preserve or create a backup of the currently active boot image in `/boot`
3. upload the new image into the real boot directory
4. do not treat the replacement as complete until one remote `sync` has succeeded

The reboot itself belongs to the telnet validation step, but the upload skill
must surface that a post-upload reboot is mandatory for the image to take
effect. Hand the validation step a reconnect deadline of 60 seconds by default,
or 30 seconds when the user explicitly requests it. The default recovery
criterion is that at least one of ping or Telnet is available; enforce both only
when the board acceptance criteria require both. If neither channel recovers
within the deadline, stop all further uploads and reboots, preserve the backup
and logs, and request human or serial-console intervention.

## Command Patterns

Use the script from the workspace root or by absolute path.

Project upload via `.reproject`:

```bash
python3 sylixos_ftp_upload/scripts/ftp_sylixos_upload.py -P /path/to/project
```

Project upload with IP override:

```bash
python3 sylixos_ftp_upload/scripts/ftp_sylixos_upload.py -P /path/to/project -i 10.13.21.42
```

Single file upload:

```bash
python3 sylixos_ftp_upload/scripts/ftp_sylixos_upload.py -i 10.13.21.42 -f ./demo -t /apps/demo/demo
```

Upload to a remote directory while keeping the local file name:

```bash
python3 sylixos_ftp_upload/scripts/ftp_sylixos_upload.py -i 10.13.21.42 -f ./libfoo.so -d /lib/
```

Batch upload from a config file:

```bash
python3 sylixos_ftp_upload/scripts/ftp_sylixos_upload.py -i 10.13.21.42 -c upload_list.txt
```

Recursive rootfs upload:

```bash
python3 sylixos_ftp_upload/scripts/ftp_sylixos_upload.py -i 10.13.21.42 --rootfs /path/to/rootfs --rootfs-target /
```

Optional overrides:

- `-m 755`: set chmod mode explicitly; default is already `755`
- `--no-chmod`: disable remote chmod only when the user explicitly wants that
- `--no-sync`: disable final remote sync only when the user explicitly wants
  that

## Path Resolution Notes

The bundled script already handles the normal SylixOS cases:

- reads `.reproject` using `GB2312`
- resolves `$(WORKSPACE_<project>)`
- resolves `$(Output)`, `$(Debug)`, and `$(Release)`
- infers platform from `DeviceSetting/@Platform`, `config.mk`, and existing
  `build/<platform>/` directories
- supports both `build/<platform>/Release` style outputs and older project-local
  `Release/Debug` outputs

Do not reimplement this path resolution unless the script proves insufficient
for the current project shape.

## Error Handling

If reachability checks fail:

- stop and report the exact failing step
- do not attempt upload when `ping` fails or port `21` is closed

If upload partially fails:

- continue uploading remaining items when the script can continue safely
- report failed local paths and intended remote paths

If FTP authentication fails:

- report credential failure explicitly

If the board rejects chmod or sync:

- report that upload data transfer may have succeeded but post-upload board
  state is incomplete
- treat that as a meaningful warning or failure depending on the user goal

## Report Back

After upload, report:

- board IP
- upload mode used: project, single file, config batch, or rootfs
- number of upload items succeeded and failed
- actual file count transferred when available
- whether remote `chmod 755` was applied
- whether final remote `sync` succeeded
- final remote paths of the important artifacts

If the next step is runtime verification, pass the resolved remote path(s) to
`sylixos_telnet_test`.
