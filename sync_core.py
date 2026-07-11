"""
SyncGUI - 同步核心模块

Author: Lisselde_E
GitHub: https://github.com/LisseldeE
License: MIT
"""

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
    
    # 使用 use_last_error=True 加载 kernel32，使 CopyFileExW 失败时
    # 可通过 ctypes.get_last_error() 取得真实 Win32 错误码（否则始终为 0）
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CopyFileExW.restype = wintypes.BOOL
    
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
    
    FILE_ATTRIBUTE_READONLY = 0x00000001
    FILE_ATTRIBUTE_HIDDEN = 0x00000002
    FILE_ATTRIBUTE_SYSTEM = 0x00000004
    FILE_ATTRIBUTE_ARCHIVE = 0x00000020
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    FILE_ATTRIBUTE_TEMPORARY = 0x00000100
    FILE_ATTRIBUTE_OFFLINE = 0x00001000
    FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 0x00002000
    FILE_ATTRIBUTE_NO_SCRUB_DATA = 0x00020000
    
    SYNC_ATTRIBUTES = (
        FILE_ATTRIBUTE_READONLY |
        FILE_ATTRIBUTE_HIDDEN |
        FILE_ATTRIBUTE_SYSTEM |
        FILE_ATTRIBUTE_ARCHIVE |
        FILE_ATTRIBUTE_TEMPORARY |
        FILE_ATTRIBUTE_OFFLINE |
        FILE_ATTRIBUTE_NOT_CONTENT_INDEXED |
        FILE_ATTRIBUTE_NO_SCRUB_DATA
    )
    
    def get_file_attributes(file_path: str) -> int:
        # GetFileAttributesW 返回 DWORD，但 ctypes 默认 restype 为 c_int
        # INVALID_FILE_ATTRIBUTES (0xFFFFFFFF) 在 c_int 中为 -1
        INVALID = 0xFFFFFFFF
        attrs = kernel32.GetFileAttributesW(file_path)
        if attrs == -1 or attrs == INVALID:
            return FILE_ATTRIBUTE_NORMAL
        return attrs
    
    def set_file_attributes(file_path: str, attributes: int) -> bool:
        result = kernel32.SetFileAttributesW(file_path, attributes)
        return result != 0
    
    def sync_file_attributes(source_path: str, dest_path: str) -> bool:
        source_attrs = get_file_attributes(source_path)
        sync_attrs = source_attrs & SYNC_ATTRIBUTES
        if sync_attrs == 0:
            sync_attrs = FILE_ATTRIBUTE_NORMAL
        return set_file_attributes(dest_path, sync_attrs)
    
    def sync_dir_attributes(source_path: str, dest_path: str) -> bool:
        shutil.copystat(source_path, dest_path)
        return sync_file_attributes(source_path, dest_path)


def _make_writable(path: str) -> None:
    """递归移除路径下所有文件/目录的只读/系统/隐藏属性，确保可删除（Windows only）"""
    if sys.platform != 'win32':
        return
    for root, dirs, files in os.walk(path):
        for name in files + dirs:
            full = os.path.join(root, name)
            try:
                attrs = get_file_attributes(full)
                REMOVE_MASK = FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN
                if attrs & REMOVE_MASK:
                    set_file_attributes(full, attrs & ~REMOVE_MASK)
            except Exception:
                pass


def rmtree_safe(path: str) -> None:
    """安全删除目录树，自动处理 Windows 特殊属性"""
    _make_writable(path)
    shutil.rmtree(path)


# 文件比较容差与校验阈值
MTIME_TOLERANCE = 2.0  # mtime 容差（秒），FAT32/exFAT 时间戳精度为 2 秒
HASH_VERIFY_MAX_SIZE = 64 * 1024 * 1024  # 超过此大小跳过哈希校验以控制性能，回退为信任 size+mtime


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


def _content_matches(file_a: str, file_b: str, size: int) -> bool:
    """校验两文件内容是否一致。

    size 相同且 mtime 相近时调用，避免仅凭 size+mtime 将同尺寸不同内容文件误判为相同。
    超过 HASH_VERIFY_MAX_SIZE 的大文件跳过哈希以控制性能，回退为信任 size+mtime（保持原行为）。
    哈希计算失败时保守地视为一致，避免因校验异常而误升级为冲突。
    """
    if size > HASH_VERIFY_MAX_SIZE:
        return True
    try:
        return calculate_file_hash(file_a) == calculate_file_hash(file_b)
    except (OSError, PermissionError):
        return True


def _safe_remove(path: str) -> None:
    """安全删除文件，忽略不存在或权限错误"""
    try:
        os.remove(path)
    except OSError:
        pass


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
                if rule.startswith('**/'):
                    dir_name = rule[3:-1]
                    parts = normalized_path.split('/')
                    for part in parts:
                        if part == dir_name:
                            return True
                else:
                    dir_name = rule[:-1]
                    if normalized_path.startswith(dir_name + '/'):
                        return True
                    if normalized_path == dir_name:
                        return True
            elif rule.startswith('.'):
                ext = rule
                if normalized_path.endswith(ext):
                    if '/' in rule:
                        dir_part = rule.rsplit('/', 1)[0]
                        if normalized_path.startswith(dir_part + '/'):
                            return True
                    else:
                        return True
            else:
                if '/' in rule:
                    dir_part, ext = rule.rsplit('.', 1) if '.' in rule else (rule, '')
                    if ext:
                        ext = '.' + ext
                        dir_part = dir_part.rstrip('/')
                        if normalized_path.startswith(dir_part + '/') and normalized_path.endswith(ext):
                            return True

        return False

    total = 0
    processed = 0
    last_progress_update = 0

    # 先统计文件数量
    for root, _, filenames in os.walk(directory):
        total += len(filenames)

    # 扫描文件
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

    # 扫描空目录
    # 使用更简单的方法：扫描所有空文件夹（包括叶子空文件夹和父空文件夹）
    empty_dirs = set()
    
    # 首先扫描叶子空文件夹
    for root, dirs, filenames in os.walk(directory, topdown=False):
        # 如果目录为空（没有文件和子目录）
        if not filenames and not dirs:
            try:
                relative_path = os.path.relpath(root, directory)

                if should_ignore(relative_path):
                    continue

                # 跳过根目录本身
                if relative_path == '.':
                    continue

                stat = os.stat(root)
                files[relative_path] = FileInfo(
                    relative_path=relative_path,
                    size=0,
                    mtime=stat.st_mtime,
                    is_dir=True,
                    is_symlink=False,
                    symlink_target=None
                )
                empty_dirs.add(relative_path)
            except (OSError, PermissionError):
                pass
    
    # 然后扫描父空文件夹（只包含空子文件夹的文件夹）
    # 使用更简单的方法：检查每个目录是否只包含空子文件夹
    for root, dirs, filenames in os.walk(directory, topdown=False):
        # 如果目录有文件，则不是空文件夹
        if filenames:
            continue
        
        # 如果目录没有子目录，则已经在上面处理过了
        if not dirs:
            continue
        
        try:
            relative_path = os.path.relpath(root, directory)

            if should_ignore(relative_path):
                continue

            # 跳过根目录本身
            if relative_path == '.':
                continue

            # 检查所有子目录是否都是空文件夹
            all_subdirs_empty = True
            for subdir in dirs:
                subdir_relative_path = os.path.relpath(os.path.join(root, subdir), directory)
                if subdir_relative_path not in empty_dirs:
                    all_subdirs_empty = False
                    break
            
            # 如果所有子目录都是空文件夹，则这个目录也是空文件夹
            if all_subdirs_empty:
                stat = os.stat(root)
                files[relative_path] = FileInfo(
                    relative_path=relative_path,
                    size=0,
                    mtime=stat.st_mtime,
                    is_dir=True,
                    is_symlink=False,
                    symlink_target=None
                )
                empty_dirs.add(relative_path)
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
            # 如果wintogo是文件夹，检查是否有子路径（文件夹内有内容）
            if wintogo_info.is_dir:
                has_children_in_wintogo = any(
                    p.startswith(path + '/') or p.startswith(path + '\\')
                    for p in wintogo_files.keys() if p != path
                )
                # 如果wintogo文件夹有内容，忽略文件夹本身（只同步其内部的内容）
                if has_children_in_wintogo:
                    if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                        progress_callback(processed, total)
                        last_progress_update = processed
                    continue
                
                # 检查local端是否有同名文件夹的内容
                has_children_in_local = any(
                    p.startswith(path + '/') or p.startswith(path + '\\')
                    for p in local_files.keys()
                )
                # 如果local端有同名文件夹的内容，忽略wintogo空文件夹（避免覆盖）
                if has_children_in_local:
                    if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                        progress_callback(processed, total)
                        last_progress_update = processed
                    continue
            
            results.append(DiffResult(
                relative_path=path,
                status=FileStatus.WINTOGO_ONLY,
                wintogo_info=wintogo_info
            ))
        elif not wintogo_info and local_info:
            # 如果local是文件夹，检查是否有子路径（文件夹内有内容）
            if local_info.is_dir:
                has_children_in_local = any(
                    p.startswith(path + '/') or p.startswith(path + '\\')
                    for p in local_files.keys() if p != path
                )
                # 如果local文件夹有内容，忽略文件夹本身（只处理其内部的内容）
                if has_children_in_local:
                    if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                        progress_callback(processed, total)
                        last_progress_update = processed
                    continue
                
                # 检查wintogo端是否有同名文件夹的内容
                has_children_in_wintogo = any(
                    p.startswith(path + '/') or p.startswith(path + '\\')
                    for p in wintogo_files.keys()
                )
                # 如果wintogo端有同名文件夹的内容，忽略local空文件夹（避免覆盖）
                if has_children_in_wintogo:
                    if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                        progress_callback(processed, total)
                        last_progress_update = processed
                    continue
            
            results.append(DiffResult(
                relative_path=path,
                status=FileStatus.LOCAL_ONLY,
                local_info=local_info
            ))
        else:
            # 两端都有同名项目
            if wintogo_info.is_dir != local_info.is_dir:
                # 类型冲突：一端是文件，另一端是目录
                results.append(DiffResult(
                    relative_path=path,
                    status=FileStatus.CONFLICT,
                    wintogo_info=wintogo_info,
                    local_info=local_info
                ))
            elif wintogo_info.is_dir and local_info.is_dir:
                # 两端都是空目录 — 无内容需要同步，跳过不加入 results
                # 用户如需删除，通过 DirSyncDialog 的"删除两端此目录"选项处理
                if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                    progress_callback(processed, total)
                    last_progress_update = processed
                continue
            elif wintogo_info.size != local_info.size:
                # 文件大小不同
                results.append(DiffResult(
                    relative_path=path,
                    status=FileStatus.CONFLICT,
                    wintogo_info=wintogo_info,
                    local_info=local_info
                ))
            else:
                # 文件大小相同，检查时间戳差异
                if abs(wintogo_info.mtime - local_info.mtime) > MTIME_TOLERANCE:
                    results.append(DiffResult(
                        relative_path=path,
                        status=FileStatus.MTIME_DIFF,
                        wintogo_info=wintogo_info,
                        local_info=local_info
                    ))
                else:
                    # 时间戳相近，用哈希校验内容是否真正一致，避免同尺寸不同内容被误判为相同
                    if _content_matches(
                        os.path.join(wintogo_dir, path),
                        os.path.join(local_dir, path),
                        wintogo_info.size
                    ):
                        results.append(DiffResult(
                            relative_path=path,
                            status=FileStatus.SAME,
                            wintogo_info=wintogo_info,
                            local_info=local_info
                        ))
                    else:
                        results.append(DiffResult(
                            relative_path=path,
                            status=FileStatus.MTIME_DIFF,
                            wintogo_info=wintogo_info,
                            local_info=local_info
                        ))
        
        if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
            progress_callback(processed, total)
            last_progress_update = processed
    
    return results


def compare_files_unidirectional(
    source_files: Dict[str, FileInfo],
    target_files: Dict[str, FileInfo],
    source_dir: str,
    target_dir: str,
    unidirectional_mode: str = "diff",
    extra_items_mode: str = "keep",  # 新增参数："keep" 或 "delete"
    progress_callback: Optional[Callable[[int, int], None]] = None,
    progress_interval: int = 100,
    wintogo_dir: str = None  # 新增参数：介质目录路径，用于正确设置状态
) -> List[DiffResult]:
    """
    单向同步的文件比较函数
    
    Args:
        source_files: 源目录文件列表
        target_files: 目标目录文件列表
        source_dir: 源目录路径
        target_dir: 目标目录路径
        unidirectional_mode: 单向同步模式 ("diff" 或 "overwrite")
        extra_items_mode: 多余项目处理模式 ("keep" 或 "delete")
        progress_callback: 进度回调函数
        progress_interval: 进度更新间隔
        wintogo_dir: 介质目录路径（用于正确设置状态）
    
    Returns:
        差异结果列表
    """
    results = []
    all_paths = set(source_files.keys()) | set(target_files.keys())
    total = len(all_paths)
    processed = 0
    last_progress_update = 0
    
    # 判断源是否是介质（用于正确设置状态）
    source_is_wintogo = (wintogo_dir is not None and source_dir == wintogo_dir)
    
    for path in all_paths:
        processed += 1
        source_info = source_files.get(path)
        target_info = target_files.get(path)
        
        # 源存在，目标不存在 - 需要同步到目标
        if source_info and not target_info:
            # 如果源是文件夹，检查是否有子路径（文件夹内有内容）
            if source_info.is_dir:
                has_children_in_source = any(
                    p.startswith(path + '/') or p.startswith(path + '\\')
                    for p in source_files.keys() if p != path
                )
                # 如果源文件夹有内容，忽略文件夹本身（只同步其内部的内容）
                if has_children_in_source:
                    if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                        progress_callback(processed, total)
                        last_progress_update = processed
                    continue
                
                # 检查目标端是否有同名文件夹的内容
                has_children_in_target = any(
                    p.startswith(path + '/') or p.startswith(path + '\\')
                    for p in target_files.keys()
                )
                # 如果目标端有同名文件夹的内容
                if has_children_in_target:
                    # 在差异同步模式下忽略源空文件夹（保留目标内容）
                    # 在覆盖同步模式下也忽略源空文件夹（删除目标内容后，目标文件夹自然变成空文件夹）
                    if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                        progress_callback(processed, total)
                        last_progress_update = processed
                    continue
            
            # 显示为源独有，状态显示"同步至目标"
            results.append(DiffResult(
                relative_path=path,
                status=FileStatus.WINTOGO_ONLY if source_is_wintogo else FileStatus.LOCAL_ONLY,
                wintogo_info=source_info if source_is_wintogo else None,
                local_info=source_info if not source_is_wintogo else None
            ))
        # 源不存在，目标存在 - 目标独有项目
        elif not source_info and target_info:
            # 如果目标是文件夹，检查是否有子路径（文件夹内有内容）
            if target_info.is_dir:
                has_children_in_target = any(
                    p.startswith(path + '/') or p.startswith(path + '\\')
                    for p in target_files.keys() if p != path
                )
                # 如果目标文件夹有内容
                if has_children_in_target:
                    # 检查源端是否有同名文件夹的内容
                    has_children_in_source = any(
                        p.startswith(path + '/') or p.startswith(path + '\\')
                        for p in source_files.keys()
                    )
                    # 如果源端有同名文件夹的内容
                    if has_children_in_source:
                        # 在差异同步模式下忽略目标文件夹（保留源内容）
                        # 在覆盖同步模式下也忽略目标文件夹（源内容同步后，目标文件夹自然有内容）
                        if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                            progress_callback(processed, total)
                            last_progress_update = processed
                        continue
            
            # 根据 extra_items_mode 处理目标独有项目
            if extra_items_mode == "keep":
                # "保留多余项目"模式：忽略目标多余项目
                if progress_callback and (processed - last_progress_update >= progress_interval or processed == total):
                    progress_callback(processed, total)
                    last_progress_update = processed
                continue
            else:  # extra_items_mode == "delete"
                # "删除多余项目"模式：显示为目标独有，列表标记为红色，状态显示"将被删除"
                results.append(DiffResult(
                    relative_path=path,
                    status=FileStatus.LOCAL_ONLY if source_is_wintogo else FileStatus.WINTOGO_ONLY,
                    wintogo_info=target_info if not source_is_wintogo else None,
                    local_info=target_info if source_is_wintogo else None
                ))
        # 双方都存在
        else:
            if source_info.is_dir != target_info.is_dir:
                # 类型冲突，需要同步源到目标
                results.append(DiffResult(
                    relative_path=path,
                    status=FileStatus.CONFLICT,
                    wintogo_info=source_info if source_is_wintogo else target_info,
                    local_info=target_info if source_is_wintogo else source_info
                ))
            elif source_info.is_dir and target_info.is_dir:
                # 两端都是目录
                # 对于空目录，忽略时间戳差异，直接标记为SAME
                # 因为空目录本身没有内容，时间戳不影响其功能
                results.append(DiffResult(
                    relative_path=path,
                    status=FileStatus.SAME,
                    wintogo_info=source_info if source_is_wintogo else target_info,
                    local_info=target_info if source_is_wintogo else source_info
                ))
            elif source_info.size != target_info.size:
                # 大小不同
                if unidirectional_mode == "diff":
                    # 差异同步模式：检查时间戳，若目标新于源，则忽略此项目
                    if source_info.mtime > target_info.mtime:
                        # 源新于目标，显示为差异项，状态显示"覆盖目标"
                        results.append(DiffResult(
                            relative_path=path,
                            status=FileStatus.CONFLICT,
                            wintogo_info=source_info if source_is_wintogo else target_info,
                            local_info=target_info if source_is_wintogo else source_info
                        ))
                    else:
                        # 目标新于源，忽略此项目（不添加到结果列表）
                        pass
                else:  # unidirectional_mode == "overwrite"
                    # 覆盖同步模式：无视新旧，始终源覆盖目标
                    results.append(DiffResult(
                        relative_path=path,
                        status=FileStatus.CONFLICT,
                        wintogo_info=source_info if source_is_wintogo else target_info,
                        local_info=target_info if source_is_wintogo else source_info
                    ))
            else:
                # 大小相同，检查时间戳
                if abs(source_info.mtime - target_info.mtime) > MTIME_TOLERANCE:
                    # 时间戳不同
                    if unidirectional_mode == "diff":
                        # 差异同步模式：若源新于目标，则覆盖目标；若目标新于源，则忽略此项目
                        if source_info.mtime > target_info.mtime:
                            # 源新于目标，显示为差异项，状态显示"覆盖目标"
                            results.append(DiffResult(
                                relative_path=path,
                                status=FileStatus.MTIME_DIFF,
                                wintogo_info=source_info if source_is_wintogo else target_info,
                                local_info=target_info if source_is_wintogo else source_info
                            ))
                        else:
                            # 目标新于源，忽略此项目（不添加到结果列表）
                            pass
                    else:  # unidirectional_mode == "overwrite"
                        # 覆盖同步模式：无视新旧，始终源覆盖目标
                        results.append(DiffResult(
                            relative_path=path,
                            status=FileStatus.MTIME_DIFF,
                            wintogo_info=source_info if source_is_wintogo else target_info,
                            local_info=target_info if source_is_wintogo else source_info
                        ))
                else:
                    # 时间戳相近，用哈希校验内容是否真正一致，避免同尺寸不同内容被误判为相同
                    if _content_matches(
                        os.path.join(source_dir, path),
                        os.path.join(target_dir, path),
                        source_info.size
                    ):
                        results.append(DiffResult(
                            relative_path=path,
                            status=FileStatus.SAME,
                            wintogo_info=source_info if source_is_wintogo else target_info,
                            local_info=target_info if source_is_wintogo else source_info
                        ))
                    else:
                        results.append(DiffResult(
                            relative_path=path,
                            status=FileStatus.MTIME_DIFF,
                            wintogo_info=source_info if source_is_wintogo else target_info,
                            local_info=target_info if source_is_wintogo else source_info
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


def delete_file(file_path: str, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    try:
        # 注意：不能用 os.path.exists 前置判断，Windows 上权限不足时 exists 可能返回 False
        # 始终尝试 os.remove，FileNotFoundError 说明文件已不存在，视为成功
        
        # Windows: 先移除 READONLY / SYSTEM / HIDDEN 等可能阻止删除的属性
        if sys.platform == 'win32':
            try:
                attrs = get_file_attributes(file_path)
                # 仅当 GetFileAttributesW 返回有效值时尝试修改属性
                if attrs != -1:
                    REMOVE_MASK = FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_HIDDEN
                    if attrs & REMOVE_MASK:
                        set_file_attributes(file_path, attrs & ~REMOVE_MASK)
            except Exception:
                pass

        for attempt in range(max_retries):
            try:
                os.remove(file_path)
                break
            except FileNotFoundError:
                # 文件已不存在，视为成功
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

        # 不在删除文件后尝试删除父目录
        # 空目录的删除应该在同步完成后统一处理
        return True
    except (OSError, PermissionError) as e:
        print(f"Error deleting {file_path}: {e}")
        return False


def _remove_empty_path_chain(path: str) -> int:
    """
    从给定路径开始，向上递归尝试删除空目录。
    删除成功后继续尝试删除父目录，直到目录非空或到达顶级。

    Args:
        path: 要删除的目录路径

    Returns:
        成功删除的目录数量
    """
    total = 0
    current = os.path.normpath(path)
    while True:
        try:
            os.rmdir(current)
            total += 1
            print(f"Removed empty directory: {current}")
        except OSError:
            # 目录非空、权限不足或不存在 → 停止向上清理
            break
        parent = os.path.dirname(current)
        # 如果已经到达驱动器根目录或上级不变，停止
        if parent == current:
            break
        current = parent
    return total


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
    
    # 写入临时文件，成功后原子重命名为目标文件，避免复制失败时残留部分内容破坏原有目标
    temp_path = dest_path + ".sync_tmp"
    
    for attempt in range(max_retries):
        if sys.platform == 'win32' and progress_callback:
            result = _copy_file_win32(source_path, temp_path, progress_callback)
        else:
            result = _copy_file_fallback(source_path, temp_path, progress_callback, chunk_size)
        
        if result:
            try:
                os.replace(temp_path, dest_path)
            except OSError as e:
                print(f"Error replacing {temp_path} to {dest_path}: {e}")
                _safe_remove(temp_path)
                return False
            if sys.platform == 'win32':
                sync_file_attributes(source_path, dest_path)
            return True
        
        if attempt < max_retries - 1:
            if is_file_locked(source_path) or is_file_locked(dest_path):
                print(f"File locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                break
    
    # 所有重试失败：清理临时文件，避免残留
    _safe_remove(temp_path)
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
        if sys.platform == 'win32':
            sync_file_attributes(source_path, dest_path)
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
                        rmtree_safe(wintogo_path)
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
                        rmtree_safe(local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting symlink {local_path}: {e}")
                    return False
        elif diff.status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
            if direction == "wintogo_to_local":
                try:
                    if os.path.exists(local_path) or os.path.islink(local_path):
                        os.remove(local_path)
                    if diff.wintogo_info and diff.wintogo_info.symlink_target:
                        os.symlink(diff.wintogo_info.symlink_target, local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error syncing symlink from WinToGo to local: {e}")
                    return False
            elif direction == "local_to_wintogo":
                try:
                    if os.path.exists(wintogo_path) or os.path.islink(wintogo_path):
                        os.remove(wintogo_path)
                    if diff.local_info and diff.local_info.symlink_target:
                        os.symlink(diff.local_info.symlink_target, wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error syncing symlink from local to WinToGo: {e}")
                    return False
            elif direction == "delete_both":
                try:
                    if os.path.islink(wintogo_path) or os.path.exists(wintogo_path):
                        os.remove(wintogo_path) if os.path.islink(wintogo_path) else rmtree_safe(wintogo_path)
                    if os.path.islink(local_path) or os.path.exists(local_path):
                        os.remove(local_path) if os.path.islink(local_path) else rmtree_safe(local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting symlinks: {e}")
                    return False
        return True
    
    is_dir = False
    is_dir_conflict = False
    if diff.wintogo_info and diff.wintogo_info.is_dir:
        is_dir = True
    elif diff.local_info and diff.local_info.is_dir:
        is_dir = True
    
    if diff.status == FileStatus.CONFLICT:
        if diff.wintogo_info and diff.local_info:
            if diff.wintogo_info.is_dir != diff.local_info.is_dir:
                is_dir_conflict = True
    
    if is_dir_conflict:
        if direction == "wintogo_to_local":
            try:
                if diff.wintogo_info.is_dir:
                    if os.path.isfile(local_path):
                        os.remove(local_path)
                    elif os.path.isdir(local_path):
                        rmtree_safe(local_path)
                    os.makedirs(local_path, exist_ok=True)
                    sync_dir_attributes(wintogo_path, local_path)
                else:
                    if os.path.isdir(local_path):
                        rmtree_safe(local_path)
                    return copy_file_with_progress(wintogo_path, local_path, progress_callback)
                return True
            except (OSError, PermissionError) as e:
                print(f"Error resolving directory/file conflict: {e}")
                return False
        elif direction == "local_to_wintogo":
            try:
                if diff.local_info.is_dir:
                    if os.path.isfile(wintogo_path):
                        os.remove(wintogo_path)
                    elif os.path.isdir(wintogo_path):
                        rmtree_safe(wintogo_path)
                    os.makedirs(wintogo_path, exist_ok=True)
                    sync_dir_attributes(local_path, wintogo_path)
                else:
                    if os.path.isdir(wintogo_path):
                        rmtree_safe(wintogo_path)
                    return copy_file_with_progress(local_path, wintogo_path, progress_callback)
                return True
            except (OSError, PermissionError) as e:
                print(f"Error resolving directory/file conflict: {e}")
                return False
        elif direction == "delete_both":
            try:
                if os.path.isdir(wintogo_path):
                    rmtree_safe(wintogo_path)
                elif os.path.isfile(wintogo_path):
                    os.remove(wintogo_path)
                if os.path.isdir(local_path):
                    rmtree_safe(local_path)
                elif os.path.isfile(local_path):
                    os.remove(local_path)
                return True
            except (OSError, PermissionError) as e:
                print(f"Error deleting directory/file conflict: {e}")
                return False
        return True
    
    if is_dir:
        if diff.status == FileStatus.WINTOGO_ONLY:
            if direction == "to_local":
                try:
                    os.makedirs(local_path, exist_ok=True)
                    sync_dir_attributes(wintogo_path, local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error creating directory {local_path}: {e}")
                    return False
            elif direction == "delete_wintogo":
                try:
                    rmtree_safe(wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting directory {wintogo_path}: {e}")
                    return False
        elif diff.status == FileStatus.LOCAL_ONLY:
            if direction == "to_wintogo":
                try:
                    os.makedirs(wintogo_path, exist_ok=True)
                    sync_dir_attributes(local_path, wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error creating directory {wintogo_path}: {e}")
                    return False
            elif direction == "delete_local":
                try:
                    rmtree_safe(local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting directory {local_path}: {e}")
                    return False
            elif direction == "delete_wintogo":
                try:
                    rmtree_safe(wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error deleting directory {wintogo_path}: {e}")
                    return False
        elif diff.status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
            if direction == "wintogo_to_local":
                try:
                    sync_dir_attributes(wintogo_path, local_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error copying directory attributes from {wintogo_path} to {local_path}: {e}")
                    return False
            elif direction == "local_to_wintogo":
                try:
                    sync_dir_attributes(local_path, wintogo_path)
                    return True
                except (OSError, PermissionError) as e:
                    print(f"Error copying directory attributes from {local_path} to {wintogo_path}: {e}")
                    return False
            elif direction == "delete_both":
                try:
                    if os.path.isdir(wintogo_path):
                        rmtree_safe(wintogo_path)
                    if os.path.isdir(local_path):
                        rmtree_safe(local_path)
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
        elif direction == "delete_wintogo":
            return delete_file(wintogo_path)
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