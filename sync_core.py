import os
import hashlib
import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, List, Dict
from pathlib import Path


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


def scan_directory(directory: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, FileInfo]:
    files = {}
    directory = os.path.abspath(directory)
    
    if not os.path.exists(directory):
        return files
    
    all_files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            all_files.append(full_path)
    
    total = len(all_files)
    for idx, full_path in enumerate(all_files):
        try:
            relative_path = os.path.relpath(full_path, directory)
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


def sync_file(
    diff: DiffResult,
    wintogo_dir: str,
    local_dir: str,
    direction: str
) -> bool:
    wintogo_path = os.path.join(wintogo_dir, diff.relative_path)
    local_path = os.path.join(local_dir, diff.relative_path)
    
    if diff.status == FileStatus.WINTOGO_ONLY:
        if direction == "to_local":
            return copy_file(wintogo_path, local_path)
    elif diff.status == FileStatus.LOCAL_ONLY:
        if direction == "to_wintogo":
            return copy_file(local_path, wintogo_path)
    elif diff.status == FileStatus.CONFLICT:
        if direction == "wintogo_to_local":
            return copy_file(wintogo_path, local_path)
        elif direction == "local_to_wintogo":
            return copy_file(local_path, wintogo_path)
    
    return False
