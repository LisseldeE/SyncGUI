import os
import hashlib
import shutil
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, List, Dict
from pathlib import Path

if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    import msvcrt
    
    kernel32 = ctypes.windll.kernel32
    
    COPY_FILE_CALLBACK = ctypes.WINFUNCTYPE(
        wintypes.DWORD,
        wintypes.LARGE_INTEGER,
        wintypes.LARGE_INTEGER,
        wintypes.LARGE_INTEGER,
        wintypes.LARGE_INTEGER,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.LPVOID
    )
    
    COPY_FILE_FAIL_IF_EXISTS = 0x00000001
    COPY_FILE_RESTARTABLE = 0x00000002
    PROGRESS_CONTINUE = 0
    PROGRESS_CANCEL = 1
    PROGRESS_STOP = 2
    PROGRESS_QUIET = 3


class FileStatus(Enum):
    WINTOGO_ONLY = "wintogo_only"
    LOCAL_ONLY = "local_only"
    SAME = "same"
    CONFLICT = "conflict"
    MTIME_DIFF = "mtime_diff"


@dataclass
class FileInfo:
    relative_path: str
    size: int
    mtime: float
    hash: Optional[str] = None
    is_dir: bool = False
    is_symlink: bool = False
    symlink_target: Optional[str] = None


@dataclass
class DiffResult:
    relative_path: str
    status: FileStatus
    wintogo_info: Optional[FileInfo] = None
    local_info: Optional[FileInfo] = None


def calculate_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def scan_directory(
    directory: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    ignore_rules: Optional[List[str]] = None,
    progress_interval: int = 100
) -> Dict[str, FileInfo]:
    files = {}
    directory = os.path.abspath(directory)
    
    if not os.path.exists(directory):
        return files
    
    if ignore_rules is None:
        ignore_rules = []
    
    def should_ignore(relative_path: str) -> bool:
        normalized_path = relative_path.replace('\\', '/')
        
        for rule in ignore_rules:
            rule = rule.replace('\\', '/')
            
            if rule.endswith('/'):
                dir_name = rule[:-1]
                if normalized_path.startswith(dir_name + '/') or normalized_path.startswith(dir_name + '\\'):
                    return True
                parts = normalized_path.split('/')
                for i, part in enumerate(parts[:-1]):
                    if part == dir_name:
                        return True
            elif rule.startswith('.'):
                ext = rule
                if normalized_path.endswith(ext):
                    if '/' in rule:
                        dir_part = rule.rsplit('/', 1)[0]
                        if normalized_path.startswith(dir_part + '/') or normalized_path.startswith(dir_part + '\\'):
                            return True
                    else:
                        return True
            else:
                if '/' in rule:
                    dir_part, ext = rule.rsplit('.', 1) if '.' in rule else (rule, '')
                    if ext:
                        ext = '.' + ext
                        if normalized_path.startswith(dir_part + '/') and normalized_path.endswith(ext):
                            return True
        
        return False
    
    total = 0
    processed = 0
    last_progress_update = 0
    
    all_dirs = set()
    dirs_with_files = set()
    
    for root, dirnames, filenames in os.walk(directory):
        total += len(filenames)
        for dirname in dirnames:
            all_dirs.add(os.path.join(root, dirname))
        if filenames:
            dirs_with_files.add(root)
    
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            processed += 1
            
            try:
                relative_path = os.path.relpath(full_path, directory)
                
                if should_ignore(relative_path):
                    if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                        progress_callback(processed, total)
                        last_progress_update = processed
                    continue
                
                is_symlink = os.path.islink(full_path)
                symlink_target = None
                if is_symlink:
                    try:
                        symlink_target = os.readlink(full_path)
                    except (OSError, PermissionError):
                        pass
                
                stat = os.stat(full_path)
                files[relative_path] = FileInfo(
                    relative_path=relative_path,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                    is_dir=False,
                    is_symlink=is_symlink,
                    symlink_target=symlink_target
                )
            except (OSError, PermissionError):
                pass
            
            if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                progress_callback(processed, total)
                last_progress_update = processed
    
    leaf_empty_dirs = set()
    for dir_path in all_dirs:
        try:
            relative_dir = os.path.relpath(dir_path, directory)
            if should_ignore(relative_dir):
                continue
            
            has_any_content = False
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    has_any_content = True
                    break
                elif os.path.isdir(item_path):
                    has_any_content = True
                    break
            
            if not has_any_content:
                leaf_empty_dirs.add(dir_path)
        except (OSError, PermissionError):
            pass
    
    empty_dirs = leaf_empty_dirs.copy()
    for leaf_dir in leaf_empty_dirs:
        parent = os.path.dirname(leaf_dir)
        while parent and parent != directory and len(parent) > len(directory):
            try:
                parent_rel = os.path.relpath(parent, directory)
                if should_ignore(parent_rel):
                    break
                
                parent_has_other_content = False
                for item in os.listdir(parent):
                    item_path = os.path.join(parent, item)
                    item_rel = os.path.relpath(item_path, directory)
                    if os.path.isfile(item_path):
                        parent_has_other_content = True
                        break
                    elif os.path.isdir(item_path):
                        if item_path not in empty_dirs:
                            parent_has_other_content = True
                            break
                
                if not parent_has_other_content:
                    empty_dirs.add(parent)
                    parent = os.path.dirname(parent)
                else:
                    break
            except (OSError, PermissionError):
                break
    
    for empty_dir in empty_dirs:
        try:
            relative_path = os.path.relpath(empty_dir, directory)
            stat = os.stat(empty_dir)
            files[relative_path] = FileInfo(
                relative_path=relative_path,
                size=0,
                mtime=stat.st_mtime,
                is_dir=True
            )
        except (OSError, PermissionError):
            pass
    
    return files


def compare_files(
    wintogo_files: Dict[str, FileInfo],
    local_files: Dict[str, FileInfo],
    wintogo_dir: str,
    local_dir: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    progress_interval: int = 100
) -> List[DiffResult]:
    results = []
    all_paths = set(wintogo_files.keys()) | set(local_files.keys())
    total = len(all_paths)
    processed = 0
    last_progress_update = 0
    
    for path in all_paths:
        processed += 1
        wintogo_info = wintogo_files.get(path)
        local_info = local_files.get(path)
        
        if wintogo_info and not local_info:
            results.append(DiffResult(
                relative_path=path,
                status=FileStatus.WINTOGO_ONLY,
                wintogo_info=wintogo_info
            ))
        elif not wintogo_info and local_info:
            results.append(DiffResult(
                relative_path=path,
                status=FileStatus.LOCAL_ONLY,
                local_info=local_info
            ))
        else:
            if wintogo_info.size != local_info.size:
                results.append(DiffResult(
                    relative_path=path,
                    status=FileStatus.CONFLICT,
                    wintogo_info=wintogo_info,
                    local_info=local_info
                ))
            else:
                if abs(wintogo_info.mtime - local_info.mtime) > 1:
                    results.append(DiffResult(
                        relative_path=path,
                        status=FileStatus.MTIME_DIFF,
                        wintogo_info=wintogo_info,
                        local_info=local_info
                    ))
                else:
                    results.append(DiffResult(
                        relative_path=path,
                        status=FileStatus.SAME,
                        wintogo_info=wintogo_info,
                        local_info=local_info
                    ))
        
        if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
            progress_callback(processed, total)
            last_progress_update = processed
    
    return results


def is_file_locked(file_path: str) -> bool:
    if sys.platform == 'win32':
        try:
            handle = kernel32.CreateFileW(
                file_path,
                0x80000000,
                0,
                None,
                3,
                0x00000001,
                None
            )
            if handle == -1:
                return True
            kernel32.CloseHandle(handle)
            return False
        except Exception:
            return True
    else:
        try:
            with open(file_path, 'rb') as f:
                pass
            return False
        except (IOError, PermissionError):
            return True


def copy_file(source_path: str, dest_path: str, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    try:
        dest_dir = os.path.dirname(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        for attempt in range(max_retries):
            try:
                shutil.copy2(source_path, dest_path)
                return True
            except (OSError, PermissionError) as e:
                if attempt < max_retries - 1:
                    if is_file_locked(source_path) or is_file_locked(dest_path):
                        print(f"File locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        break
                else:
                    print(f"Error copying {source_path} to {dest_path}: {e}")
                    return False
        return False
    except (OSError, PermissionError) as e:
        print(f"Error copying {source_path} to {dest_path}: {e}")
        return False


def delete_file(file_path: str, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    try:
        if os.path.exists(file_path):
            for attempt in range(max_retries):
                try:
                    os.remove(file_path)
                    break
                except (OSError, PermissionError) as e:
                    if attempt < max_retries - 1:
                        if is_file_locked(file_path):
                            print(f"File locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                        else:
                            print(f"Error deleting {file_path}: {e}")
                            return False
                    else:
                        print(f"Error deleting {file_path}: {e}")
                        return False
        
        parent = os.path.dirname(file_path)
        while parent and len(parent) > 3:
            try:
                os.rmdir(parent)
                parent = os.path.dirname(parent)
            except OSError:
                break
        return True
    except (OSError, PermissionError) as e:
        print(f"Error deleting {file_path}: {e}")
        return False


def copy_file_with_progress(
    source_path: str, 
    dest_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = 1024 * 1024,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> bool:
    dest_dir = os.path.dirname(dest_path)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    for attempt in range(max_retries):
        if sys.platform == 'win32' and progress_callback:
            result = _copy_file_win32(source_path, dest_path, progress_callback)
        else:
            result = _copy_file_fallback(source_path, dest_path, progress_callback, chunk_size)
        
        if result:
            return True
        
        if attempt < max_retries - 1:
            if is_file_locked(source_path) or is_file_locked(dest_path):
                print(f"File locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                break
    
    return False


def _copy_file_win32(source_path: str, dest_path: str, progress_callback: Callable[[int, int], None]) -> bool:
    try:
        @COPY_FILE_CALLBACK
        def win_progress_callback(
            total_file_size, total_bytes_transferred,
            stream_size, stream_bytes_transferred,
            stream_number, callback_reason,
            source_file, dest_file, data
        ):
            transferred = int(total_bytes_transferred)
            total = int(total_file_size)
            if progress_callback:
                progress_callback(transferred, total)
            return PROGRESS_CONTINUE
        
        result = kernel32.CopyFileExW(
            source_path,
            dest_path,
            win_progress_callback,
            None,
            None,
            0
        )
        
        if result == 0:
            error = ctypes.get_last_error()
            print(f"CopyFileEx failed with error: {error}")
            return False
        return True
        
    except Exception as e:
        print(f"Error copying {source_path} to {dest_path}: {e}")
        return False


def _copy_file_fallback(
    source_path: str, 
    dest_path: str,
    progress_callback: Optional[Callable[[int, int], None]],
    chunk_size: int
) -> bool:
    try:
        file_size = os.path.getsize(source_path)
        copied = 0
        
        with open(source_path, 'rb') as src:
            with open(dest_path, 'wb') as dst:
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    copied += len(chunk)
                    if progress_callback:
                        progress_callback(copied, file_size)
        
        shutil.copystat(source_path, dest_path)
        return True
    except (OSError, PermissionError) as e:
        print(f"Error copying {source_path} to {dest_path}: {e}")
        return False


def sync_file(
    diff: DiffResult,
    wintogo_dir: str,
    local_dir: str,
    direction: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> bool:
    wintogo_path = os.path.join(wintogo_dir, diff.relative_path)
    local_path = os.path.join(local_dir, diff.relative_path)
    
    is_symlink = False
    symlink_target = None
    if diff.wintogo_info and diff.wintogo_info.is_symlink:
        is_symlink = True
        symlink_target = diff.wintogo_info.symlink_target
    elif diff.local_info and diff.local_info.is_symlink:
        is_symlink = True
        symlink_target = diff.local_info.symlink_target
    
    if is_symlink:
        if diff.status == FileStatus.WINTOGO_ONLY:
            if direction == "to_local":
                try:
                    if os.path.exists(local_path) or os.path.islink(local_path):
                        os.remove(local_path)
                    if symlink_target:
                        os.symlink(symlink_target, local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error creating symlink {local_path}: {e}")
                    return False
            elif direction == "delete_wintogo":
                try:
                    if os.path.islink(wintogo_path):
                        os.remove(wintogo_path)
                    elif os.path.exists(wintogo_path):
                        shutil.rmtree(wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting symlink {wintogo_path}: {e}")
                    return False
        elif diff.status == FileStatus.LOCAL_ONLY:
            if direction == "to_wintogo":
                try:
                    if os.path.exists(wintogo_path) or os.path.islink(wintogo_path):
                        os.remove(wintogo_path)
                    if symlink_target:
                        os.symlink(symlink_target, wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error creating symlink {wintogo_path}: {e}")
                    return False
            elif direction == "delete_local":
                try:
                    if os.path.islink(local_path):
                        os.remove(local_path)
                    elif os.path.exists(local_path):
                        shutil.rmtree(local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting symlink {local_path}: {e}")
                    return False
        elif diff.status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
            if direction == "delete_both":
                try:
                    if os.path.islink(wintogo_path) or os.path.exists(wintogo_path):
                        os.remove(wintogo_path) if os.path.islink(wintogo_path) else shutil.rmtree(wintogo_path)
                    if os.path.islink(local_path) or os.path.exists(local_path):
                        os.remove(local_path) if os.path.islink(local_path) else shutil.rmtree(local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting symlinks: {e}")
                    return False
        return True
    
    is_dir = False
    if diff.wintogo_info and diff.wintogo_info.is_dir:
        is_dir = True
    elif diff.local_info and diff.local_info.is_dir:
        is_dir = True
    
    if is_dir:
        if diff.status == FileStatus.WINTOGO_ONLY:
            if direction == "to_local":
                try:
                    os.makedirs(local_path, exist_ok=True)
                    shutil.copystat(wintogo_path, local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error creating directory {local_path}: {e}")
                    return False
            elif direction == "delete_wintogo":
                try:
                    shutil.rmtree(wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting directory {wintogo_path}: {e}")
                    return False
        elif diff.status == FileStatus.LOCAL_ONLY:
            if direction == "to_wintogo":
                try:
                    os.makedirs(wintogo_path, exist_ok=True)
                    shutil.copystat(local_path, wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error creating directory {wintogo_path}: {e}")
                    return False
            elif direction == "delete_local":
                try:
                    shutil.rmtree(local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting directory {local_path}: {e}")
                    return False
        elif diff.status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
            if direction == "delete_both":
                try:
                    if os.path.isdir(wintogo_path):
                        shutil.rmtree(wintogo_path)
                    if os.path.isdir(local_path):
                        shutil.rmtree(local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting directories: {e}")
                    return False
        return True
    
    if diff.status == FileStatus.WINTOGO_ONLY:
        if direction == "to_local":
            return copy_file_with_progress(wintogo_path, local_path, progress_callback)
        elif direction == "delete_wintogo":
            return delete_file(wintogo_path)
    elif diff.status == FileStatus.LOCAL_ONLY:
        if direction == "to_wintogo":
            return copy_file_with_progress(local_path, wintogo_path, progress_callback)
        elif direction == "delete_local":
            return delete_file(local_path)
    elif diff.status == FileStatus.CONFLICT:
        if direction == "wintogo_to_local":
            return copy_file_with_progress(wintogo_path, local_path, progress_callback)
        elif direction == "local_to_wintogo":
            return copy_file_with_progress(local_path, wintogo_path, progress_callback)
        elif direction == "delete_both":
            deleted_wintogo = delete_file(wintogo_path)
            deleted_local = delete_file(local_path)
            return deleted_wintogo and deleted_local
    elif diff.status == FileStatus.MTIME_DIFF:
        if direction == "wintogo_to_local":
            return copy_file_with_progress(wintogo_path, local_path, progress_callback)
        elif direction == "local_to_wintogo":
            return copy_file_with_progress(local_path, wintogo_path, progress_callback)
        elif direction == "delete_both":
            deleted_wintogo = delete_file(wintogo_path)
            deleted_local = delete_file(local_path)
            return deleted_wintogo and deleted_local
    
    return False
