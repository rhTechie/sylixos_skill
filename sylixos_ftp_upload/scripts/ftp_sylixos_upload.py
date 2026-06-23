#!/usr/bin/env python3
"""
SylixOS FTP upload tool.
"""

import argparse
import os
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from ftplib import FTP


def normalize_remote_path(path):
    """Normalize a remote POSIX path."""
    normalized = (path or "/").replace("\\", "/")
    normalized = posixpath.normpath(normalized)
    return "/" if normalized == "." else normalized


def join_remote_path(base, *parts):
    """Join remote POSIX path segments."""
    current = normalize_remote_path(base)
    for part in parts:
        current = posixpath.join(current, str(part).replace("\\", "/"))
    return normalize_remote_path(current)


def split_remote_path(path):
    """Split a remote file path into directory and basename."""
    normalized = normalize_remote_path(path)
    remote_dir = posixpath.dirname(normalized)
    remote_file = posixpath.basename(normalized)
    return ("/" if remote_dir == "." else remote_dir), remote_file


def format_size(size):
    """Format file size for logs."""
    if size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size / 1024 / 1024:.1f}MB"


def validate_permission_mode(mode):
    """Validate chmod mode."""
    normalized = mode.strip()
    if not re.fullmatch(r"[0-7]{3,4}", normalized):
        raise argparse.ArgumentTypeError(
            "permission mode must be 3 or 4 octal digits, e.g. 755 or 0755"
        )
    return normalized[-3:]


def send_ftp_command(ftp, commands):
    """Try FTP commands in order until one succeeds."""
    last_error = None
    for command in commands:
        try:
            return command, ftp.sendcmd(command)
        except Exception as exc:
            last_error = exc

    if last_error is None:
        raise RuntimeError("no FTP command to execute")
    raise last_error


def set_remote_permissions(ftp, remote_path, mode):
    """Set remote permissions after upload."""
    normalized_path = normalize_remote_path(remote_path)
    send_ftp_command(
        ftp,
        [
            f"SITE CHMOD {mode} {normalized_path}",
            f"SITE chmod {mode} {normalized_path}",
        ],
    )
    print(f"  chmod applied: {normalized_path} -> {mode}")


def sync_remote(ftp):
    """Flush uploaded data on the remote side."""
    command, response = send_ftp_command(
        ftp,
        [
            "SITE SYNC",
            "SITE sync",
            "SYNC",
            "sync",
        ],
    )
    print(f"remote sync: {command} -> {response}")


def ensure_dir(ftp, path, chmod_mode=None):
    """Ensure a remote directory exists."""
    path = normalize_remote_path(path)
    dirs = []
    while path and path != "/":
        dirs.append(path)
        path = posixpath.dirname(path)

    dirs.reverse()
    for directory in dirs:
        try:
            ftp.cwd(directory)
        except Exception:
            parent = posixpath.dirname(directory)
            if parent and parent != "/":
                ftp.cwd(parent)
            ftp.mkd(directory)
            print(f"  created directory: {directory}")
            if chmod_mode:
                set_remote_permissions(ftp, directory, chmod_mode)


def upload_file(ftp, local_file, remote_path, chmod_mode=None):
    """Upload one file."""
    remote_dir, remote_file = split_remote_path(remote_path)
    remote_path = join_remote_path(remote_dir, remote_file)

    ensure_dir(ftp, remote_dir, chmod_mode=chmod_mode)
    ftp.cwd(remote_dir)

    with open(local_file, "rb") as file_obj:
        ftp.storbinary(f"STOR {remote_file}", file_obj)

    if chmod_mode:
        set_remote_permissions(ftp, remote_path, chmod_mode)

    size = os.path.getsize(local_file)
    print(f"uploaded: {remote_path} ({format_size(size)})")
    return 1


def upload_directory_contents(ftp, local_dir, remote_dir, chmod_mode=None):
    """Upload first-level regular files in a directory."""
    remote_dir = normalize_remote_path(remote_dir)
    ensure_dir(ftp, remote_dir, chmod_mode=chmod_mode)
    ftp.cwd(remote_dir)

    uploaded_files = 0
    skipped_items = []
    for name in sorted(os.listdir(local_dir)):
        local_path = os.path.join(local_dir, name)
        if os.path.islink(local_path):
            print(f"  skip symlink: {local_path}")
            skipped_items.append(local_path)
            continue
        if not os.path.isfile(local_path):
            print(f"  skip non-regular file: {local_path}")
            skipped_items.append(local_path)
            continue

        uploaded_files += upload_file(
            ftp,
            local_path,
            join_remote_path(remote_dir, name),
            chmod_mode=chmod_mode,
        )

    print(f"directory uploaded: {remote_dir}/ ({uploaded_files} files)")
    return uploaded_files, skipped_items


def upload_directory_tree(ftp, local_root, remote_root="/", chmod_mode=None):
    """Recursively upload a directory tree."""
    local_root = os.path.abspath(local_root)
    remote_root = normalize_remote_path(remote_root)

    if not os.path.isdir(local_root):
        raise RuntimeError(f"directory does not exist: {local_root}")

    uploaded_files = 0
    skipped_items = []
    ensure_dir(ftp, remote_root, chmod_mode=chmod_mode)

    for current_root, dirnames, filenames in os.walk(
        local_root, topdown=True, followlinks=False
    ):
        dirnames.sort()
        filenames.sort()

        relative_dir = os.path.relpath(current_root, local_root)
        if relative_dir == ".":
            remote_dir = remote_root
        else:
            remote_dir = join_remote_path(remote_root, relative_dir)

        ensure_dir(ftp, remote_dir, chmod_mode=chmod_mode)

        kept_dirnames = []
        for dirname in dirnames:
            local_dir = os.path.join(current_root, dirname)
            if os.path.islink(local_dir):
                print(f"  skip dir symlink: {local_dir}")
                skipped_items.append(local_dir)
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in filenames:
            local_path = os.path.join(current_root, filename)
            if os.path.islink(local_path):
                print(f"  skip file symlink: {local_path}")
                skipped_items.append(local_path)
                continue
            if not os.path.isfile(local_path):
                print(f"  skip non-regular file: {local_path}")
                skipped_items.append(local_path)
                continue

            remote_path = join_remote_path(remote_dir, filename)
            uploaded_files += upload_file(
                ftp,
                local_path,
                remote_path,
                chmod_mode=chmod_mode,
            )

    print(f"rootfs uploaded: {local_root} -> {remote_root} ({uploaded_files} files)")
    if skipped_items:
        print(f"skipped {len(skipped_items)} symlinks or special files")
    return uploaded_files, skipped_items


def parse_config_mk(project_path):
    """Extract platform list and build type from config.mk."""
    config_mk = os.path.join(project_path, "config.mk")
    platforms = []
    debug_level = "release"

    if not os.path.exists(config_mk):
        return platforms, debug_level

    with open(config_mk, "r", encoding="utf-8", errors="ignore") as file_obj:
        for line in file_obj:
            stripped = line.strip()

            debug_match = re.match(r"^DEBUG_LEVEL\s*:?=\s*(.+)$", stripped)
            if debug_match:
                value = debug_match.group(1).strip().lower()
                if value in ("debug", "release"):
                    debug_level = value
                continue

            platform_match = re.match(r"^PLATFORMS\s*:?=\s*(.+)$", stripped)
            if platform_match:
                value = platform_match.group(1).strip()
                if value:
                    platforms = value.split()

    return platforms, debug_level


def discover_build_platforms(project_path):
    """Infer built platforms from the build directory."""
    build_dir = os.path.join(project_path, "build")
    if not os.path.isdir(build_dir):
        return []

    return sorted(
        entry
        for entry in os.listdir(build_dir)
        if os.path.isdir(os.path.join(build_dir, entry))
    )


def resolve_reproject_src_candidates(
    src, project_path, project_name, platforms, debug_level
):
    """Expand .reproject source path variables into candidate paths."""
    normalized = src.replace("\\", "/")
    normalized = normalized.replace(f"$(WORKSPACE_{project_name})", project_path)

    output_name = "Debug" if debug_level == "debug" else "Release"

    replacements_list = []
    for platform in platforms:
        replacements_list.append(
            {
                "$(Output)": f"build/{platform}/{output_name}",
                "$(Debug)": f"build/{platform}/Debug",
                "$(Release)": f"build/{platform}/Release",
            }
        )

    replacements_list.append(
        {
            "$(Output)": output_name,
            "$(Debug)": "Debug",
            "$(Release)": "Release",
        }
    )

    candidates = []
    seen = set()
    for replacements in replacements_list:
        resolved = normalized
        for token, value in replacements.items():
            resolved = resolved.replace(token, value)
        resolved = os.path.normpath(resolved)
        if resolved not in seen:
            seen.add(resolved)
            candidates.append(resolved)

    if not candidates:
        candidates.append(os.path.normpath(normalized))
    return candidates


def parse_reproject(project_path):
    """Parse .reproject and return board IP and upload items."""
    reproject_file = os.path.join(project_path, ".reproject")
    if not os.path.exists(reproject_file):
        print(f"error: missing .reproject: {reproject_file}")
        sys.exit(1)

    with open(reproject_file, "r", encoding="gb2312") as file_obj:
        content = file_obj.read()

    root = ET.fromstring(content)
    device_setting = root.find(".//DeviceSetting")
    if device_setting is None:
        print("error: DeviceSetting not found in .reproject")
        sys.exit(1)

    board_ip = (device_setting.get("DevName") or "").strip()
    if not board_ip:
        print("error: board IP (DeviceSetting/@DevName) missing in .reproject")
        sys.exit(1)

    project_name = os.path.basename(project_path)
    config_platforms, debug_level = parse_config_mk(project_path)
    device_platform = (device_setting.get("Platform") or "").strip()
    build_platforms = discover_build_platforms(project_path)

    platforms = []
    if device_platform:
        platforms.append(device_platform)
    platforms.extend(config_platforms)
    platforms.extend(build_platforms)

    ordered_platforms = []
    seen_platforms = set()
    for platform in platforms + ["ARM64_GENERIC"]:
        if platform and platform not in seen_platforms:
            seen_platforms.add(platform)
            ordered_platforms.append(platform)

    upload_paths = []
    for pair in root.findall(".//UploadPath/PairItem"):
        src = pair.get("key")
        dst = pair.get("value")
        if not src or not dst:
            continue

        candidates = resolve_reproject_src_candidates(
            src,
            project_path,
            project_name,
            ordered_platforms,
            debug_level,
        )
        resolved_src = next(
            (candidate for candidate in candidates if os.path.exists(candidate)),
            None,
        )
        if resolved_src:
            upload_paths.append((resolved_src, dst))
        else:
            print(f"warning: source missing, skipped: {candidates[0]}")

    return board_ip, upload_paths


def main():
    parser = argparse.ArgumentParser(
        description="SylixOS FTP upload tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s -P /path/to/project
  %(prog)s -P . -i 10.13.21.100
  %(prog)s -i 10.13.21.42 -f lyn_drv.ko -t /lib/modules/drivers/lyn_drv.ko
  %(prog)s -i 10.13.21.42 -f liblyn_drv.so -d /lib/
  %(prog)s -i 10.13.21.42 -c upload_list.txt
  %(prog)s -i 10.13.21.42 --rootfs /path/to/rootfs --rootfs-target /
        """,
    )

    parser.add_argument("-P", "--project", help="project directory; parse .reproject")
    parser.add_argument("-i", "--ip", help="board IP; overrides .reproject")
    parser.add_argument("-u", "--user", default="root", help="FTP username")
    parser.add_argument("-p", "--password", default="root", help="FTP password")
    parser.add_argument("-f", "--file", help="local file path")
    parser.add_argument("-t", "--target", help="remote file path")
    parser.add_argument("-d", "--dir", help="remote directory; keep local filename")
    parser.add_argument(
        "-c",
        "--config",
        help="batch config file; each line is local_path|remote_path",
    )
    parser.add_argument(
        "-r",
        "--rootfs",
        help="local rootfs directory; upload recursively without .reproject",
    )
    parser.add_argument(
        "--rootfs-target",
        default="/",
        help="target root path for rootfs upload",
    )
    parser.add_argument(
        "-m",
        "--chmod",
        type=validate_permission_mode,
        default="755",
        help="remote chmod after upload; default 755",
    )
    parser.add_argument(
        "--no-chmod",
        action="store_true",
        help="disable remote chmod after upload",
    )
    parser.add_argument(
        "--sync",
        dest="sync",
        action="store_true",
        default=True,
        help="run remote sync once after all uploads; default enabled",
    )
    parser.add_argument(
        "--no-sync",
        dest="sync",
        action="store_false",
        help="disable remote sync after upload",
    )

    args = parser.parse_args()

    selected_modes = sum(
        bool(value) for value in [args.project, args.config, args.file, args.rootfs]
    )
    if selected_modes == 0:
        parser.error("one of --project, --file, --config, or --rootfs is required")
    if selected_modes > 1:
        parser.error("--project, --file, --config, and --rootfs are mutually exclusive")

    if args.file and not (args.target or args.dir):
        parser.error("--file requires --target or --dir")
    if args.file and args.target and args.dir:
        parser.error("--target and --dir are mutually exclusive")
    if args.rootfs_target != "/" and not args.rootfs:
        parser.error("--rootfs-target can only be used with --rootfs")

    chmod_mode = None if args.no_chmod else args.chmod
    upload_list = []
    board_ip = args.ip

    if args.project:
        project_path = os.path.abspath(args.project)
        print(f"parsing project: {project_path}")
        parsed_ip, parsed_list = parse_reproject(project_path)
        if not board_ip:
            board_ip = parsed_ip
        upload_list = parsed_list
        print(f"board IP: {board_ip}")
        print(f"upload items: {len(upload_list)}\n")

        if not upload_list:
            print("error: no valid upload items resolved from .reproject")
            sys.exit(1)

    if not board_ip:
        parser.error("board IP is required unless --project resolves it from .reproject")

    try:
        print(f"connecting to {board_ip}...")
        ftp = FTP()
        ftp.connect(board_ip, 21, timeout=10)
        ftp.login(args.user, args.password)
        ftp.set_pasv(True)
        print("login succeeded\n")

        success_count = 0
        fail_count = 0
        uploaded_file_count = 0

        if args.project:
            for index, (src, dst) in enumerate(upload_list, 1):
                try:
                    print(f"[{index}/{len(upload_list)}] {os.path.basename(src)}")
                    if os.path.isfile(src):
                        uploaded_file_count += upload_file(
                            ftp,
                            src,
                            dst,
                            chmod_mode=chmod_mode,
                        )
                    elif os.path.isdir(src):
                        uploaded_files, _ = upload_directory_contents(
                            ftp,
                            src,
                            dst,
                            chmod_mode=chmod_mode,
                        )
                        uploaded_file_count += uploaded_files
                    success_count += 1
                    print()
                except Exception as exc:
                    print(f"  upload failed: {exc}\n")
                    fail_count += 1

        elif args.config:
            with open(args.config, "r", encoding="utf-8", errors="ignore") as file_obj:
                for line in file_obj:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split("|")
                    if len(parts) != 2:
                        print(f"skip invalid line: {line}")
                        continue

                    local_file, remote_path = parts
                    if not os.path.exists(local_file):
                        print(f"source missing: {local_file}")
                        fail_count += 1
                        continue

                    print(f"upload: {os.path.basename(local_file)}")
                    if os.path.isfile(local_file):
                        uploaded_file_count += upload_file(
                            ftp,
                            local_file,
                            remote_path,
                            chmod_mode=chmod_mode,
                        )
                    elif os.path.isdir(local_file):
                        uploaded_files, _ = upload_directory_tree(
                            ftp,
                            local_file,
                            remote_path,
                            chmod_mode=chmod_mode,
                        )
                        uploaded_file_count += uploaded_files
                    success_count += 1

        elif args.rootfs:
            print(f"upload rootfs: {args.rootfs}")
            uploaded_files, _ = upload_directory_tree(
                ftp,
                args.rootfs,
                args.rootfs_target,
                chmod_mode=chmod_mode,
            )
            uploaded_file_count += uploaded_files
            success_count += 1

        else:
            if not os.path.exists(args.file):
                print(f"error: source missing: {args.file}")
                sys.exit(1)

            if args.target:
                remote_path = normalize_remote_path(args.target)
            else:
                remote_path = join_remote_path(args.dir, os.path.basename(args.file))

            print(f"upload: {os.path.basename(args.file)}")
            uploaded_file_count += upload_file(
                ftp,
                args.file,
                remote_path,
                chmod_mode=chmod_mode,
            )
            success_count += 1

        if args.sync:
            sync_remote(ftp)

        ftp.quit()

        print("\n=== upload complete ===")
        if args.project or args.config or args.rootfs:
            print(f"success items: {success_count}")
            print(f"failed items: {fail_count}")
            print(f"total items: {success_count + fail_count}")
            print(f"uploaded files: {uploaded_file_count}")
        else:
            print("upload succeeded")

    except Exception as exc:
        print(f"\nerror: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
