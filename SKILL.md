---
name: sylixos
description: Master skill for SylixOS development workflow. Automatically determines whether to handle Linux-to-SylixOS driver porting analysis, build projects, upload files to target boards, run telnet-based board-side tests, debug networking behavior, or perform staged long-run validation based on the user's request.
---

# SylixOS Development Workflow

This is the master skill for SylixOS development. It automatically routes to the appropriate sub-skill based on the user's request.

## When to Use

Use this skill for any SylixOS development task, including:
- Porting Linux character-device drivers to SylixOS
- Summarizing verified SylixOS migration experience from an existing project
- Building/compiling SylixOS projects
- Uploading files to target boards
- Running tests on target boards over telnet
- Debugging long-running board-side issues with staged short-run, A/B, and soak validation
- Designing or debugging single-board dual-port Ethernet self-tests
- Explaining Linux vs SylixOS networking API differences encountered during debugging
- Complete development workflow (build + upload + test)

## Cross-Cutting Practice

Apply these habits across all SylixOS sub-skills:

1. Keep a process document while working, not only at the end.
2. Date each major investigation entry to day precision using the actual current date in `YYYY-MM-DD` format.
3. Prefer result files or log files over long live console streams for meaningful tests.
4. Record exact commands, CPU placement assumptions, board IPs, and result file paths.
5. Record the code version of every touched component before risky changes.
6. If the target code directory has no Git history, initialize a local Git repository before invasive multi-file debugging so diffs and rollbacks are manageable.
7. For driver porting, record the original Linux pattern, the chosen SylixOS pattern, wrapper/callback points inspected, and whether the result is source-review-only, compile-only, or board-verified.
8. When a timing problem has no clear next hypothesis, split the path with timestamp instrumentation and narrow it stage by stage; do this in the app, driver, or base layer as needed.
9. After a major validation round, restore both the DUT and the peer board to a clean state when state carry-over could contaminate the next result.
10. When replacing BSP boot images, treat upload as incomplete until the new image is copied into `/boot`, `sync` is issued on the board, the board is rebooted, and the post-reboot build time is verified.

## Sub-Skills

This master skill delegates to specialized sub-skills:

### 1. `sylixos_cli_build` - Build and Compilation

**Trigger conditions:**
- User asks to compile/build a project
- User mentions "编译", "构建", "build", "compile", "make"
- User wants to fix compilation errors
- User asks to rebuild after code changes

**What it does:**
- Discovers workspace layout (base, compat layer, license SDK, BSP)
- Updates config.mk with absolute paths
- Determines correct platform (ARM64_GENERIC, etc.)
- Executes build using multi-platform.mk
- Reports build results

**Location:** `sylixos_cli_build/SKILL.md`

### 2. `sylixos_ftp_upload` - FTP Upload to Board

**Trigger conditions:**
- User asks to upload to board/device
- User mentions "上传", "upload", "deploy", "部署"
- User specifies a board IP or mentions target device

**What it does:**
- Parses .reproject configuration file
- Extracts board IP and upload file list
- Verifies network connectivity
- Uploads files via the bundled FTP script (default: root/root)
- Applies remote `chmod 755` to uploaded files by default
- Runs one final remote `sync` after upload
- Reports upload results

**Location:** `sylixos_ftp_upload/SKILL.md`

### 3. `sylixos_telnet_test` - Telnet Login and Board Test

**Trigger conditions:**
- User asks to telnet to the board
- User mentions "测试", "test", "板卡验证", "run on board"
- User wants to execute uploaded files on hardware
- User asks for build + upload + test as one workflow

**What it does:**
- Resolves board IP, work directory, and uploaded remote paths
- Verifies port `23` connectivity before login
- Logs in with telnet using board credentials
- Fixes execute permissions when needed
- Runs the board-side test command and captures output
- Reports actual runtime result from the target

**Location:** `sylixos_telnet_test/SKILL.md`

### 4. `sylixos-driver-porting` - Linux Character-Device Driver Porting

**Trigger conditions:**
- User asks to port Linux character-device driver code to SylixOS
- User asks to summarize or review an existing SylixOS port
- User mentions "移植", "port", "适配", "兼容层", "character device", "interrupt", "driver migration"
- User wants a reusable skill or checklist for later similar ports
- User asks to keep or improve the process record for driver porting/debugging

**What it does:**
- Compares Linux original code with current SylixOS ported code
- Verifies migration conclusions against active source instead of trusting markdown notes
- Extracts reusable patterns for character-device registration and interrupt registration/callback adaptation
- Distinguishes verified fixes from candidate-only ideas that are not yet landed
- Maintains lightweight process documentation for multi-step porting, debugging, or board-validation work

**Location:** `sylixos-driver-porting/SKILL.md`

### 5. `sylixos-network` - Networking Debug And Validation

**Trigger conditions:**
- User mentions "单板双网口自测"
- User asks for "双网口互测" without an external peer PC
- User wants to prove physical Ethernet traversal instead of local loopback
- User asks to summarize Linux and SylixOS network interface differences
- User is confused by `AF_PACKET`, `sockaddr_ll`, `SO_BINDTODEVICE`, MTU, or loopback behavior
- User wants a reusable debugging checklist for future AI-assisted network bring-up

**What it does:**
- Distinguishes application connectivity from physical-path validation
- Summarizes practical Linux-vs-SylixOS differences in networking APIs and semantics
- Highlights local-IP short-circuit delivery behavior
- Explains raw Ethernet constraints, MTU limits, and interface-counter interpretation
- Provides a reusable debugging checklist for future AI sessions

**Location:** `sylixos-network/SKILL.md`

### 6. `sylixos-long-run-validation` - Long-Run Board Validation Method

**Trigger conditions:**
- User mentions “长时间测试”, “长期测试”, “soak”, “endurance”, “稳定性验证”
- User wants staged short-run then long-run verification
- User wants A/B validation before claiming an optimization
- User is debugging jitter/latency/load issues that need 30-minute or 1-hour confirmation

**What it does:**
- Separates test-model effects from real path effects
- Uses a staged ladder: quick reproduction -> A/B isolation -> 30-minute validation -> 1-hour confirmation
- Forces regression under the default real pressure mix before accepting a fix
- Emphasizes CPU placement, IRQ placement, and harness reliability as first-class hypotheses

**Location:** `sylixos-long-run-validation/SKILL.md`

## Decision Logic

When the user makes a request, determine which sub-skill(s) to use:

### Build Only
User says:
- "编译 xxx 项目"
- "Build the driver"
- "Fix compilation errors"
- "重新编译"

→ Use `sylixos_cli_build` skill

### Upload Only
User says:
- "上传到板卡"
- "Upload to board"
- "Deploy the driver"
- "上传 xxx 项目"

→ Use `sylixos_ftp_upload` skill

### Test Only
User says:
- "telnet 登录板卡测试"
- "Run the uploaded app on board"
- "执行板卡上的测试程序"
- "上传后测试"

→ Use `sylixos_telnet_test` skill

### Porting / Migration Analysis
User says:
- "把 Linux 驱动移植到 SylixOS"
- "把 Linux 字符设备驱动移植到 SylixOS"
- "总结这个移植项目的经验"
- "分析当前代码里哪些移植结论已经落地"
- "记录这次驱动移植和板端验证过程"
- "生成一个后续可复用的 skill"

→ Use `sylixos-driver-porting` skill

### Networking Validation / API Differences
User says:
- "做一个单板双网口自测"
- "不使用外部陪测机验证物理链路"
- "双口短接后怎么证明不是 lo0"
- "raw Ethernet 自测怎么做"
- "总结 Linux 和 SylixOS 网络接口差异"
- "为什么 AF_PACKET 在 SylixOS 上行为不一样"
- "整理一个后续 AI 调试网络时可复用的 skill"

→ Use `sylixos-network` skill

### Long-Run Validation / Soak Debugging
User says:
- "做长期测试问题排查"
- "先短测再长测验证"
- "做 30 分钟或 1 小时确认"
- "这类抖动问题怎么系统验证"

→ Use `sylixos-long-run-validation` skill

### Build + Upload
User says:
- "编译并上传"
- "Build and deploy"
- "编译后上传到板卡"
- "Compile and upload to board"

→ Use both skills in sequence:
1. First use `sylixos_cli_build` to compile
2. If build succeeds, use `sylixos_ftp_upload` to upload

### Build + Upload + Test
User says:
- "编译上传并测试"
- "Build, deploy, and test on board"
- "上传后通过 telnet 跑测试"
- "Compile, upload, then run on hardware"

→ Use three skills in sequence:
1. First use `sylixos_cli_build` to compile
2. If build succeeds, use `sylixos_ftp_upload` to upload
3. If upload succeeds, use `sylixos_telnet_test` to run the board-side test

### Ambiguous Cases

If unclear, ask the user:
- "需要编译吗？" (Need to build?)
- "需要上传到板卡吗？" (Need to upload to board?)

## Workflow Examples

### Example 1: Build Only

```
User: "编译 lynxi_driver_hm100"

Action:
1. Apply sylixos_cli_build skill
2. Discover workspace layout
3. Update config.mk
4. Execute make with multi-platform.mk
5. Report build results
```

### Example 2: Upload Only

```
User: "上传 lynxi_driver_hm100 到板卡"

Action:
1. Apply sylixos_ftp_upload skill
2. Parse .reproject file
3. Verify network connectivity
4. Upload files via FTP
5. Report upload results
```

### Example 3: Build + Upload

```
User: "编译 lynxi_driver_hm100 并上传到板卡"

Action:
1. Apply sylixos_cli_build skill
   - Build the project
   - Check for errors
2. If build succeeds:
   - Apply sylixos_ftp_upload skill
   - Upload to board
3. Report complete workflow results
```

### Example 4: Build + Upload + Test

```
User: "编译 timer_test，上传到板卡并通过 telnet 测试"

Action:
1. Apply sylixos_cli_build skill
   - Discover the real base project
   - Update config.mk with absolute paths
   - Build with multi-platform.mk
2. If build succeeds:
   - Apply sylixos_ftp_upload skill
   - Parse .reproject
   - Upload the built file to the board
3. If upload succeeds:
   - Apply sylixos_telnet_test skill
   - Log in over telnet
   - Verify remote file permissions
   - Execute the board-side test command
4. Report build, upload, and runtime test results
```

### Example 5: Fix and Deploy

```
User: "修复编译错误并重新编译上传"

Action:
1. Analyze compilation errors
2. Fix the errors
3. Apply sylixos_cli_build skill to rebuild
4. If build succeeds:
   - Apply sylixos_ftp_upload skill
   - Upload to board
```

### Example 6: Porting Summary

```
User: "结合代码和移植文档，总结一个 SylixOS 驱动移植 skill"

Action:
1. Apply sylixos-driver-porting skill
2. Compare Linux original tree and SylixOS ported tree
3. Verify each markdown conclusion against active code
4. Extract reusable patterns and unresolved risks
5. Write the skill file
```

## Common Project Types

### Driver Projects
- Usually contain: `lyn_drv.mk`, `config.mk`, `.reproject`
- Build output: `*.ko` (kernel modules), `*.so` (libraries)
- Upload targets: `/lib/modules/drivers/`, `/lib/`

### Ported Driver Stacks
- Usually contain both Linux-origin source layout and SylixOS-native build files
- Often include driver layer, HAL wrappers, SDK or middleware, and sample apps
- Need evidence-based review because markdown migration notes may be stale or wrong

### Application Projects
- Usually contain: `config.mk`, `.reproject`, `src/` directory
- Build output: executables, `*.so` libraries
- Upload targets: `/apps/`, `/usr/bin/`
- For newly created reusable app projects, create `.reproject` together with the
  build files so later FTP upload and telnet validation can reuse stable board
  metadata

### BSP Projects
- Usually contain: `SylixOS/` directory, `config.mk`
- Build output: `*.elf`, `*.bin`, `*.dtb`
- Upload targets: boot partition or `/boot/`

## Error Handling

### Build Errors
- If compilation fails, analyze errors and suggest fixes
- Common issues: missing headers, wrong paths, type mismatches
- May need to update libdrv_linux_compat if compatibility layer issues

### Upload Errors
- Network unreachable: Check board IP and network
- FTP connection failed: Verify FTP service is running
- Permission denied: Check FTP credentials
- File not found: Ensure build completed successfully
- Remote chmod/sync failed: Treat upload as incomplete until board-side state is confirmed

### Test Errors
- Telnet port closed: Verify board telnet service is enabled
- Login rejected: Verify telnet credentials
- Uploaded file is not executable: Set octal mode such as `chmod 755`
- Runtime command ambiguous: Require an explicit board-side test command
- Program hangs or never returns: Report timeout and last visible output

## Integration Notes

- These sub-skills are independent and can be used separately
- Build skill may modify libdrv_linux_compat if needed
- Upload skill assumes build artifacts exist
- For newly scaffolded reusable projects, prefer generating `.reproject` during
  creation instead of relying on ad hoc upload arguments forever
- Upload skill now prefers `sylixos_ftp_upload/scripts/ftp_sylixos_upload.py`
  so path resolution, remote `chmod 755`, and final `sync` are handled
  consistently
- Test skill assumes the artifact is already on the board
- Always verify build success before uploading
- Always verify upload success before telnet testing
- Default FTP credentials: root/root (can be overridden)
- Default telnet credentials: root/root (can be overridden)

## Quick Reference

| User Intent | Keywords | Sub-Skill(s) |
|-------------|----------|--------------|
| Porting | 移植, port, 适配, migration | sylixos-driver-porting |
| Compile | 编译, build, compile, make | sylixos_cli_build |
| Upload | 上传, upload, deploy, 部署 | sylixos_ftp_upload |
| Test on board | 测试, test, telnet, 板卡验证 | sylixos_telnet_test |
| Build + Upload | 编译并上传, build and upload | Build then upload |
| Build + Upload + Test | 编译上传并测试, deploy and test | Build then upload then test |
| Fix errors | 修复, fix, 错误, error | sylixos_cli_build |
| Network validation | 网络, 双网口, AF_PACKET, MTU | sylixos-network |
| Long-run validation | 长时间, 抖动, soak, endurance | sylixos-long-run-validation |

## Tips

1. **Always check context**: Look for .reproject, config.mk, Makefile to identify project type
2. **Verify prerequisites**: Base project, compat layer, toolchain must be available
3. **Use absolute paths**: Never use relative paths in config.mk
4. **Prefer board truth**: Use actual telnet runtime output as the final validation
5. **Report clearly**: Show build/upload/test progress and final results
6. **Handle errors gracefully**: If build fails, don't attempt upload; if upload fails, don't attempt test
7. **Ask when unclear**: Better to confirm than assume wrong action
