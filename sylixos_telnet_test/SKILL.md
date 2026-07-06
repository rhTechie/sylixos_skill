---
name: sylixos_telnet_test
description: Use when verifying uploaded SylixOS artifacts on a target board via telnet. Resolve board IP and work directory from user input or .reproject, log in over telnet, fix executable permissions when needed, run the board-side test command, capture output, and report the result.
---

# SylixOS Telnet Test

Use this skill when the user asks to log in to a SylixOS board with telnet and
run or verify uploaded files on the target.

This skill is the normal post-deploy validation step after build and FTP upload.

## When to Use

- User says "telnet 登录板卡测试"
- User says "上传后运行测试"
- User mentions "板卡验证", "run on board", "test on hardware"
- User wants build + upload + test as one workflow

## Prerequisites

- `telnet` must be available in the current environment
- Board must be reachable on port `23`
- The target file must already exist on the board
- Credentials default to `root/root` unless the user specifies others

## Workflow

### 1. Resolve Board and Runtime Metadata

Prefer explicit user input first.

If the user does not provide all details, parse the project's `.reproject`:

- `DeviceSetting/@DevName`: board IP
- `DeviceSetting/@WorkDir`: board work directory
- `UploadPath/PairItem/@value`: uploaded remote paths

Read `.reproject` with `GB2312` encoding.

Use the remote upload path as the default run target when:

- there is exactly one uploaded application-like file
- or the destination path clearly points to `/apps/.../<name>`

Do not guess a runtime command for:

- `*.ko`
- `*.so`
- `*.a`
- projects with multiple possible entry points

In those cases, ask the user for the exact board-side test command.

If `.reproject` does not exist, use an explicit runtime tuple instead:

- board IP
- remote file path
- optional board work directory
- exact board-side command, if not obvious

For ad hoc validation tools, do not block on missing `.reproject`.

### 2. Verify Connectivity Before Login

Check basic reachability first:

```bash
ping -c 3 <board_ip>
nc -vz -w 3 <board_ip> 23
```

If port `23` is closed, report the failure and stop.

### 3. Open Interactive Telnet Session

Use a TTY session:

```bash
telnet <board_ip>
```

Wait for:

- `login:`
- `password:`

Then send credentials one step at a time. Do not send batched commands before
the shell prompt appears.

### 4. Verify Remote File State

After login:

- run `pwd`
- prefer `ll <dir>` over GNU-style `ls -l`
- confirm the uploaded file exists at the expected remote path

If the file should be directly executable, ensure it has execute permission.

Important SylixOS note:

- prefer `chmod 755 <file>`
- do not assume `chmod +x <file>` is supported

Also prefer checking one file or directory at a time. On some SylixOS shells,
batched commands are harder to read and easier to desynchronize.

### 5. Run the Test Command

Use the user-provided command when available.

Otherwise:

- `cd <WorkDir>` when `WorkDir` exists and helps readability
- execute the uploaded file by full path, for example:

```sh
/apps/timer_test/timer_test
```

Send commands one by one and poll output between steps. Do not blast multiple
commands into the telnet session unless prompt synchronization is already known
to be reliable.

If telnet interaction looks desynchronized:

- send a single command
- wait for output and prompt
- then send the next command

Do not trust a long pasted command sequence on first login.

### 6. Capture and Evaluate Result

For finite tests:

- wait until the shell prompt returns
- capture the command output
- report the executed command and the visible result

For long-running or interactive tests:

- use a bounded wait
- capture the last visible output
- report that the process did not naturally return before timeout

For long or noisy tests, prefer file-based capture:

- write the board-side output to a result file when the shell and harness support it
- use the file as the primary artifact for later review
- only rely on live console output for short or quiet commands

This reduces false conclusions caused by telnet noise, output truncation, or connection instability.

### 7. BSP Image Post-Upload Verification

When the uploaded artifact is a BSP boot image in `/boot`, do not stop after
connectivity and file checks.

Required sequence:

1. verify the expected boot image files exist in `/boot`
2. run `sync`
3. execute an explicit `reboot`
4. wait for network reconnection instead of assuming immediate availability
5. log back in and verify the boot banner or equivalent runtime version output
   shows the expected build time

Treat the image replacement as unverified until the post-reboot build time is
confirmed.

## Reporting Requirements

Always report:

- board IP used
- whether telnet login succeeded
- remote file path or command that was executed
- whether execute permission had to be fixed
- key board-side output
- whether the shell prompt returned normally
- for BSP image replacement, whether the post-reboot build time matched the expected image

## Common SylixOS Notes

- `ll` is often more reliable than GNU-style `ls -l`
- FTP-uploaded application files may land without execute permission
- octal `chmod` is more portable on SylixOS shells than symbolic `+x`
- local `file` output is only a hint; actual board execution result is the real validation
- for hardware-facing tests, capture pre/post board state when relevant
  for example `ifconfig`, driver status, or device-node presence
- for paired-board tests, remember that the peer board may also need reboot or cleanup before the next round

## Error Handling

### Connectivity Errors

- `ping` fails: report board unreachable
- port `23` closed: report telnet unavailable

### Authentication Errors

- login or password rejected: report auth failure and stop

### File Errors

- remote file missing: compare actual uploaded path with `.reproject`
- permission denied: run `chmod 755 <file>` and retry if appropriate
- command not found or loader error: capture the exact board message

### Ambiguous Test Target

If `.reproject` uploads multiple files and the runnable entry point is not
obvious, ask the user for the exact command instead of guessing.

If `.reproject` is missing and the remote path is explicit, that is not
ambiguous by itself. Execute the explicit file path after permission checks.

## Cleanup Discipline

After a major validation round:

1. stop or confirm exit of all board-side stress processes
2. if the next round materially changes strategy or binaries, prefer reboot
3. if the test uses a peer board, restore the peer too when its leftover traffic or state could pollute the next result

## Integration Order

For full workflow requests, use skills in this order:

1. `sylixos_cli_build`
2. `sylixos_ftp_upload`
3. `sylixos_telnet_test`
