---
name: sylixos_ftp_upload
description: Use when uploading SylixOS project files to target board via FTP. Automatically parses .reproject configuration file to get board IP, upload file list and target paths, then uploads all files via FTP.
---

# SylixOS FTP Upload

Use this skill when the user asks to upload a SylixOS project to a target board or device.

This skill automates the process of:
1. Parsing the `.reproject` configuration file
2. Extracting board IP, file list, and target paths
3. Verifying network connectivity
4. Uploading files via FTP

If the user also wants runtime verification on the board, hand off to
`sylixos_telnet_test` after upload succeeds.

## When to Use

- User says "上传到板卡" / "upload to board"
- User mentions uploading a specific project (e.g., "上传 lynxi_driver_hm100")
- User asks to deploy files to the target device
- After successful compilation, if user wants to test on hardware

## Prerequisites

- Project must have a `.reproject` file in its root directory
- Target board must be network accessible
- FTP service must be running on the target board

If `.reproject` does not exist, do not stop immediately. Fall back to an
explicit deploy tuple:

- board IP
- local artifact path(s)
- remote destination path

This fallback is important for:

- ad hoc test applications
- newly created throwaway utilities
- single-file validation tools created during debugging

But when the task is to create or scaffold a new long-lived SylixOS project,
generate a matching `.reproject` at project creation time instead of leaving the
project without upload metadata.

## Workflow

### 1. Locate and Parse .reproject File

The `.reproject` file is an XML configuration file (GB2312 encoding) that contains:
- `DeviceSetting/@DevName`: Target board IP address
- `DeviceSetting/@WorkDir`: default board-side working directory
- `UploadPath/PairItem`: List of files to upload with source and destination paths
- `OutputSetting`: mapping for `$(Output)`, `Debug`, and `Release`

Example structure:
```xml
<SylixOSSetting>
    <OutputSetting>
        <OutputPath Name="Output" Path="Release:Debug" TreeNode="Output"/>
        <OutputPath Name="Debug" Path="Debug" TreeNode="Debug"/>
        <OutputPath Name="Release" Path="Release" TreeNode="Release"/>
    </OutputSetting>
    <UploadPath>
        <PairItem key="$(WORKSPACE_project)/$(Output)/strip/project_name"
                  value="/apps/project_name/project_name"/>
    </UploadPath>
    <DeviceSetting Auto="false" DevName="10.13.21.42" Platform="ARM64_GENERIC"
                   WorkDir="/apps/project_name"/>
</SylixOSSetting>
```

### 2. Parse Configuration

Use Python to parse the XML file:

```python
import xml.etree.ElementTree as ET
import os

# Read with GB2312 encoding
with open('.reproject', 'r', encoding='gb2312') as f:
    content = f.read()

root = ET.fromstring(content)

# Get board IP
device_setting = root.find('.//DeviceSetting')
board_ip = device_setting.get('DevName')
work_dir = device_setting.get('WorkDir', '')

# Resolve output aliases used by RealEvo-style app projects
debug_level = 'release'
output_alias = 'Release'
if debug_level == 'debug':
    output_alias = 'Debug'

# Get upload paths
upload_paths = []
for pair in root.findall('.//UploadPath/PairItem'):
    src = pair.get('key')
    dst = pair.get('value')
    
    # Replace workspace variable with actual path
    # Pattern: $(WORKSPACE_projectname) -> /actual/path/to/project
    src = src.replace('$(WORKSPACE_projectname)', '/actual/project/path')
    src = src.replace('$(Output)', f'build/ARM64_GENERIC/{output_alias}')
    
    upload_paths.append((src, dst))
```

**Important**:

- The `key` attribute commonly contains workspace variables like
  `$(WORKSPACE_projectname)` that must be replaced with the actual absolute path
  to the project directory.
- For app projects, `$(Output)` is usually a logical alias that must be resolved
  to the real build path such as `build/ARM64_GENERIC/Release` or
  `build/ARM64_GENERIC/Debug`.

### 1b. Generate `.reproject` For New Projects

When creating a new project intended for repeated board upload and testing, do
not leave `.reproject` absent. Generate one immediately.

For a standalone application project, use this template shape:

```xml
<?xml version="1.0" encoding="GB2312" standalone="no"?>
<SylixOSSetting>
    <BaseSetting Profile="standard" ProjectType="SylixOSAppProject"
                 RealEvoVer="6.5.0 Ultimate"
                 TlsVersion="SylixOS_COM_LTS_3.6.5"/>
    <OutputSetting>
        <OutputPath Name="Output" Path="Release:Debug" TreeNode="Output"/>
        <OutputPath Name="Debug" Path="Debug" TreeNode="Debug"/>
        <OutputPath Name="Release" Path="Release" TreeNode="Release"/>
    </OutputSetting>
    <BuildSetting CoustomCfgMakefile="false"
                  NeedReBuild="false"
                  NotScanSourceFile="false"/>
    <DeviceSetting Auto="false"
                   DevName="10.13.21.42"
                   Platform="ARM64_GENERIC"
                   WorkDir="/apps/<project_name>"/>
    <UploadPath>
        <PairItem key="$(WORKSPACE_<project_name>)/$(Output)/strip/<project_name>"
                  value="/apps/<project_name>/<project_name>"/>
    </UploadPath>
    <ExtDevNames/>
</SylixOSSetting>
```

Template rules:

- `ProjectType`:
  `SylixOSAppProject` for executables, `SylixOSSlibProject` for libraries, BSP
  project type for BSPs.
- `DeviceSetting/@DevName`:
  reuse the board IP already used in the workspace when one is obvious;
  otherwise leave the agreed default board IP.
- `DeviceSetting/@Platform`:
  set it when the workspace platform is known, for example `ARM64_GENERIC`.
- `DeviceSetting/@WorkDir`:
  for single executable apps, prefer `/apps/<project_name>`.
- `UploadPath/PairItem/@key`:
  for single app executables, prefer
  `$(WORKSPACE_<project_name>)/$(Output)/strip/<project_name>`.
- `UploadPath/PairItem/@value`:
  for single app executables, prefer `/apps/<project_name>/<project_name>`.
- `OutputSetting`:
  keep the standard `Output/Debug/Release` trio so IDE and upload tooling stay
  consistent.

If the project is a one-off throwaway validation utility, fallback upload
without `.reproject` is still acceptable, but that is the exception, not the
preferred project shape.

### 1a. Fallback When `.reproject` Is Missing

If the project has no `.reproject`, use this generic fallback instead of
blocking:

1. Ask for or infer the board IP from the user request.
2. Ask for or choose an explicit remote destination directory.
3. Upload the built artifact directly by absolute path.

Recommended default behavior:

- prefer a user-provided remote directory
- otherwise reuse the directory the user already uses on that board
- otherwise choose a simple writable app path such as `/media/sdcard5/` or
  `/apps/<toolname>/` depending on the board workflow

Do not invent a fake `.reproject` for an already existing throwaway binary when
the user only wants one immediate upload. Generate `.reproject` when creating or
formalizing a reusable project.

### 3. Verify Network Connectivity

Before uploading, verify the board is reachable:

```bash
ping -c 3 <board_ip>
```

If ping fails, report the error to the user and do not proceed.

Also verify FTP service explicitly:

```bash
nc -vz -w 3 <board_ip> 21
```

If port `21` is closed, stop and report FTP unavailable.

### 4. Get FTP Credentials

**Default credentials for SylixOS boards**:
- Username: `root`
- Password: `root`

If the user has specified different credentials, use those instead.

### 5. Upload Files via FTP

Use Python's `ftplib` to upload files:

```python
from ftplib import FTP
import os

def ensure_dir(ftp, path):
    """Ensure directory exists on FTP server, create if needed"""
    dirs = []
    while path and path != '/':
        dirs.append(path)
        path = os.path.dirname(path)
    
    dirs.reverse()
    for d in dirs:
        try:
            ftp.cwd(d)
        except:
            try:
                parent = os.path.dirname(d)
                if parent and parent != '/':
                    ftp.cwd(parent)
                ftp.mkd(d)
            except:
                pass

# Connect to FTP
ftp = FTP()
ftp.connect(board_ip, 21, timeout=10)
ftp.login('root', 'root')

# Upload each file
for src, dst in upload_paths:
    if os.path.isfile(src):
        # Upload single file
        dst_dir = os.path.dirname(dst)
        ensure_dir(ftp, dst_dir)
        ftp.cwd(dst_dir)
        
        with open(src, 'rb') as f:
            ftp.storbinary(f'STOR {os.path.basename(dst)}', f)
        
    elif os.path.isdir(src):
        # Upload all files in directory
        ensure_dir(ftp, dst)
        ftp.cwd(dst)
        
        for filename in os.listdir(src):
            src_file = os.path.join(src, filename)
            if os.path.isfile(src_file):
                with open(src_file, 'rb') as f:
                    ftp.storbinary(f'STOR {filename}', f)

ftp.quit()
```

When debugging board-side runtime issues, consider uploading both:

- stripped binary for normal execution
- unstripped binary with a distinct suffix for later investigation

This is especially useful for small test applications where the size overhead is
acceptable.

### 6. Report Results

After upload completes, report to the user:
- Number of files uploaded successfully
- Number of files failed (if any)
- Total data transferred
- File locations on the board

Example output:
```
=== 上传完成 ===
成功: 11/11
失败: 0/11

文件位置:
- 驱动: /lib/modules/drivers/lyn_drv.ko
- 库: /lib/liblyn_*.so
- 测试工具: /apps/lynxi_driver_test/

总数据量: 约 3.5MB
```

## Error Handling

### Network Errors
- If ping fails: Report "无法连接到板卡 IP: <ip>"
- If FTP connection fails: Report "FTP 连接失败，请检查板卡 FTP 服务是否运行"

### File Errors
- If source file doesn't exist: Skip and report in summary
- If FTP upload fails: Catch exception, report which file failed, continue with remaining files

If `.reproject` is absent and the user gave only a local binary path:

- upload that one file directly
- do not fail merely because project metadata is missing

### Permission Errors
- If FTP credentials are wrong: Report "FTP 认证失败，请检查用户名和密码"
- If no write permission: Report "目标目录无写入权限: <path>"

## Common File Types

SylixOS projects typically upload:
- **Kernel modules**: `*.ko` files → `/lib/modules/drivers/`
- **Shared libraries**: `*.so` files → `/lib/`
- **Static libraries**: `*.a` files → `/lib/`
- **Executables**: Test tools and utilities → `/apps/` or `/usr/bin/`
- **Configuration files**: `*.conf`, `*.cfg` → `/etc/`

## Platform-Specific Notes

### ARM64_GENERIC Platform
- Build output directory: `build/ARM64_GENERIC/Release/`
- Stripped binaries: `build/ARM64_GENERIC/Release/strip/`
- Prefer uploading stripped versions for production

### Directory Structure
- Drivers: `/lib/modules/drivers/`
- Libraries: `/lib/`
- Applications: `/apps/` or `/usr/bin/`
- Test tools: `/apps/<project>_test/`

## Complete Example

```python
#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from ftplib import FTP
import os
import sys

def parse_reproject(project_path):
    """Parse .reproject file and return board IP and upload list"""
    reproject_file = os.path.join(project_path, '.reproject')
    
    with open(reproject_file, 'r', encoding='gb2312') as f:
        content = f.read()
    
    root = ET.fromstring(content)
    
    # Get board IP
    device_setting = root.find('.//DeviceSetting')
    board_ip = device_setting.get('DevName')
    work_dir = device_setting.get('WorkDir')
    platform = device_setting.get('Platform') or 'ARM64_GENERIC'
    
    debug_level = 'release'
    config_mk = os.path.join(project_path, 'config.mk')
    if os.path.exists(config_mk):
        with open(config_mk, 'r', encoding='utf-8', errors='ignore') as f:
            config_text = f.read().lower()
        if 'debug_level := debug' in config_text or 'debug_level = debug' in config_text:
            debug_level = 'debug'
    
    output_alias = f'build/{platform}/Release'
    if debug_level == 'debug':
        output_alias = f'build/{platform}/Debug'
    
    # Get project name from path
    project_name = os.path.basename(project_path)
    
    # Parse upload paths
    upload_paths = []
    for pair in root.findall('.//UploadPath/PairItem'):
        src = pair.get('key')
        dst = pair.get('value')
        
        # Replace workspace variable
        src = src.replace(f'$(WORKSPACE_{project_name})', project_path)
        src = src.replace('$(Output)', output_alias)
        
        if os.path.exists(src):
            upload_paths.append((src, dst))
    
    return board_ip, work_dir, upload_paths

def upload_to_board(board_ip, upload_paths, username='root', password='root'):
    """Upload files to board via FTP"""
    ftp = FTP()
    ftp.connect(board_ip, 21, timeout=10)
    ftp.login(username, password)
    
    success = 0
    failed = 0
    
    for src, dst in upload_paths:
        try:
            if os.path.isfile(src):
                dst_dir = os.path.dirname(dst)
                ensure_dir(ftp, dst_dir)
                ftp.cwd(dst_dir)
                
                with open(src, 'rb') as f:
                    ftp.storbinary(f'STOR {os.path.basename(dst)}', f)
                
                success += 1
            elif os.path.isdir(src):
                ensure_dir(ftp, dst)
                ftp.cwd(dst)
                
                for filename in os.listdir(src):
                    src_file = os.path.join(src, filename)
                    if os.path.isfile(src_file):
                        with open(src_file, 'rb') as f:
                            ftp.storbinary(f'STOR {filename}', f)
                
                success += 1
        except Exception as e:
            print(f"Failed to upload {src}: {e}")
            failed += 1
    
    ftp.quit()
    return success, failed

# Usage
if __name__ == '__main__':
    project_path = '/path/to/project'
    board_ip, work_dir, upload_paths = parse_reproject(project_path)
    success, failed = upload_to_board(board_ip, upload_paths)
    print(f"Success: {success}, Failed: {failed}")
```

## Tips

1. **Always verify network connectivity first** - Use ping before attempting FTP
2. **Check file existence** - Skip non-existent files and report them
3. **Create directories automatically** - Use `ensure_dir()` to create target directories
4. **Handle encoding correctly** - `.reproject` files use GB2312 encoding
5. **Report progress** - Show which file is being uploaded for better user experience
6. **Use binary mode** - Always use `storbinary()` for uploading files
7. **Handle both files and directories** - Some upload items are directories containing multiple files
8. **Resolve `$(Output)` correctly** - It usually maps to `build/<PLATFORM>/Release` or `build/<PLATFORM>/Debug`
9. **Create `.reproject` for new reusable projects** - Especially standalone app test tools that will be rebuilt and re-uploaded later
8. **Timeout settings** - Set reasonable timeout (10s) for FTP connections
9. **Error recovery** - If one file fails, continue with remaining files

## Security Notes

- Default credentials (`root`/`root`) are common for development boards
- For production systems, always use secure credentials
- Consider using SFTP instead of FTP for production environments
- FTP transmits credentials in plain text - use only on trusted networks
