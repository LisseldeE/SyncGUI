import os
import hashlib
import shutil
import sys
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


@dataclass
class FileInfo:
    relative_path: str
    size: int
    mtime: float
    hash: Optional[str] = None


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
    ignore_rules: Optional[List[str]] = None
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
    
    all_files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            all_files.append(full_path)
    
    total = len(all_files)
    for idx, full_path in enumerate(all_files):
        try:
            relative_path = os.path.relpath(full_path, directory)
            
            if should_ignore(relative_path):
                if progress_callback:
                    progress_callback(idx + 1, total)
                continue
            
            stat = os.stat(full_path)
            files[relative_path] = FileInfo(
                relative_path=relative_path,
                size=stat.st_size,
                mtime=stat.st_mtime
            )
        except (OSError, PermissionError):
            continue
        
        if progress_callback:
            progress_callback(idx + 1, total)
    
    return files


def compare_files(
    wintogo_files: Dict[str, FileInfo],
    local_files: Dict[str, FileInfo],
    wintogo_dir: str,
    local_dir: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[DiffResult]:
    results = []
    all_paths = set(wintogo_files.keys()) | set(local_files.keys())
    total = len(all_paths)
    
    for idx, path in enumerate(all_paths):
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
                wintogo_hash = calculate_file_hash(os.path.join(wintogo_dir, path))
                local_hash = calculate_file_hash(os.path.join(local_dir, path))
                wintogo_info.hash = wintogo_hash
                local_info.hash = local_hash
                
                if wintogo_hash != local_hash:
                    results.append(DiffResult(
                        relative_path=path,
                        status=FileStatus.CONFLICT,
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
            else:
                results.append(DiffResult(
                    relative_path=path,
                    status=FileStatus.SAME,
                    wintogo_info=wintogo_info,
                    local_info=local_info
                ))
        
        if progress_callback:
            progress_callback(idx + 1, total)
    
    return results


def copy_file(source_path: str, dest_path: str) -> bool:
    try:
        dest_dir = os.path.dirname(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        shutil.copy2(source_path, dest_path)
        return True
    except (OSError, PermissionError) as e:
        print(f"Error copying {source_path} to {dest_path}: {e}")
        return False


def copy_file_with_progress(
    source_path: str, 
    dest_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = 1024 * 1024
) -> bool:
    dest_dir = os.path.dirname(dest_path)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    if sys.platform == 'win32' and progress_callback:
        return _copy_file_win32(source_path, dest_path, progress_callback)
    else:
        return _copy_file_fallback(source_path, dest_path, progress_callback, chunk_size)


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
    
    if diff.status == FileStatus.WINTOGO_ONLY:
        if direction == "to_local":
            return copy_file_with_progress(wintogo_path, local_path, progress_callback)
    elif diff.status == FileStatus.LOCAL_ONLY:
        if direction == "to_wintogo":
            return copy_file_with_progress(local_path, wintogo_path, progress_callback)
    elif diff.status == FileStatus.CONFLICT:
        if direction == "wintogo_to_local":
            return copy_file_with_progress(wintogo_path, local_path, progress_callback)
        elif direction == "local_to_wintogo":
            return copy_file_with_progress(local_path, wintogo_path, progress_callback)
    
    return False
