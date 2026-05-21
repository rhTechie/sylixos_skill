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

## Workflow

### 1. Locate and Parse .reproject File

The `.reproject` file is an XML configuration file (GB2312 encoding) that contains:
- `DeviceSetting/@DevName`: Target board IP address
- `UploadPath/PairItem`: List of files to upload with source and destination paths

Example structure:
```xml
<SylixOSSetting>
    <UploadPath>
        <PairItem key="$(WORKSPACE_project)/build/ARM64_GENERIC/Release/file.ko" 
                  value="/lib/modules/drivers/file.ko"/>
    </UploadPath>
    <DeviceSetting DevName="10.13.21.42" Platform="ARM64_GENERIC"/>
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

# Get upload paths
upload_paths = []
for pair in root.findall('.//UploadPath/PairItem'):
    src = pair.get('key')
    dst = pair.get('value')
    
    # Replace workspace variable with actual path
    # Pattern: $(WORKSPACE_projectname) -> /actual/path/to/project
    src = src.replace('$(WORKSPACE_projectname)', '/actual/project/path')
    
    upload_paths.append((src, dst))
```

**Important**: The `key` attribute contains workspace variables like `$(WORKSPACE_projectname)` that must be replaced with the actual absolute path to the project directory.

### 3. Verify Network Connectivity

Before uploading, verify the board is reachable:

```bash
ping -c 3 <board_ip>
```

If ping fails, report the error to the user and do not proceed.

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
    
    # Get project name from path
    project_name = os.path.basename(project_path)
    
    # Parse upload paths
    upload_paths = []
    for pair in root.findall('.//UploadPath/PairItem'):
        src = pair.get('key')
        dst = pair.get('value')
        
        # Replace workspace variable
        src = src.replace(f'$(WORKSPACE_{project_name})', project_path)
        
        if os.path.exists(src):
            upload_paths.append((src, dst))
    
    return board_ip, upload_paths

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
    board_ip, upload_paths = parse_reproject(project_path)
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
8. **Timeout settings** - Set reasonable timeout (10s) for FTP connections
9. **Error recovery** - If one file fails, continue with remaining files

## Security Notes

- Default credentials (`root`/`root`) are common for development boards
- For production systems, always use secure credentials
- Consider using SFTP instead of FTP for production environments
- FTP transmits credentials in plain text - use only on trusted networks
