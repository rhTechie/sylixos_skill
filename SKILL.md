---
name: sylixos
description: Master skill for SylixOS development workflow. Automatically determines whether to handle Linux-to-SylixOS porting analysis, build projects, or upload files to target boards based on the user's request.
---

# SylixOS Development Workflow

This is the master skill for SylixOS development. It automatically routes to the appropriate sub-skill based on the user's request.

## When to Use

Use this skill for any SylixOS development task, including:
- Porting Linux drivers or SDKs to SylixOS
- Summarizing verified SylixOS migration experience from an existing project
- Building/compiling SylixOS projects
- Uploading files to target boards
- Complete development workflow (build + upload)

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
- Uploads files via FTP (default: root/root)
- Reports upload results

**Location:** `sylixos_ftp_upload/SKILL.md`

### 3. `sylixos-driver-porting` - Linux Driver/SDK Porting Analysis

**Trigger conditions:**
- User asks to port Linux driver or SDK code to SylixOS
- User asks to summarize or review an existing SylixOS port
- User mentions "移植", "port", "适配", "兼容层", "driver migration", "SDK migration"
- User wants a reusable skill or checklist for later similar ports

**What it does:**
- Compares Linux original code with current SylixOS ported code
- Verifies migration conclusions against active source instead of trusting markdown notes
- Extracts reusable patterns across driver, HAL, SDK, sample, and build layers
- Distinguishes verified fixes from candidate-only ideas that are not yet landed

**Location:** `sylixos-driver-porting/SKILL.md`

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

### Porting / Migration Analysis
User says:
- "把 Linux 驱动移植到 SylixOS"
- "总结这个移植项目的经验"
- "分析当前代码里哪些移植结论已经落地"
- "生成一个后续可复用的 skill"

→ Use `sylixos-driver-porting` skill

### Build + Upload
User says:
- "编译并上传"
- "Build and deploy"
- "编译后上传到板卡"
- "Compile and upload to board"

→ Use both skills in sequence:
1. First use `sylixos_cli_build` to compile
2. If build succeeds, use `sylixos_ftp_upload` to upload

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

### Example 4: Fix and Deploy

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

### Example 5: Porting Summary

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

## Integration Notes

- These sub-skills are independent and can be used separately
- Build skill may modify libdrv_linux_compat if needed
- Upload skill assumes build artifacts exist
- Always verify build success before uploading
- Default FTP credentials: root/root (can be overridden)

## Quick Reference

| User Intent | Keywords | Sub-Skill(s) |
|-------------|----------|--------------|
| Porting | 移植, port, 适配, migration | sylixos-driver-porting |
| Compile | 编译, build, compile, make | sylixos_cli_build |
| Upload | 上传, upload, deploy, 部署 | sylixos_ftp_upload |
| Both | 编译并上传, build and upload | Both in sequence |
| Fix errors | 修复, fix, 错误, error | sylixos_cli_build |

## Tips

1. **Always check context**: Look for .reproject, config.mk, Makefile to identify project type
2. **Verify prerequisites**: Base project, compat layer, toolchain must be available
3. **Use absolute paths**: Never use relative paths in config.mk
4. **Report clearly**: Show build/upload progress and final results
5. **Handle errors gracefully**: If build fails, don't attempt upload
6. **Ask when unclear**: Better to confirm than assume wrong action
