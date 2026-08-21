"""
SyncGUI - 本地与移动介质双向文件同步工具

Author: Lisselde_E
GitHub: https://github.com/LisseldeE
License: MIT
Copyright (c) 2026 Lisselde_E.
"""

import sys
import os
import json
import time
import ssl
from datetime import datetime
from collections import defaultdict
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QProgressBar, QMessageBox, QHeaderView,
    QDialog, QDialogButtonBox, QGroupBox, QRadioButton, QButtonGroup,
    QFrame, QSizePolicy, QCheckBox, QListWidget, QListWidgetItem,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPoint, QPropertyAnimation, QByteArray
from PySide6.QtGui import QColor, QFont, QPalette

from sync_core import (
    scan_directory, compare_files, compare_files_unidirectional, sync_file,
    rmtree_safe, _remove_empty_path_chain, FileStatus, DiffResult
)
from i18n import I18n
from config import Config


class AnimatedButton(QPushButton):
    """
    带动画效果的按钮类
    - 点击时有按下效果（向下移动1px）
    """
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        # 原始位置
        self.original_pos = None
        
        # 点击动画标记
        self.is_pressed = False
        
    def mousePressEvent(self, event):
        """鼠标按下事件 - 触发点击动画"""
        # 每次点击前都更新位置，应对布局变化（如语言切换）
        self.original_pos = self.pos()
        
        self.is_pressed = True
        # 向下移动1px，模拟按下效果
        self.move(QPoint(self.original_pos.x(), self.original_pos.y() + 1))
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 恢复位置"""
        self.is_pressed = False
        # 恢复到原始位置
        if self.original_pos is not None:
            self.move(self.original_pos)
        super().mouseReleaseEvent(event)


class ClickableLabel(QLabel):
    """
    可点击的标签类（原始实现 - 不控制样式）
    - 鼠标悬停时显示手型光标
    - 点击时发出clicked信号
    """
    clicked = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """鼠标进入事件 - 显示手型光标"""
        self.setCursor(Qt.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件 - 恢复默认光标"""
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)


def get_config_dir():
    """获取配置文件保存目录（用户目录/SyncGUI）"""
    # 获取用户目录
    config_dir = os.path.join(os.path.expanduser('~'), 'SyncGUI')
    
    # 确保目录存在
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except:
            pass
    
    return config_dir


CONFIG_FILE = os.path.join(get_config_dir(), 'config.json')


def _is_dark_mode():
    """自动检测 Windows 系统深色模式（参考 pyside6-AltRowStyle.md）"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0  # 0 = 深色, 1 = 浅色
    except Exception:
        return False


# 禁用态按钮样式：深色模式用深灰背景，浅色模式用老版本灰色填充
_DISABLED_BTN_QSS = (
    "background-color: #2d2d2d;\n"
    "    color: #adb5bd;\n"
    "    border: 1px solid rgba(255, 255, 255, 0.2);"
) if _is_dark_mode() else (
    "background-color: #adb5bd;\n"
    "    color: #f8f9fa;\n"
    "    border: none;"
)

# 按钮悬浮背景色：深色模式用深灰，浅色模式用浅灰
_HOVER_BG = "#3a3a3a" if _is_dark_mode() else "#f1f3f5"


STYLESHEET = """
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}
QLineEdit {
    padding: 10px 12px;
    border: 1px solid #ced4da;
    border-radius: 6px;
    font-size: 13px;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
QLineEdit:focus {
    border: 2px solid #4dabf7;
}
QPushButton {
    padding: 10px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    border: 1px solid #ced4da;
}
QPushButton:hover {
    background-color: __HOVER_BG__;
    border: 1px solid #adb5bd;
}
QPushButton#browseBtn:disabled {
    __DISABLED__
}
QPushButton#scanBtn {
    background-color: #339af0;
    color: white;
    border: none;
}
QPushButton#scanBtn:hover {
    background-color: #228be6;
}
QPushButton#scanBtn:disabled {
    __DISABLED__
}
QPushButton#aboutBtn {
    color: #339af0;
    border: 1px solid #ced4da;
    border-radius: 16px;
    font-size: 16px;
    font-weight: bold;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    padding: 0;
}
QPushButton#aboutBtn:hover {
    background-color: __HOVER_BG__;
    color: #228be6;
    border: 1px solid #adb5bd;
}
QPushButton#aboutBtn:disabled {
    __DISABLED__
}
QPushButton:disabled {
    __DISABLED__
}
QPushButton#syncBtn {
    background-color: #51cf66;
    color: white;
    border: none;
}
QPushButton#syncBtn:hover {
    background-color: #40c057;
}
QPushButton#syncBtn:disabled {
    __DISABLED__
}
QProgressBar {
    border: none;
    border-radius: 6px;
    text-align: center;
    font-weight: 500;
}
QProgressBar::chunk {
    background-color: #339af0;
    border-radius: 6px;
}
QMessageBox QLabel {
    font-size: 13px;
}
QMessageBox QPushButton {
    padding: 8px 24px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    min-width: 80px;
}
QMessageBox QPushButton[text="确定"],
QMessageBox QPushButton[text="是"],
QMessageBox QPushButton[text="Yes"],
QMessageBox QPushButton[text="OK"],
QMessageBox QPushButton[text="Ok"],
QMessageBox QPushButton[text="完成"] {
    background-color: #40c057;
    color: white;
    border: none;
}
QMessageBox QPushButton[text="确定"]:hover,
QMessageBox QPushButton[text="是"]:hover,
QMessageBox QPushButton[text="Yes"]:hover,
QMessageBox QPushButton[text="OK"]:hover,
QMessageBox QPushButton[text="Ok"]:hover,
QMessageBox QPushButton[text="完成"]:hover {
    background-color: #37b24d;
}
QMessageBox QPushButton[text="取消"],
QMessageBox QPushButton[text="否"],
QMessageBox QPushButton[text="No"],
QMessageBox QPushButton[text="Cancel"] {
    background-color: #fa5252;
    color: white;
    border: none;
}
QMessageBox QPushButton[text="取消"]:hover,
QMessageBox QPushButton[text="否"]:hover,
QMessageBox QPushButton[text="No"]:hover,
QMessageBox QPushButton[text="Cancel"]:hover {
    background-color: #f03e3e;
}
""".replace("__DISABLED__", _DISABLED_BTN_QSS).replace("__HOVER_BG__", _HOVER_BG)


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(config):
    try:
        # 确保配置目录存在
        config_dir = get_config_dir()
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass


class ScanWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(dict, dict)
    
    def __init__(self, wintogo_dir: str, local_dir: str, ignore_rules: list = None):
        super().__init__()
        self.wintogo_dir = wintogo_dir
        self.local_dir = local_dir
        self.ignore_rules = ignore_rules or []
    
    def run(self):
        wintogo_files = scan_directory(self.wintogo_dir, self._progress_callback, self.ignore_rules)
        local_files = scan_directory(self.local_dir, self._progress_callback, self.ignore_rules)
        self.finished.emit(wintogo_files, local_files)
    
    def _progress_callback(self, current: int, total: int):
        self.progress.emit(current, total)


class CompareWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(list)
    
    def __init__(self, wintogo_files: dict, local_files: dict, 
                 wintogo_dir: str, local_dir: str,
                 sync_type: str = "bidirectional",
                 unidirectional_mode: str = "diff",
                 sync_direction: str = "removable_to_local",
                 extra_items_mode: str = "keep"):
        super().__init__()
        self.wintogo_files = wintogo_files
        self.local_files = local_files
        self.wintogo_dir = wintogo_dir
        self.local_dir = local_dir
        self.sync_type = sync_type
        self.unidirectional_mode = unidirectional_mode
        self.sync_direction = sync_direction
        self.extra_items_mode = extra_items_mode
    
    def run(self):
        if self.sync_type == "unidirectional":
            # 单向同步
            if self.sync_direction == "removable_to_local":
                # 介质 → 本地
                source_files = self.wintogo_files
                target_files = self.local_files
                source_dir = self.wintogo_dir
                target_dir = self.local_dir
            else:
                # 本地 → 介质
                source_files = self.local_files
                target_files = self.wintogo_files
                source_dir = self.local_dir
                target_dir = self.wintogo_dir
            
            results = compare_files_unidirectional(
                source_files, target_files,
                source_dir, target_dir,
                self.unidirectional_mode,
                self.extra_items_mode,  # 新增参数：多余项目处理模式
                self._progress_callback,
                100,  # progress_interval
                self.wintogo_dir  # wintogo_dir: 介质目录路径，用于正确设置状态
            )
        else:
            # 双向同步
            results = compare_files(
                self.wintogo_files, self.local_files,
                self.wintogo_dir, self.local_dir,
                self._progress_callback
            )
        self.finished.emit(results)
    
    def _progress_callback(self, current: int, total: int):
        self.progress.emit(current, total)


class SyncWorker(QThread):
    progress = Signal(object, object, object, object, str)
    finished = Signal(int, int, int)
    
    def __init__(self, diff_results: list, conflict_decisions: dict,
                 wintogo_dir: str, local_dir: str):
        super().__init__()
        self.diff_results = diff_results
        self.conflict_decisions = conflict_decisions
        self.wintogo_dir = wintogo_dir
        self.local_dir = local_dir
    
    def run(self):
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        to_sync = [d for d in self.diff_results if d.status != FileStatus.SAME]

        # 对删除操作进行排序：按路径深度排序（父目录优先）
        # 这样可以确保在删除文件夹时，如果父目录已被删除，则跳过子内容的删除
        delete_items = []
        other_items = []

        for diff in to_sync:
            decision = self.conflict_decisions.get(diff.relative_path, "skip")
            if decision.startswith("delete_"):
                delete_items.append(diff)
            else:
                other_items.append(diff)

        # 对删除项目按路径深度排序（浅层路径优先，这样父目录会先被删除）
        # 注意：Windows 路径使用反斜杠，统一用 os.sep 确保跨平台正确
        delete_items.sort(key=lambda d: d.relative_path.count(os.sep), reverse=False)

        # 合并列表：删除操作优先
        to_sync = delete_items + other_items

        # 记录已删除的路径，用于跳过子路径的删除
        deleted_paths = set()

        total_bytes = 0
        for diff in to_sync:
            if diff.wintogo_info:
                total_bytes += diff.wintogo_info.size
            elif diff.local_info:
                total_bytes += diff.local_info.size

        transferred_bytes = 0

        for idx, diff in enumerate(to_sync):
            file_size = 0
            if diff.wintogo_info:
                file_size = diff.wintogo_info.size
            elif diff.local_info:
                file_size = diff.local_info.size

            decision = self.conflict_decisions.get(diff.relative_path, "skip")

            # 检查是否是删除操作，且父路径已经被删除
            if decision.startswith("delete_"):
                # 检查是否有父路径已经被删除
                # 跨平台：用 os.sep 分割路径（Windows 用 \，Linux/Unix 用 /）
                path_parts = diff.relative_path.split(os.sep)
                parent_deleted = False
                for i in range(len(path_parts) - 1):
                    parent_path = os.sep.join(path_parts[:i+1])
                    if parent_path in deleted_paths:
                        parent_deleted = True
                        break
                
                if parent_deleted:
                    # 父路径已经被删除，跳过此路径的删除
                    skip_count += 1
                    self.progress.emit(transferred_bytes, total_bytes, 0, file_size, diff.relative_path)
                    continue
            
            if decision == "skip":
                skip_count += 1
                self.progress.emit(transferred_bytes, total_bytes, 0, file_size, diff.relative_path)
                continue
            
            start_bytes = transferred_bytes
            current_total_bytes = total_bytes
            current_filename = diff.relative_path
            
            def progress_callback(copied: int, file_total: int, start=start_bytes, total_b=current_total_bytes, name=current_filename):
                self.progress.emit(start + copied, total_b, copied, file_total, name)
            
            if sync_file(diff, self.wintogo_dir, self.local_dir, decision, progress_callback):
                success_count += 1
                transferred_bytes += file_size
                # 记录已删除的路径
                if decision.startswith("delete_"):
                    deleted_paths.add(diff.relative_path)
            else:
                fail_count += 1
                transferred_bytes += file_size
        
        self.finished.emit(success_count, fail_count, skip_count)


class FadeDialog(QDialog):
    """对话框基类（使用默认系统窗口控制）。"""


# ============================================================
# 手动选择翻页式向导（SlideContainer + DiffPage + ManualSyncWizard）
# 替代逐个弹窗的 ConflictDialog / OnlyOneSideDialog / MtimeDiffDialog
# ============================================================

class DiffPage(QWidget):
    """单个 diff 的内容页面（不含底部按钮，由 ManualSyncWizard 提供固定按钮区）。"""

    def __init__(self, diff: DiffResult, same_dir_count: int, lang: str,
                 removable_name: str, local_name: str, parent=None):
        super().__init__(parent)
        self.diff = diff
        self.same_dir_count = same_dir_count
        self.lang = lang
        self.removable_name = removable_name
        self.local_name = local_name
        self.wintogo_newer = None  # 仅 CONFLICT / MTIME_DIFF 有效
        self._dark = _is_dark_mode()
        self._build_ui()

    # ---- 颜色辅助 ----

    def _muted_color(self):
        """次要文字颜色（深色模式下用浅灰）。"""
        return "#adb5bd" if self._dark else "#495057"

    def _hint_color(self):
        """提示文字颜色。"""
        return "#ced4da" if self._dark else "#868e96"

    def _hline_color(self):
        return "#3a3a3a" if self._dark else "#e9ecef"

    def _box_border(self):
        return "#3a3a3a" if self._dark else "#dee2e6"

    # ---- UI 构建 ----

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(28, 16, 28, 12)

        status = self.diff.status

        # ---- Full-width title ----
        self._build_title(layout, status)

        layout.addWidget(self._hline())

        # ---- Content area: left (info) | right (options) ----
        content = QHBoxLayout()
        content.setSpacing(20)

        # == Left: Info panel (file path / time boxes / hints) ==
        info_panel = QVBoxLayout()
        info_panel.setSpacing(10)
        self._build_info_side(info_panel, status)

        # == Vertical separator ==
        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFixedWidth(1)
        vline.setStyleSheet(f"QFrame {{ background-color: {self._hline_color()}; border: none; }}")

        # == Right: Options panel (choice label / radio buttons / apply checkbox) ==
        options_panel = QVBoxLayout()
        options_panel.setSpacing(8)
        self._build_options_side(options_panel, status)

        content.addLayout(info_panel, 3)
        content.addWidget(vline)
        content.addLayout(options_panel, 2)

        layout.addLayout(content)

    def _build_title(self, layout, status):
        """构建全宽标题。"""
        if status == FileStatus.CONFLICT:
            self.wintogo_newer = self.diff.wintogo_info.mtime > self.diff.local_info.mtime
            title = QLabel(I18n.tr("conflict_title", self.lang))
            title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e03131;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
        elif status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY):
            is_wintogo_only = status == FileStatus.WINTOGO_ONLY
            side_name = I18n.tr("removable_time", self.lang) if is_wintogo_only else I18n.tr("local_time", self.lang)
            title = QLabel(I18n.tr("diff_title", self.lang) + f" ({side_name})")
            title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1971c2;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
        elif status == FileStatus.MTIME_DIFF:
            self.wintogo_newer = self.diff.wintogo_info.mtime > self.diff.local_info.mtime
            title = QLabel(I18n.tr("mtime_title", self.lang))
            title.setStyleSheet("font-size: 18px; font-weight: bold; color: #fd7e14;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

    def _build_info_side(self, panel, status):
        """左侧信息区域：文件路径 / 时间对比 / 提示。"""
        panel.addWidget(self._file_label())

        if status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
            panel.addWidget(self._time_boxes())

            if status == FileStatus.MTIME_DIFF:
                hint_text = (self.lang == "zh" and "文件大小相同，但修改时间不同"
                             or "Same size, but different modification time")
                hint0 = QLabel(hint_text)
                hint0.setStyleSheet(f"color: {self._hint_color()}; font-size: 12px;")
                hint0.setAlignment(Qt.AlignCenter)
                panel.addWidget(hint0)

            newer_side = (I18n.tr("removable_time", self.lang)
                          if self.wintogo_newer else I18n.tr("local_time", self.lang))
            hint = QLabel(I18n.tr("newer_hint", self.lang, side=newer_side))
            hint.setStyleSheet("color: #fd7e14; font-size: 13px;")
            hint.setAlignment(Qt.AlignCenter)
            panel.addWidget(hint)

        else:  # WINTOGO_ONLY / LOCAL_ONLY
            is_wintogo_only = status == FileStatus.WINTOGO_ONLY
            info = self.diff.wintogo_info if is_wintogo_only else self.diff.local_info
            if info:
                size_str = self._format_size(info.size)
                mtime_str = datetime.fromtimestamp(info.mtime).strftime('%Y-%m-%d %H:%M:%S')
                size_text = self.lang == "zh" and "大小" or "Size"
                mtime_text = self.lang == "zh" and "修改时间" or "Modified"
                info_lbl = QLabel(f"{size_text}: {size_str}  |  {mtime_text}: {mtime_str}")
                info_lbl.setStyleSheet(f"color: {self._hint_color()}; font-size: 12px;")
                info_lbl.setAlignment(Qt.AlignCenter)
                panel.addWidget(info_lbl)

        panel.addStretch()

    def _build_options_side(self, panel, status):
        """右侧操作区域：选择标签 / 单选按钮 / 应用到同目录。"""
        panel.addWidget(self._choice_label())

        self.button_group = QButtonGroup(self)

        if status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
            newer_side = (I18n.tr("removable_time", self.lang)
                          if self.wintogo_newer else I18n.tr("local_time", self.lang))
            older_side = (I18n.tr("local_time", self.lang)
                          if self.wintogo_newer else I18n.tr("removable_time", self.lang))

            if status == FileStatus.CONFLICT:
                self.rb_newer = QRadioButton(I18n.tr("keep_newest", self.lang, side=newer_side))
                self.rb_older = QRadioButton(I18n.tr("keep_older", self.lang, side=older_side))
            else:
                newer_text = (self.lang == "zh"
                              and f"✨ 用{newer_side}（较新）覆盖{older_side}"
                              or f"✨ Use {newer_side} (newer) to overwrite")
                older_text = (self.lang == "zh"
                              and f"📥 用{older_side}（较旧）覆盖{newer_side}"
                              or f"📥 Use {older_side} (older) to overwrite")
                self.rb_newer = QRadioButton(newer_text)
                self.rb_older = QRadioButton(older_text)

            self.rb_delete_both = QRadioButton(
                self.lang == "zh" and "🗑️ 双端删除此项目" or "🗑️ Delete from both sides")
            self.rb_newer.setChecked(True)

            self.button_group.addButton(self.rb_newer, 0)
            self.button_group.addButton(self.rb_older, 1)
            self.button_group.addButton(self.rb_delete_both, 2)
            for rb in (self.rb_newer, self.rb_older, self.rb_delete_both):
                panel.addWidget(rb)

        else:  # WINTOGO_ONLY / LOCAL_ONLY
            is_wintogo_only = status == FileStatus.WINTOGO_ONLY
            side_name = (I18n.tr("removable_time", self.lang)
                         if is_wintogo_only else I18n.tr("local_time", self.lang))

            # 名称前缀裁剪
            removable_prefix = self.removable_name
            if removable_prefix.endswith("目录"):
                removable_prefix = removable_prefix[:-2]
            elif removable_prefix.endswith("Directory"):
                removable_prefix = removable_prefix[:-9]
            local_prefix = self.local_name
            if local_prefix.endswith("目录"):
                local_prefix = local_prefix[:-2]
            elif local_prefix.endswith("Directory"):
                local_prefix = local_prefix[:-9]

            if is_wintogo_only:
                copy_text = (self.lang == "zh"
                             and f"➡️ {removable_prefix} → {local_prefix}（补充{local_prefix}缺失的文件）"
                             or f"➡️ {removable_prefix} → {local_prefix}")
            else:
                copy_text = (self.lang == "zh"
                             and f"➡️ {local_prefix} → {removable_prefix}（补充{removable_prefix}缺失的文件）"
                             or f"➡️ {local_prefix} → {removable_prefix}")

            delete_text = (self.lang == "zh"
                           and f"🗑️ 删除此文件（移除{side_name}多余的文件）"
                           or "🗑️ Delete this file")
            self.rb_copy = QRadioButton(copy_text)
            self.rb_delete = QRadioButton(delete_text)
            self.rb_copy.setChecked(True)

            self.button_group.addButton(self.rb_copy, 0)
            self.button_group.addButton(self.rb_delete, 1)
            for rb in (self.rb_copy, self.rb_delete):
                panel.addWidget(rb)

        self._add_apply_dir_check(panel)
        panel.addStretch()

    def _hline(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"QFrame {{ background-color: {self._hline_color()}; border: none; }}")
        return line

    def _file_label(self):
        lbl = QLabel(I18n.tr("file_label", self.lang, path=self.diff.relative_path))
        lbl.setStyleSheet(f"font-size: 13px; padding: 8px 4px; border: none;")
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setWordWrap(True)
        return lbl

    def _time_boxes(self):
        """构建两端时间对比框（CONFLICT / MTIME_DIFF 共用）。"""
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(12)

        w_time = datetime.fromtimestamp(self.diff.wintogo_info.mtime).strftime('%Y-%m-%d %H:%M:%S')
        l_time = datetime.fromtimestamp(self.diff.local_info.mtime).strftime('%Y-%m-%d %H:%M:%S')

        border = self._box_border()
        muted = self._muted_color()

        w_box = QFrame()
        w_box.setStyleSheet(f"QFrame {{ border: none; padding: 6px 0; }}")
        w_lay = QVBoxLayout(w_box)
        w_lay.setSpacing(2)
        w_lay.setContentsMargins(0, 0, 0, 0)
        w_title = QLabel(I18n.tr("removable_time", self.lang))
        w_title.setStyleSheet("font-weight: bold; color: #1971c2; font-size: 13px;")
        w_title.setAlignment(Qt.AlignCenter)
        w_time_lbl = QLabel(w_time)
        w_time_lbl.setStyleSheet(f"color: {muted}; font-size: 12px;")
        w_time_lbl.setAlignment(Qt.AlignCenter)
        w_lay.addWidget(w_title)
        w_lay.addWidget(w_time_lbl)

        l_box = QFrame()
        l_box.setStyleSheet(f"QFrame {{ border: none; padding: 6px 0; }}")
        l_lay = QVBoxLayout(l_box)
        l_lay.setSpacing(2)
        l_title = QLabel(I18n.tr("local_time", self.lang))
        l_title.setStyleSheet("font-weight: bold; color: #2f9e44; font-size: 13px;")
        l_title.setAlignment(Qt.AlignCenter)
        l_time_lbl = QLabel(l_time)
        l_time_lbl.setStyleSheet(f"color: {muted}; font-size: 12px;")
        l_time_lbl.setAlignment(Qt.AlignCenter)
        l_lay.addWidget(l_title)
        l_lay.addWidget(l_time_lbl)

        lay.addWidget(w_box)
        lay.addWidget(l_box)
        return widget

    def _choice_label(self):
        lbl = QLabel(I18n.tr("choice_label", self.lang))
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        return lbl

    def _add_apply_dir_check(self, layout):
        if self.same_dir_count > 0:
            self.apply_dir_check = QCheckBox(I18n.tr("apply_dir_files", self.lang, count=self.same_dir_count))
            self.apply_dir_check.setStyleSheet("color: #1971c2; font-weight: 500;")
            self.apply_dir_check.setChecked(True)
            layout.addWidget(self.apply_dir_check)

    # _build_conflict / _build_only_one_side / _build_mtime_diff 已被
    # _build_title + _build_info_side + _build_options_side 取代

    # ---- 结果获取 ----

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def get_direction(self):
        checked_id = self.button_group.checkedId()
        status = self.diff.status

        if status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
            if checked_id == 0:
                return "wintogo_to_local" if self.wintogo_newer else "local_to_wintogo"
            elif checked_id == 1:
                return "local_to_wintogo" if self.wintogo_newer else "wintogo_to_local"
            elif checked_id == 2:
                return "delete_both"
            else:
                return "skip"
        else:  # WINTOGO_ONLY / LOCAL_ONLY
            is_wintogo_only = status == FileStatus.WINTOGO_ONLY
            if checked_id == 0:
                return "to_local" if is_wintogo_only else "to_wintogo"
            elif checked_id == 1:
                return "delete_wintogo" if is_wintogo_only else "delete_local"
            else:
                return "skip"

    def should_apply_to_dir(self):
        if self.same_dir_count > 0 and hasattr(self, 'apply_dir_check'):
            return self.apply_dir_check.isChecked()
        return False


class ManualSyncWizard(FadeDialog):
    """手动选择模式翻页式向导。

    固定窗口，内容区由右向左滑动切换，底部按钮固定。
    支持上一个 / 确认 / 跳过 / 取消同步。
    勾选"应用到同目录"时批量决策同目录同状态的其他 diff，并自动跳过。
    """

    SLIDE_DURATION = 200  # 毫秒

    def __init__(self, diffs, same_dir_counts, lang, removable_name, local_name, parent=None):
        # 在 super().__init__ 前预初始化，因为 resizeEvent 可能在这些属性之前触发
        self._current_page = None
        self._sliding = False
        super().__init__(parent)
        self.lang = lang
        self.removable_name = removable_name
        self.local_name = local_name
        self.diffs = diffs
        self.same_dir_counts = same_dir_counts
        self.decisions = {}          # {relative_path: direction}
        self.cancel_sync = False
        self.current_index = 0
        self._dark = _is_dark_mode()

        self.setWindowTitle(I18n.tr("wizard_title", lang))
        self.setFixedSize(860, 560)

        self._init_style()
        self._init_ui()
        self._show_page(0, animate=False)

    def _init_style(self):
        border_color = "#3a3a3a" if self._dark else "#e9ecef"
        text_muted = "#adb5bd" if self._dark else "#495057"
        btn_border = "#495057" if self._dark else "#ced4da"
        btn_border_hover = "#868e96" if self._dark else "#adb5bd"
        btn_disabled_border = "#3a3a3a" if self._dark else "#e9ecef"

        if self._dark:
            base_bg = "#2d2d2d"
            base_text = "#e0e0e0"
        else:
            base_bg = "#ffffff"
            base_text = "#212529"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {base_bg}; }}
            QWidget#slideHost {{ background-color: {base_bg}; }}
            QFrame#header {{ background-color: {base_bg}; border-bottom: 1px solid {border_color}; }}
            QFrame#footer {{ background-color: {base_bg}; border-top: 1px solid {border_color}; }}
            QLabel {{ color: {base_text}; }}
            QRadioButton {{ padding: 8px 12px; font-size: 13px; color: {base_text}; }}
            QRadioButton::indicator {{ width: 18px; height: 18px; border-radius: 9px; border: 2px solid {btn_border}; }}
            QRadioButton::indicator:hover {{ border: 2px solid {btn_border_hover}; }}
            QRadioButton::indicator:checked {{ border: 2px solid #2f9e44; background-color: #2f9e44; }}
            QCheckBox {{ padding: 6px 8px; font-size: 13px; color: {base_text}; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 2px solid {btn_border}; }}
            QCheckBox::indicator:hover {{ border: 2px solid {btn_border_hover}; }}
            QCheckBox::indicator:checked {{ border: 2px solid #2f9e44; background-color: #2f9e44; }}
            QPushButton {{ padding: 8px 24px; border-radius: 6px; font-size: 13px; font-weight: 500; }}
        """)
        self._border_color = border_color
        self._text_muted = text_muted
        self._btn_disabled_border = btn_disabled_border
        self._base_text = base_text
        self._base_bg = base_bg

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ---- 内容容器（弹出动画目标）----
        self._content_container = QWidget()
        container_lay = QVBoxLayout(self._content_container)
        container_lay.setSpacing(0)
        container_lay.setContentsMargins(0, 0, 0, 0)

        # ---- 顶部进度条 ----
        header = QFrame()
        header.setObjectName("header")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(28, 10, 28, 10)
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet(f"font-size: 13px; color: {self._text_muted}; font-weight: 500;")
        h_lay.addWidget(self.progress_label)
        h_lay.addStretch()
        container_lay.addWidget(header)

        # ---- 内容滑动区（无 layout，手动管理页面 pos 以实现滑动）----
        self.slide_host = QWidget()
        self.slide_host.setObjectName("slideHost")
        container_lay.addWidget(self.slide_host, 1)

        # ---- 底部固定按钮区 ----
        footer = QFrame()
        footer.setObjectName("footer")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(28, 12, 28, 12)

        self.prev_btn = QPushButton(I18n.tr("wizard_prev", self.lang))
        self.prev_btn.setMinimumSize(90, 36)
        self.prev_btn.setStyleSheet(f"""
            QPushButton {{ border: 1px solid {self._border_color}; border-radius: 6px; }}
            QPushButton:hover {{ border: 1px solid #868e96; }}
            QPushButton:disabled {{ color: {self._text_muted}; border-color: {self._btn_disabled_border}; }}
        """)
        self.prev_btn.clicked.connect(self._go_prev)

        self.confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        self.confirm_btn.setMinimumSize(100, 38)
        self.confirm_btn.setStyleSheet("""
            QPushButton { background-color: #40c057; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #37b24d; }
            QPushButton:pressed { background-color: #2f9e44; }
        """)
        self.confirm_btn.clicked.connect(self._confirm_current)

        self.skip_btn = QPushButton(I18n.tr("wizard_skip", self.lang))
        self.skip_btn.setMinimumSize(90, 36)
        self.skip_btn.setStyleSheet(f"""
            QPushButton {{ border: 1px solid {self._border_color}; border-radius: 6px; }}
            QPushButton:hover {{ border: 1px solid #868e96; }}
        """)
        self.skip_btn.clicked.connect(self._skip_current)

        self.cancel_sync_btn = QPushButton(I18n.tr("btn_cancel_sync", self.lang))
        self.cancel_sync_btn.setMinimumSize(120, 38)
        self.cancel_sync_btn.setStyleSheet("""
            QPushButton { background-color: #ff6b6b; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #fa5252; }
            QPushButton:pressed { background-color: #e03131; }
        """)
        self.cancel_sync_btn.clicked.connect(self._cancel_sync)

        f_lay.addWidget(self.prev_btn)
        f_lay.addStretch()
        f_lay.addWidget(self.confirm_btn)
        f_lay.addSpacing(8)
        f_lay.addWidget(self.skip_btn)
        f_lay.addSpacing(8)
        f_lay.addWidget(self.cancel_sync_btn)
        container_lay.addWidget(footer)

        # 将内容容器加入根布局
        root.addWidget(self._content_container, 1)

    # ---- 页面切换（滑动）----

    def _show_page(self, index, animate=True, direction=1):
        diff = self.diffs[index]
        same_dir_count = self.same_dir_counts.get(diff.relative_path, 0)
        new_page = DiffPage(diff, same_dir_count, self.lang, self.removable_name, self.local_name)
        new_page.setParent(self.slide_host)
        new_page.resize(self.slide_host.size())

        if not animate or self._current_page is None:
            if self._current_page:
                self._current_page.deleteLater()
            self._current_page = new_page
            new_page.move(0, 0)
            new_page.show()
        else:
            self._sliding = True
            old_page = self._current_page
            w = self.slide_host.width()
            start_x = w if direction > 0 else -w
            new_page.move(start_x, 0)
            new_page.show()

            anim_old = QPropertyAnimation(old_page, b"pos", self)
            anim_old.setDuration(self.SLIDE_DURATION)
            anim_old.setStartValue(QPoint(0, 0))
            anim_old.setEndValue(QPoint(-w if direction > 0 else w, 0))

            anim_new = QPropertyAnimation(new_page, b"pos", self)
            anim_new.setDuration(self.SLIDE_DURATION)
            anim_new.setStartValue(QPoint(start_x, 0))
            anim_new.setEndValue(QPoint(0, 0))

            def _on_finished():
                old_page.deleteLater()
                self._current_page = new_page
                self._sliding = False
                self._update_ui_state()

            anim_old.finished.connect(_on_finished)
            anim_old.start()
            anim_new.start()

        self.current_index = index
        self._update_ui_state()

    def _update_ui_state(self):
        total = len(self.diffs)
        self.progress_label.setText(
            I18n.tr("wizard_progress", self.lang, current=self.current_index + 1, total=total))
        self.prev_btn.setEnabled(self.current_index > 0 and not self._sliding)
        if self.current_index >= total - 1:
            self.confirm_btn.setText(I18n.tr("wizard_finish", self.lang))
        else:
            self.confirm_btn.setText(I18n.tr("btn_confirm", self.lang))

    # ---- 按钮动作 ----

    def _confirm_current(self):
        if self._sliding or self._current_page is None:
            return
        page = self._current_page
        direction = page.get_direction()
        apply_to_dir = page.should_apply_to_dir()
        diff = self.diffs[self.current_index]
        self.decisions[diff.relative_path] = direction

        if apply_to_dir:
            parent_dir = os.path.dirname(diff.relative_path)
            for other in self.diffs:
                if (other.relative_path != diff.relative_path
                        and os.path.dirname(other.relative_path) == parent_dir
                        and other.status == diff.status
                        and other.relative_path not in self.decisions):
                    self.decisions[other.relative_path] = direction

        self._go_next()

    def _skip_current(self):
        if self._sliding:
            return
        diff = self.diffs[self.current_index]
        self.decisions[diff.relative_path] = "skip"
        self._go_next()

    def _go_next(self):
        idx = self.current_index + 1
        while idx < len(self.diffs):
            if self.diffs[idx].relative_path not in self.decisions:
                break
            idx += 1
        if idx >= len(self.diffs):
            self.accept()
            return
        self._show_page(idx, animate=True, direction=1)

    def _go_prev(self):
        if self._sliding or self.current_index <= 0:
            return
        # 回到上一页时清除其旧决策，允许重新选择
        prev_diff = self.diffs[self.current_index - 1]
        self.decisions.pop(prev_diff.relative_path, None)
        self._show_page(self.current_index - 1, animate=True, direction=-1)

    def _cancel_sync(self):
        self.cancel_sync = True
        self.reject()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_page and not self._sliding:
            self._current_page.resize(self.slide_host.size())


class ConflictDialog(FadeDialog):
    def __init__(self, diff: DiffResult, same_dir_count: int = 0, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(I18n.tr("dialog_conflict", lang))
        self.result_direction = None
        self.apply_to_dir = False
        self.cancel_sync = False
        self.same_dir_count = same_dir_count
        self.setMinimumWidth(500)
        
        self.wintogo_newer = diff.wintogo_info.mtime > diff.local_info.mtime
        self._init_ui(diff)
    
    def _init_ui(self, diff: DiffResult):
        self.setStyleSheet("""
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #adb5bd;
                background-color: #ffffff;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #868e96;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #2f9e44;
                background-color: #2f9e44;
            }
            QCheckBox {
                padding: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #adb5bd;
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #868e96;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #2f9e44;
                background-color: #2f9e44;
            }
            QPushButton {
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel(I18n.tr("conflict_title", self.lang))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e03131;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        file_label = QLabel(I18n.tr("file_label", self.lang, path=diff.relative_path))
        file_label.setStyleSheet("""
            font-size: 13px; 
            padding: 12px;
        """)
        file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(file_label)
        
        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 8, 0, 8)
        
        wintogo_time = datetime.fromtimestamp(diff.wintogo_info.mtime).strftime('%Y-%m-%d %H:%M:%S')
        local_time = datetime.fromtimestamp(diff.local_info.mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        wintogo_box = QFrame()
        wintogo_box.setStyleSheet("""
            QFrame {
                background-color: #e7f5ff;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        wintogo_layout = QVBoxLayout(wintogo_box)
        wintogo_layout.setSpacing(6)
        wintogo_title = QLabel(I18n.tr("removable_time", self.lang))
        wintogo_title.setStyleSheet("font-weight: bold; color: #1971c2; font-size: 14px;")
        wintogo_title.setAlignment(Qt.AlignCenter)
        wintogo_time_label = QLabel(wintogo_time)
        wintogo_time_label.setStyleSheet("color: #495057; font-size: 12px;")
        wintogo_time_label.setAlignment(Qt.AlignCenter)
        wintogo_layout.addWidget(wintogo_title)
        wintogo_layout.addWidget(wintogo_time_label)
        
        local_box = QFrame()
        local_box.setStyleSheet("""
            QFrame {
                background-color: #ebfbee;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        local_layout = QVBoxLayout(local_box)
        local_layout.setSpacing(6)
        local_title = QLabel(I18n.tr("local_time", self.lang))
        local_title.setStyleSheet("font-weight: bold; color: #2f9e44; font-size: 14px;")
        local_title.setAlignment(Qt.AlignCenter)
        local_time_label = QLabel(local_time)
        local_time_label.setStyleSheet("color: #495057; font-size: 12px;")
        local_time_label.setAlignment(Qt.AlignCenter)
        local_layout.addWidget(local_title)
        local_layout.addWidget(local_time_label)
        
        time_layout.addWidget(wintogo_box)
        time_layout.addWidget(local_box)
        layout.addWidget(time_widget)
        
        newer = I18n.tr("removable_time", self.lang) if self.wintogo_newer else I18n.tr("local_time", self.lang)
        hint_label = QLabel(I18n.tr("newer_hint", self.lang, side=newer))
        hint_label.setStyleSheet("color: #fd7e14; font-size: 13px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line2)
        
        choice_label = QLabel(I18n.tr("choice_label", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)

        self.rb_newer = QRadioButton()
        self.rb_older = QRadioButton()
        self.rb_delete_both = QRadioButton(self.lang == "zh" and "🗑️ 双端删除此项目" or "🗑️ Delete from both sides")
        self.rb_skip = QRadioButton(I18n.tr("skip_file", self.lang))

        newer_side = I18n.tr("removable_time", self.lang) if self.wintogo_newer else I18n.tr("local_time", self.lang)
        older_side = I18n.tr("local_time", self.lang) if self.wintogo_newer else I18n.tr("removable_time", self.lang)
        self.rb_newer.setText(I18n.tr("keep_newest", self.lang, side=newer_side))
        self.rb_older.setText(I18n.tr("keep_older", self.lang, side=older_side))

        self.rb_newer.setChecked(True)

        self.button_group.addButton(self.rb_newer, 0)
        self.button_group.addButton(self.rb_older, 1)
        self.button_group.addButton(self.rb_delete_both, 2)
        self.button_group.addButton(self.rb_skip, 3)

        layout.addWidget(self.rb_newer)
        layout.addWidget(self.rb_older)
        layout.addWidget(self.rb_delete_both)
        layout.addWidget(self.rb_skip)
        
        if self.same_dir_count > 0:
            self.apply_dir_check = QCheckBox(I18n.tr("apply_dir_files", self.lang, count=self.same_dir_count))
            self.apply_dir_check.setStyleSheet("color: #1971c2; font-weight: 500;")
            self.apply_dir_check.setChecked(True)
            layout.addWidget(self.apply_dir_check)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        confirm_btn.setMinimumSize(100, 38)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #40c057;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #37b24d;
            }
            QPushButton:pressed {
                background-color: #2f9e44;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(I18n.tr("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(I18n.tr("btn_cancel_sync", self.lang))
        cancel_sync_btn.setMinimumSize(120, 38)
        cancel_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #fa5252;
            }
            QPushButton:pressed {
                background-color: #e03131;
            }
        """)
        cancel_sync_btn.clicked.connect(self._cancel_sync)
        
        btn_layout.addWidget(confirm_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_sync_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _cancel_sync(self):
        """取消本次同步"""
        self.cancel_sync = True
        self.reject()

    def get_direction(self):
        checked_id = self.button_group.checkedId()
        if checked_id == 0:
            if self.wintogo_newer:
                return "wintogo_to_local"
            else:
                return "local_to_wintogo"
        elif checked_id == 1:
            if self.wintogo_newer:
                return "local_to_wintogo"
            else:
                return "wintogo_to_local"
        elif checked_id == 2:
            return "delete_both"
        else:
            return "skip"

    def should_apply_to_dir(self):
        if self.same_dir_count > 0 and hasattr(self, 'apply_dir_check'):
            return self.apply_dir_check.isChecked()
        return False


class OnlyOneSideDialog(FadeDialog):
    def __init__(self, diff: DiffResult, same_dir_count: int = 0, lang: str = "zh", removable_name: str = "移动介质目录", local_name: str = "本地目录", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.removable_name = removable_name
        self.local_name = local_name
        self.setWindowTitle(I18n.tr("dialog_diff", lang))
        self.diff = diff
        self.result_direction = None
        self.apply_to_dir = False
        self.cancel_sync = False
        self.same_dir_count = same_dir_count
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #adb5bd;
                background-color: #ffffff;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #868e96;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #2f9e44;
                background-color: #2f9e44;
            }
            QCheckBox {
                padding: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #adb5bd;
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #868e96;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #2f9e44;
                background-color: #2f9e44;
            }
            QPushButton {
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        is_wintogo_only = self.diff.status == FileStatus.WINTOGO_ONLY
        side_name = I18n.tr("removable_time", self.lang) if is_wintogo_only else I18n.tr("local_time", self.lang)
        other_side = I18n.tr("local_time", self.lang) if is_wintogo_only else I18n.tr("removable_time", self.lang)
        
        title_label = QLabel(I18n.tr("diff_title", self.lang) + f" ({side_name})")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1971c2;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        file_label = QLabel(I18n.tr("file_label", self.lang, path=self.diff.relative_path))
        file_label.setStyleSheet("""
            font-size: 13px; 
            padding: 12px;
        """)
        file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(file_label)
        
        info = self.diff.wintogo_info if is_wintogo_only else self.diff.local_info
        if info:
            size_str = self._format_size(info.size)
            mtime_str = datetime.fromtimestamp(info.mtime).strftime('%Y-%m-%d %H:%M:%S')
            size_text = self.lang == "zh" and "大小" or "Size"
            mtime_text = self.lang == "zh" and "修改时间" or "Modified"
            info_label = QLabel(f"{size_text}: {size_str}  |  {mtime_text}: {mtime_str}")
            info_label.setStyleSheet("color: #868e96; font-size: 12px;")
            info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_label)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line2)
        
        choice_label = QLabel(I18n.tr("choice_label", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)

        # 根据文件状态动态显示正确的同步方向
        # 提取名称前缀
        removable_prefix = self.removable_name
        if removable_prefix.endswith("目录"):
            removable_prefix = removable_prefix[:-2]
        elif removable_prefix.endswith("Directory"):
            removable_prefix = removable_prefix[:-9]
        
        local_prefix = self.local_name
        if local_prefix.endswith("目录"):
            local_prefix = local_prefix[:-2]
        elif local_prefix.endswith("Directory"):
            local_prefix = local_prefix[:-9]
        
        if is_wintogo_only:
            # 介质存在，本地不存在：显示"介质 → 本地"
            copy_text = self.lang == "zh" and f"➡️ {removable_prefix} → {local_prefix}（补充{local_prefix}缺失的文件）" or f"➡️ {removable_prefix} → {local_prefix}"
        else:
            # 本地存在，介质不存在：显示"本地 → 介质"
            copy_text = self.lang == "zh" and f"➡️ {local_prefix} → {removable_prefix}（补充{removable_prefix}缺失的文件）" or f"➡️ {local_prefix} → {removable_prefix}"

        delete_text = self.lang == "zh" and f"🗑️ 删除此文件（移除{side_name}多余的文件）" or f"🗑️ Delete this file"
        self.rb_copy = QRadioButton(copy_text)
        self.rb_delete = QRadioButton(delete_text)
        self.rb_skip = QRadioButton(I18n.tr("skip_file", self.lang))

        self.rb_copy.setChecked(True)

        self.button_group.addButton(self.rb_copy, 0)
        self.button_group.addButton(self.rb_delete, 1)
        self.button_group.addButton(self.rb_skip, 2)

        layout.addWidget(self.rb_copy)
        layout.addWidget(self.rb_delete)
        layout.addWidget(self.rb_skip)
        
        if self.same_dir_count > 0:
            self.apply_dir_check = QCheckBox(I18n.tr("apply_dir_files", self.lang, count=self.same_dir_count))
            self.apply_dir_check.setStyleSheet("color: #1971c2; font-weight: 500;")
            self.apply_dir_check.setChecked(True)
            layout.addWidget(self.apply_dir_check)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        confirm_btn.setMinimumSize(100, 38)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #40c057;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #37b24d;
            }
            QPushButton:pressed {
                background-color: #2f9e44;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(I18n.tr("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(I18n.tr("btn_cancel_sync", self.lang))
        cancel_sync_btn.setMinimumSize(120, 38)
        cancel_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #fa5252;
            }
            QPushButton:pressed {
                background-color: #e03131;
            }
        """)
        cancel_sync_btn.clicked.connect(self._cancel_sync)
        
        btn_layout.addWidget(confirm_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_sync_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _cancel_sync(self):
        """取消本次同步"""
        self.cancel_sync = True
        self.reject()
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def get_direction(self):
        checked_id = self.button_group.checkedId()
        is_wintogo_only = self.diff.status == FileStatus.WINTOGO_ONLY

        if checked_id == 0:
            if is_wintogo_only:
                return "to_local"
            else:
                return "to_wintogo"
        elif checked_id == 1:
            if is_wintogo_only:
                return "delete_wintogo"
            else:
                return "delete_local"
        else:
            return "skip"
    
    def should_apply_to_dir(self):
        if self.same_dir_count > 0 and hasattr(self, 'apply_dir_check'):
            return self.apply_dir_check.isChecked()
        return False


class MtimeDiffDialog(FadeDialog):
    def __init__(self, diff: DiffResult, same_dir_count: int = 0, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(I18n.tr("dialog_mtime", lang))
        self.diff = diff
        self.result_direction = None
        self.apply_to_dir = False
        self.cancel_sync = False
        self.same_dir_count = same_dir_count
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #adb5bd;
                background-color: #ffffff;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #868e96;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #2f9e44;
                background-color: #2f9e44;
            }
            QCheckBox {
                padding: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #adb5bd;
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #868e96;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #2f9e44;
                background-color: #2f9e44;
            }
            QPushButton {
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel(I18n.tr("mtime_title", self.lang))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #fd7e14;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        hint_text = self.lang == "zh" and "文件大小相同，但修改时间不同" or "Same size, but different modification time"
        hint_label = QLabel(hint_text)
        hint_label.setStyleSheet("color: #868e96; font-size: 12px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        file_label = QLabel(I18n.tr("file_label", self.lang, path=self.diff.relative_path))
        file_label.setStyleSheet("""
            font-size: 13px; 
            padding: 12px;
        """)
        file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(file_label)
        
        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 8, 0, 8)
        
        wintogo_time = datetime.fromtimestamp(self.diff.wintogo_info.mtime).strftime('%Y-%m-%d %H:%M:%S')
        local_time = datetime.fromtimestamp(self.diff.local_info.mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        wintogo_box = QFrame()
        wintogo_box.setStyleSheet("""
            QFrame {
                background-color: #e7f5ff;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        wintogo_layout = QVBoxLayout(wintogo_box)
        wintogo_layout.setSpacing(6)
        wintogo_title = QLabel(I18n.tr("removable_time", self.lang))
        wintogo_title.setStyleSheet("font-weight: bold; color: #1971c2; font-size: 14px;")
        wintogo_title.setAlignment(Qt.AlignCenter)
        wintogo_time_label = QLabel(wintogo_time)
        wintogo_time_label.setStyleSheet("color: #495057; font-size: 12px;")
        wintogo_time_label.setAlignment(Qt.AlignCenter)
        wintogo_layout.addWidget(wintogo_title)
        wintogo_layout.addWidget(wintogo_time_label)
        
        local_box = QFrame()
        local_box.setStyleSheet("""
            QFrame {
                background-color: #ebfbee;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        local_layout = QVBoxLayout(local_box)
        local_layout.setSpacing(6)
        local_title = QLabel(I18n.tr("local_time", self.lang))
        local_title.setStyleSheet("font-weight: bold; color: #2f9e44; font-size: 14px;")
        local_title.setAlignment(Qt.AlignCenter)
        local_time_label = QLabel(local_time)
        local_time_label.setStyleSheet("color: #495057; font-size: 12px;")
        local_time_label.setAlignment(Qt.AlignCenter)
        local_layout.addWidget(local_title)
        local_layout.addWidget(local_time_label)
        
        time_layout.addWidget(wintogo_box)
        time_layout.addWidget(local_box)
        layout.addWidget(time_widget)
        
        self.wintogo_newer = self.diff.wintogo_info.mtime > self.diff.local_info.mtime
        newer = I18n.tr("removable_time", self.lang) if self.wintogo_newer else I18n.tr("local_time", self.lang)
        hint_label2 = QLabel(I18n.tr("newer_hint", self.lang, side=newer))
        hint_label2.setStyleSheet("color: #fd7e14; font-size: 13px;")
        hint_label2.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label2)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line2)
        
        choice_label = QLabel(I18n.tr("choice_label", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)

        self.rb_newer = QRadioButton()
        self.rb_older = QRadioButton()
        self.rb_delete_both = QRadioButton(self.lang == "zh" and "🗑️ 双端删除此项目" or "🗑️ Delete from both sides")
        self.rb_skip = QRadioButton(self.lang == "zh" and "⏭️ 跳过（保持现状）" or "⏭️ Skip (keep current)")

        newer_side = I18n.tr("removable_time", self.lang) if self.wintogo_newer else I18n.tr("local_time", self.lang)
        older_side = I18n.tr("local_time", self.lang) if self.wintogo_newer else I18n.tr("removable_time", self.lang)
        newer_text = self.lang == "zh" and f"✨ 用{newer_side}（较新）覆盖{older_side}" or f"✨ Use {newer_side} (newer) to overwrite"
        older_text = self.lang == "zh" and f"📥 用{older_side}（较旧）覆盖{newer_side}" or f"📥 Use {older_side} (older) to overwrite"
        self.rb_newer.setText(newer_text)
        self.rb_older.setText(older_text)

        self.rb_newer.setChecked(True)

        self.button_group.addButton(self.rb_newer, 0)
        self.button_group.addButton(self.rb_older, 1)
        self.button_group.addButton(self.rb_delete_both, 2)
        self.button_group.addButton(self.rb_skip, 3)

        layout.addWidget(self.rb_newer)
        layout.addWidget(self.rb_older)
        layout.addWidget(self.rb_delete_both)
        layout.addWidget(self.rb_skip)
        
        if self.same_dir_count > 0:
            self.apply_dir_check = QCheckBox(I18n.tr("apply_dir_files", self.lang, count=self.same_dir_count))
            self.apply_dir_check.setStyleSheet("color: #1971c2; font-weight: 500;")
            self.apply_dir_check.setChecked(True)
            layout.addWidget(self.apply_dir_check)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        confirm_btn.setMinimumSize(100, 38)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #40c057;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #37b24d;
            }
            QPushButton:pressed {
                background-color: #2f9e44;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(I18n.tr("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(I18n.tr("btn_cancel_sync", self.lang))
        cancel_sync_btn.setMinimumSize(120, 38)
        cancel_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #fa5252;
            }
            QPushButton:pressed {
                background-color: #e03131;
            }
        """)
        cancel_sync_btn.clicked.connect(self._cancel_sync)
        
        btn_layout.addWidget(confirm_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_sync_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _cancel_sync(self):
        """取消本次同步"""
        self.cancel_sync = True
        self.reject()

    def get_direction(self):
        checked_id = self.button_group.checkedId()
        if checked_id == 0:
            if self.wintogo_newer:
                return "wintogo_to_local"
            else:
                return "local_to_wintogo"
        elif checked_id == 1:
            if self.wintogo_newer:
                return "local_to_wintogo"
            else:
                return "wintogo_to_local"
        elif checked_id == 2:
            return "delete_both"
        else:
            return "skip"

    def should_apply_to_dir(self):
        if self.same_dir_count > 0 and hasattr(self, 'apply_dir_check'):
            return self.apply_dir_check.isChecked()
        return False


class IgnoreRulesDialog(FadeDialog):
    def __init__(self, rules, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(I18n.tr("dialog_ignore", lang))
        self.setMinimumSize(500, 400)
        self.rules = rules.copy()
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QLabel {
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #4dabf7;
            }
            QPushButton {
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                border: 1px solid #ced4da;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #e7f5ff;
                color: #1971c2;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel(self.lang == "zh" and "⚙ 忽略规则设置" or "⚙ Ignore Rules")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        layout.addWidget(title_label)
        
        hint_label = QLabel(I18n.tr("ignore_hint", self.lang))
        hint_label.setStyleSheet("color: #868e96; font-size: 12px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        
        self.rule_list = QListWidget()
        self.rule_list.setMinimumHeight(150)
        for rule in self.rules:
            self.rule_list.addItem(rule)
        layout.addWidget(self.rule_list)
        
        add_layout = QHBoxLayout()
        self.rule_input = QLineEdit()
        self.rule_input.setPlaceholderText(I18n.tr("ignore_add_placeholder", self.lang))
        self.rule_input.returnPressed.connect(self._add_rule)
        add_layout.addWidget(self.rule_input)
        
        add_btn = QPushButton(I18n.tr("btn_add", self.lang))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #339af0;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #228be6;
            }
        """)
        add_btn.setMinimumWidth(80)
        add_btn.clicked.connect(self._add_rule)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        del_btn = QPushButton(self.lang == "zh" and "删除选中规则" or "Delete Selected")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #fa5252;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #f03e3e;
            }
        """)
        del_btn.clicked.connect(self._delete_rule)
        layout.addWidget(del_btn)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        confirm_btn.setMinimumSize(100, 38)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #40c057;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #37b24d;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(I18n.tr("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(confirm_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def _add_rule(self):
        rule = self.rule_input.text().strip()
        if rule and rule not in self.rules:
            self.rules.append(rule)
            self.rule_list.addItem(rule)
            self.rule_input.clear()
    
    def _delete_rule(self):
        current_item = self.rule_list.currentItem()
        if current_item:
            row = self.rule_list.row(current_item)
            self.rule_list.takeItem(row)
            self.rules.pop(row)
    
    def get_rules(self):
        return self.rules


class DirSyncDialog(FadeDialog):
    def __init__(self, dir_path: str, diff_list: list, lang: str = "zh", removable_name: str = "移动介质目录", local_name: str = "本地目录", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.removable_name = removable_name
        self.local_name = local_name
        self.setWindowTitle(I18n.tr("dialog_dir_sync", lang))
        self.dir_path = dir_path
        self.diff_list = diff_list
        self.result_direction = None
        self.cancel_sync = False
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #adb5bd;
                background-color: #ffffff;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #868e96;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #2f9e44;
                background-color: #2f9e44;
            }
            QPushButton {
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel(I18n.tr("dir_sync_title", self.lang))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1971c2;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        path_text = self.lang == "zh" and f"路径: {self.dir_path}" or f"Path: {self.dir_path}"
        dir_label = QLabel(path_text)
        dir_label.setStyleSheet("""
            font-size: 14px; 
            padding: 10px;
        """)
        dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(dir_label)
        
        only_wintogo = len([d for d in self.diff_list if d.status == FileStatus.WINTOGO_ONLY])
        only_local = len([d for d in self.diff_list if d.status == FileStatus.LOCAL_ONLY])
        conflicts = len([d for d in self.diff_list if d.status == FileStatus.CONFLICT])
        mtime_diffs = len([d for d in self.diff_list if d.status == FileStatus.MTIME_DIFF])
        
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 8, 0, 8)
        
        if only_wintogo > 0:
            wintogo_box = QFrame()
            wintogo_box.setStyleSheet("QFrame { background-color: #e7f5ff; border-radius: 8px; padding: 10px; }")
            wintogo_layout = QVBoxLayout(wintogo_box)
            # 提取前缀（去掉"目录"尾缀）
            removable_prefix = self.removable_name
            if removable_prefix.endswith("目录"):
                removable_prefix = removable_prefix[:-2]
            elif removable_prefix.endswith("Directory"):
                removable_prefix = removable_prefix[:-9]
            wintogo_title = QLabel(self.lang == "zh" and f"{removable_prefix}独有" or f"{removable_prefix} Only")
            wintogo_title.setStyleSheet("font-weight: bold; color: #1971c2; font-size: 13px;")
            wintogo_title.setAlignment(Qt.AlignCenter)
            wintogo_count = QLabel(str(only_wintogo))
            wintogo_count.setStyleSheet("font-size: 18px; font-weight: bold; color: #1971c2;")
            wintogo_count.setAlignment(Qt.AlignCenter)
            wintogo_layout.addWidget(wintogo_title)
            wintogo_layout.addWidget(wintogo_count)
            stats_layout.addWidget(wintogo_box)
        
        if only_local > 0:
            local_box = QFrame()
            local_box.setStyleSheet("QFrame { background-color: #ebfbee; border-radius: 8px; padding: 10px; }")
            local_layout = QVBoxLayout(local_box)
            # 提取前缀（去掉"目录"尾缀）
            local_prefix = self.local_name
            if local_prefix.endswith("目录"):
                local_prefix = local_prefix[:-2]
            elif local_prefix.endswith("Directory"):
                local_prefix = local_prefix[:-9]
            local_title = QLabel(self.lang == "zh" and f"{local_prefix}独有" or f"{local_prefix} Only")
            local_title.setStyleSheet("font-weight: bold; color: #2f9e44; font-size: 13px;")
            local_title.setAlignment(Qt.AlignCenter)
            local_count = QLabel(str(only_local))
            local_count.setStyleSheet("font-size: 18px; font-weight: bold; color: #2f9e44;")
            local_count.setAlignment(Qt.AlignCenter)
            local_layout.addWidget(local_title)
            local_layout.addWidget(local_count)
            stats_layout.addWidget(local_box)
        
        if conflicts > 0:
            conflict_box = QFrame()
            conflict_box.setStyleSheet("QFrame { background-color: #fff3bf; border-radius: 8px; padding: 10px; }")
            conflict_layout = QVBoxLayout(conflict_box)
            conflict_title = QLabel(self.lang == "zh" and "冲突" or "Conflict")
            conflict_title.setStyleSheet("font-weight: bold; color: #e67700; font-size: 13px;")
            conflict_title.setAlignment(Qt.AlignCenter)
            conflict_count = QLabel(str(conflicts))
            conflict_count.setStyleSheet("font-size: 18px; font-weight: bold; color: #e67700;")
            conflict_count.setAlignment(Qt.AlignCenter)
            conflict_layout.addWidget(conflict_title)
            conflict_layout.addWidget(conflict_count)
            stats_layout.addWidget(conflict_box)
        
        if mtime_diffs > 0:
            mtime_box = QFrame()
            mtime_box.setStyleSheet("QFrame { background-color: #ffe8cc; border-radius: 8px; padding: 10px; }")
            mtime_layout = QVBoxLayout(mtime_box)
            mtime_title = QLabel(self.lang == "zh" and "时间差异" or "Time Diff")
            mtime_title.setStyleSheet("font-weight: bold; color: #fd7e14; font-size: 13px;")
            mtime_title.setAlignment(Qt.AlignCenter)
            mtime_count = QLabel(str(mtime_diffs))
            mtime_count.setStyleSheet("font-size: 18px; font-weight: bold; color: #fd7e14;")
            mtime_count.setAlignment(Qt.AlignCenter)
            mtime_layout.addWidget(mtime_title)
            mtime_layout.addWidget(mtime_count)
            stats_layout.addWidget(mtime_box)
        
        layout.addWidget(stats_widget)
        
        total_text = self.lang == "zh" and f"共 {len(self.diff_list)} 个差异项" or f"Total: {len(self.diff_list)} items"
        total_label = QLabel(total_text)
        total_label.setStyleSheet("color: #868e96; font-size: 13px;")
        total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(total_label)
        detail_btn = QPushButton(I18n.tr("view_detail", self.lang))
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        detail_btn.clicked.connect(self._show_detail_list)
        layout.addWidget(detail_btn)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        choice_label = QLabel(I18n.tr("dir_choice", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)
        
        self.rb_wintogo = QRadioButton(I18n.tr("dir_to_local", self.lang))
        self.rb_local = QRadioButton(I18n.tr("dir_to_removable", self.lang))
        self.rb_delete_both = QRadioButton(I18n.tr("dir_delete_both", self.lang))
        self.rb_skip = QRadioButton(self.lang == "zh" and "⏭️ 跳过此目录" or "⏭️ Skip this directory")
        
        self.rb_wintogo.setChecked(True)
        
        self.button_group.addButton(self.rb_wintogo, 0)
        self.button_group.addButton(self.rb_local, 1)
        self.button_group.addButton(self.rb_delete_both, 2)
        self.button_group.addButton(self.rb_skip, 3)
        
        layout.addWidget(self.rb_wintogo)
        layout.addWidget(self.rb_local)
        layout.addWidget(self.rb_delete_both)
        layout.addWidget(self.rb_skip)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        confirm_btn.setMinimumSize(100, 38)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #40c057;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #37b24d;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(I18n.tr("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(I18n.tr("btn_cancel_sync", self.lang))
        cancel_sync_btn.setMinimumSize(120, 38)
        cancel_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #fa5252;
            }
            QPushButton:pressed {
                background-color: #e03131;
            }
        """)
        cancel_sync_btn.clicked.connect(self._cancel_sync)
        
        btn_layout.addWidget(confirm_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_sync_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _cancel_sync(self):
        """取消本次同步"""
        self.cancel_sync = True
        self.reject()
    
    def get_direction(self):
        checked_id = self.button_group.checkedId()
        if checked_id == 0:
            return "wintogo_to_local"
        elif checked_id == 1:
            return "local_to_wintogo"
        elif checked_id == 2:
            return "delete_both"
        else:
            return "skip"
    
    def _show_detail_list(self):
        detail_dialog = QDialog(self)
        detail_dialog.setWindowTitle("差异文件详情")
        detail_dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(detail_dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel(f"📁 {self.dir_path}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1971c2;")
        layout.addWidget(title)
        
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #e7f5ff;
            }
        """)
        
        for diff in self.diff_list:
            status_text = ""
            status_color = ""
            
            # 提取前缀（去掉"目录"尾缀）
            removable_prefix = self.removable_name
            if removable_prefix.endswith("目录"):
                removable_prefix = removable_prefix[:-2]
            elif removable_prefix.endswith("Directory"):
                removable_prefix = removable_prefix[:-9]
            
            local_prefix = self.local_name
            if local_prefix.endswith("目录"):
                local_prefix = local_prefix[:-2]
            elif local_prefix.endswith("Directory"):
                local_prefix = local_prefix[:-9]
            
            if diff.status == FileStatus.WINTOGO_ONLY:
                status_text = f"[{removable_prefix}独有]"
                status_color = "#1971c2"
            elif diff.status == FileStatus.LOCAL_ONLY:
                status_text = f"[{local_prefix}独有]"
                status_color = "#2f9e44"
            elif diff.status == FileStatus.CONFLICT:
                status_text = "[冲突]"
                status_color = "#e67700"
            elif diff.status == FileStatus.MTIME_DIFF:
                status_text = "[时间差异]"
                status_color = "#fd7e14"
            
            file_name = os.path.basename(diff.relative_path)
            rel_path = diff.relative_path
            
            item = QListWidgetItem(f"{status_text} {file_name}")
            item.setData(Qt.UserRole, rel_path)
            item.setForeground(QColor(status_color))
            
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 36)
        close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        close_btn.clicked.connect(detail_dialog.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        detail_dialog.exec()


class ConfirmSyncDialog(FadeDialog):
    """带淡入动画的同步确认弹窗，替代 QMessageBox。"""

    def __init__(self, title, message, lang, parent=None):
        super().__init__(parent)
        self._confirmed = False
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # 内容容器
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 图标 + 消息
        msg_label = QLabel(f"❓ {message}")
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 13px; line-height: 1.6;")
        content_layout.addWidget(msg_label)

        content_layout.addStretch()

        # 按钮
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        self.cancel_btn = QPushButton(lang == "zh" and "取消" or "Cancel")
        self.cancel_btn.setMinimumSize(90, 36)
        self.cancel_btn.setStyleSheet("""
            QPushButton { border: 1px solid #ced4da; border-radius: 6px; padding: 8px 24px; font-size: 13px; }
            QPushButton:hover { border: 1px solid #adb5bd; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton(lang == "zh" and "确定" or "Confirm")
        self.confirm_btn.setMinimumSize(90, 36)
        self.confirm_btn.setStyleSheet("""
            QPushButton { background-color: #40c057; color: white; border: none; border-radius: 6px; padding: 8px 24px; font-size: 13px; font-weight: 500; }
            QPushButton:hover { background-color: #37b24d; }
            QPushButton:pressed { background-color: #2f9e44; }
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)

        btn_lay.addWidget(self.confirm_btn)
        btn_lay.addSpacing(8)
        btn_lay.addWidget(self.cancel_btn)
        content_layout.addLayout(btn_lay)

        layout.addWidget(content)

    def _on_confirm(self):
        self._confirmed = True
        self.accept()

    def is_confirmed(self):
        return self._confirmed


class SyncRulesDialog(FadeDialog):
    def __init__(self, rules, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(I18n.tr("dialog_sync_rule", lang))
        self.setMinimumSize(500, 400)
        self.rules = rules.copy()
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QLabel {
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #4dabf7;
            }
            QPushButton {
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                border: 1px solid #ced4da;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #e7f5ff;
                color: #1971c2;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel(self.lang == "zh" and "📁 同步规则设置" or "📁 Sync Rules")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        layout.addWidget(title_label)
        
        hint_label = QLabel(I18n.tr("sync_rule_hint", self.lang))
        hint_label.setStyleSheet("color: #868e96; font-size: 12px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        
        self.rule_list = QListWidget()
        self.rule_list.setMinimumHeight(150)
        for rule in self.rules:
            self.rule_list.addItem(rule)
        layout.addWidget(self.rule_list)
        
        add_layout = QHBoxLayout()
        self.rule_input = QLineEdit()
        self.rule_input.setPlaceholderText(I18n.tr("sync_rule_add_placeholder", self.lang))
        self.rule_input.returnPressed.connect(self._add_rule)
        add_layout.addWidget(self.rule_input)
        
        add_btn = QPushButton(I18n.tr("btn_add", self.lang))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #339af0;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #228be6;
            }
        """)
        add_btn.setMinimumWidth(80)
        add_btn.clicked.connect(self._add_rule)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        del_btn = QPushButton(self.lang == "zh" and "删除选中规则" or "Delete Selected")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #fa5252;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #f03e3e;
            }
        """)
        del_btn.clicked.connect(self._delete_rule)
        layout.addWidget(del_btn)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        confirm_btn.setMinimumSize(100, 38)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #40c057;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #37b24d;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(I18n.tr("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(confirm_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def _add_rule(self):
        rule = self.rule_input.text().strip()
        if rule and rule not in self.rules:
            self.rules.append(rule)
            self.rule_list.addItem(rule)
            self.rule_input.clear()
    
    def _delete_rule(self):
        current_item = self.rule_list.currentItem()
        if current_item:
            row = self.rule_list.row(current_item)
            self.rule_list.takeItem(row)
            self.rules.pop(row)
    
    def get_rules(self):
        return self.rules


class RenameDialog(FadeDialog):
    """修改目录名称对话框"""
    def __init__(self, old_name: str, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.old_name = old_name
        self.new_name = old_name
        # 提取前缀和尾缀（根据语言动态设置）
        self.suffix = lang == "zh" and "目录" or " Directory"
        self.prefix = old_name
        # 去掉可能存在的旧后缀
        if old_name.endswith("目录"):
            self.prefix = old_name[:-2]
        elif old_name.endswith("Directory"):
            self.prefix = old_name[:-9]
        elif old_name.endswith(" Directory"):
            self.prefix = old_name[:-10]

        self.setWindowTitle(I18n.tr("rename_dialog_title", lang))
        self.setModal(True)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setFixedSize(400, 200)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 输入框（上方）- 只显示前缀部分
        self.name_input = QLineEdit()
        self.name_input.setText(self.prefix)
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #339af0;
            }
        """)
        layout.addWidget(self.name_input)

        # 名称展示行（下方：原名称 → 新名称）
        name_row_layout = QHBoxLayout()
        name_row_layout.setSpacing(8)

        # 原名称标签
        old_label = QLabel(I18n.tr("rename_old_name", self.lang) + ":")
        old_label.setStyleSheet("color: #868e96; font-size: 12px;")
        name_row_layout.addWidget(old_label)

        old_name_text = QLabel(self.prefix)
        old_name_text.setStyleSheet("color: #495057; font-size: 12px; font-weight: bold;")
        name_row_layout.addWidget(old_name_text)

        # 箭头
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("color: #339af0; font-size: 14px; font-weight: bold;")
        name_row_layout.addWidget(arrow_label)

        # 新名称标签
        new_label = QLabel(I18n.tr("rename_new_name", self.lang) + ":")
        new_label.setStyleSheet("color: #868e96; font-size: 12px;")
        name_row_layout.addWidget(new_label)

        self.new_name_preview = QLabel(self.prefix)
        self.new_name_preview.setStyleSheet("color: #2f9e44; font-size: 12px; font-weight: bold;")
        name_row_layout.addWidget(self.new_name_preview)

        name_row_layout.addStretch()
        layout.addLayout(name_row_layout)

        # 输入框变化时更新预览
        self.name_input.textChanged.connect(self._update_preview)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        confirm_btn = QPushButton(I18n.tr("btn_confirm", self.lang))
        confirm_btn.setMinimumSize(100, 36)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #40c057;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #37b24d;
            }
        """)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        cancel_btn = QPushButton(I18n.tr("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _update_preview(self):
        """更新新名称预览"""
        text = self.name_input.text().strip()
        if not text:
            text = self.prefix
        # 只显示前缀部分
        self.new_name_preview.setText(text)

    def _on_confirm(self):
        """确认修改"""
        text = self.name_input.text().strip()
        if text:
            # 返回完整名称（前缀+尾缀）
            self.new_name = text + self.suffix
            self.accept()
        else:
            QMessageBox.warning(self,
                self.lang == "zh" and "警告" or "Warning",
                self.lang == "zh" and "名称不能为空" or "Name cannot be empty")

    def get_new_name(self):
        # 返回前缀部分（不含尾缀）
        text = self.name_input.text().strip()
        if not text:
            text = self.prefix
        return text


class AboutDialog(FadeDialog):
    """关于弹窗"""
    def __init__(self, lang='zh', parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(I18n.tr("about_title", lang))
        self.setModal(True)
        # 设置窗口标志：只保留关闭按钮
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        # 根据是否显示检查更新按钮调整窗口高度（增加垂直分散度）
        height = 300 if Config.ENABLE_CHECK_UPDATE else 260
        self.setFixedSize(400, height)

        # SSL 上下文（避免 SSL 证书校验错误导致无法更新）
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题（蓝色，22px）
        title_label = QLabel(Config.APP_NAME)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #339af0;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        layout.addSpacing(8)

        # 版本信息（12px）
        version_label = QLabel(f"{I18n.tr('about_version_label', self.lang)} {Config.DISPLAY_VERSION}")
        version_label.setStyleSheet("font-size: 12px; color: #495057;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # 描述（灰色小字，11px）
        desc_label = QLabel(I18n.tr("about_description", self.lang))
        desc_label.setStyleSheet("font-size: 11px; color: #868e96;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addSpacing(12)

        # 作者信息（灰色悬浮变蓝，不可点击，11px）
        author_label = QLabel(f"{I18n.tr('about_author_label', self.lang)}：{Config.APP_AUTHOR}")
        author_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #495057;
            }
            QLabel:hover {
                color: #339af0;
            }
        """)
        author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_label)

        # GitHub链接（灰色悬浮变蓝，可点击，11px）
        github_label = QLabel(f"GitHub: {Config.GITHUB_REPO}")
        github_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #495057;
            }
            QLabel:hover {
                color: #339af0;
            }
        """)
        github_label.setAlignment(Qt.AlignCenter)
        github_label.setCursor(Qt.PointingHandCursor)
        github_label.mousePressEvent = lambda event: self._open_github(event)
        layout.addWidget(github_label)

        layout.addSpacing(8)

        # 问题反馈和查看详情链接（使用 QLabel + 手动控制下划线）
        link_layout = QHBoxLayout()
        link_layout.addStretch()

        # 创建问题反馈链接
        self.feedback_label = QLabel(I18n.tr('about_feedback', self.lang))
        self.feedback_label.setStyleSheet("QLabel { font-size: 11px; color: #339af0; }")
        self.feedback_label.setAlignment(Qt.AlignCenter)
        self.feedback_label.setCursor(Qt.PointingHandCursor)
        self.feedback_label.mousePressEvent = lambda event: self._open_issues(event)
        # 手动实现悬浮下划线效果
        self.feedback_label.enterEvent = lambda event: self._apply_link_hover_style(self.feedback_label)
        self.feedback_label.leaveEvent = lambda event: self._apply_link_normal_style(self.feedback_label)
        link_layout.addWidget(self.feedback_label)

        link_layout.addSpacing(20)

        # 创建查看详情链接
        self.details_label = QLabel(I18n.tr('about_details', self.lang))
        self.details_label.setStyleSheet("QLabel { font-size: 11px; color: #339af0; }")
        self.details_label.setAlignment(Qt.AlignCenter)
        self.details_label.setCursor(Qt.PointingHandCursor)
        self.details_label.mousePressEvent = lambda event: self._open_details(event)
        # 手动实现悬浮下划线效果
        self.details_label.enterEvent = lambda event: self._apply_link_hover_style(self.details_label)
        self.details_label.leaveEvent = lambda event: self._apply_link_normal_style(self.details_label)
        link_layout.addWidget(self.details_label)

        link_layout.addStretch()
        layout.addLayout(link_layout)

        layout.addStretch()

        # 按钮区域（120×36px）
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # 检查更新按钮（仅开源版显示）
        if Config.ENABLE_CHECK_UPDATE:
            check_update_btn = QPushButton(I18n.tr("btn_check_update", self.lang))
            check_update_btn.setFixedSize(120, 36)
            check_update_btn.setStyleSheet("""
                QPushButton {
                    background-color: #339af0;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #228be6;
                }
            """)
            check_update_btn.clicked.connect(self._check_update)
            btn_layout.addWidget(check_update_btn)

            btn_layout.addSpacing(10)

        # 关闭按钮
        close_btn = QPushButton(I18n.tr("btn_close", self.lang))
        close_btn.setFixedSize(120, 36)
        close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                border: 1px solid #adb5bd;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _open_github(self, event):
        """打开GitHub链接"""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(f"https://github.com/{Config.GITHUB_REPO}"))

    def _open_issues(self, event):
        """打开GitHub Issues页面（问题反馈）"""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(f"https://github.com/{Config.GITHUB_REPO}/issues"))

    def _open_details(self, event):
        """打开作者主页链接（查看详情）"""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(Config.APP_AUTHOR_LINK))

    def _apply_link_hover_style(self, label):
        """应用链接悬浮样式（蓝色+下划线）"""
        from PySide6.QtGui import QFont, QEnterEvent
        if isinstance(label, QLabel):
            label.setStyleSheet("QLabel { font-size: 11px; color: #228be6; }")
            font = QFont(label.font())
            font.setUnderline(True)
            label.setFont(font)

    def _apply_link_normal_style(self, label):
        """应用链接正常样式（蓝色+无下划线）"""
        from PySide6.QtGui import QFont
        if isinstance(label, QLabel):
            label.setStyleSheet("QLabel { font-size: 11px; color: #339af0; }")
            font = QFont(label.font())
            font.setUnderline(False)
            label.setFont(font)
    
    def _get_latest_version(self):
        """从 GitHub Pages 纯文本文件拉取最新版本号
        返回值: (版本号字符串, 错误信息字符串) 元组
            成功时: ("R11.7", None)
            失败时: (None, "错误描述")
        """
        import urllib.request
        import re

        req = urllib.request.Request(Config.UPDATE_URL)
        req.add_header('User-Agent', f"{Config.APP_NAME}/{Config.DISPLAY_VERSION}")

        try:
            with urllib.request.urlopen(req, timeout=15, context=self.ssl_context) as response:
                body = response.read().decode('utf-8').strip()
            # io 文件为 R 前缀四段（如 R11.7.0.0），本程序使用二段 RV.X，
            # 提取前两段（后两段固定 .0.0，忽略）。
            match = re.match(r'R(\d+)(?:\.(\d+))?', body)
            if not match:
                return None, None
            return f"R{match.group(1)}.{match.group(2) or 0}", None
        except Exception as e:
            return None, str(e)

    def _check_update(self):
        """检查更新（从 github.io 拉取版本号，下载落地页按语言区分）"""
        import re
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        # 拉取远程最新版本
        latest, err = self._get_latest_version()
        if not latest:
            QMessageBox.warning(self, I18n.tr("update_title", self.lang),
                                err or I18n.tr("update_tag_error", self.lang))
            return

        # 解析当前版本号与远程版本号为可比较数值
        latest_match = re.search(r'R(\d+(?:\.\d+)?)', latest)
        current_match = re.search(r'R(\d+(?:\.\d+)?)', Config.APP_VERSION)
        if not latest_match:
            QMessageBox.warning(self, I18n.tr("update_title", self.lang),
                                I18n.tr("update_tag_error", self.lang))
            return
        if not current_match:
            QMessageBox.warning(self, I18n.tr("update_title", self.lang),
                                I18n.tr("update_version_error", self.lang))
            return
        latest_version_num = float(latest_match.group(1))
        current_version = float(current_match.group(1))

        # 比较版本号
        if latest_version_num > current_version:
            # 下载落地页按语言区分（中文 Gitee / 其他 GitHub）
            releases_url = Config.GITEE_RELEASES if self.lang == 'zh' else Config.GITHUB_RELEASES

            # 发现新版本，弹窗询问是否前往下载
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(I18n.tr("update_title", self.lang))
            msg_box.setText(I18n.tr("update_found", self.lang).format(latest))
            msg_box.setIcon(QMessageBox.NoIcon)
            
            # 设置整体样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    font-size: 11px;
                }
                QMessageBox QLabel {
                    color: #495057;
                    font-size: 11px;
                    padding: 10px;
                }
            """)
            
            # 自定义按钮
            yes_btn = msg_box.addButton(I18n.tr("btn_yes", self.lang), QMessageBox.YesRole)
            no_btn = msg_box.addButton(I18n.tr("btn_no", self.lang), QMessageBox.NoRole)
            
            # 设置按钮样式
            yes_btn.setStyleSheet("""
                QPushButton {
                    background-color: #51cf66;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 24px;
                    min-width: 80px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #40c057;
                }
            """)
            
            no_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 24px;
                    min-width: 80px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #fa5252;
                }
            """)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == yes_btn:
                # 打开 releases 页面
                QDesktopServices.openUrl(QUrl(releases_url))
        else:
            # 当前已是最新版本（移除图标）
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(I18n.tr("update_title", self.lang))
            msg_box.setText(I18n.tr("update_latest", self.lang))
            msg_box.setIcon(QMessageBox.NoIcon)
            
            # 设置整体样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    font-size: 11px;
                }
                QMessageBox QLabel {
                    color: #495057;
                    font-size: 11px;
                    padding: 10px;
                }
            """)
            
            msg_box.exec()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 先加载配置文件中的语言设置
        config = load_config()
        self.current_lang = config.get('language', 'zh')
        self.sync_mode = config.get('sync_mode', 'newest')  # "default" or "newest"
        self.sync_type = config.get('sync_type', 'bidirectional')  # "bidirectional" or "unidirectional"
        self.unidirectional_mode = config.get('unidirectional_mode', 'diff')  # "diff" or "overwrite"
        self.sync_direction = config.get('sync_direction', 'removable_to_local')  # "removable_to_local" or "local_to_removable"
        self.extra_items_mode = config.get('extra_items_mode', 'keep')  # "keep" or "delete"
        
        # 加载名称并添加"目录"尾缀
        removable_prefix = config.get('removable_name', '')
        local_prefix = config.get('local_name', '')
        suffix = self.current_lang == "zh" and "目录" or " Directory"
        self.removable_name = removable_prefix + suffix if removable_prefix else "A" + suffix
        self.local_name = local_prefix + suffix if local_prefix else "B" + suffix
        
        self.setWindowTitle(I18n.tr("app_title", self.current_lang))
        self.setMinimumSize(1000, 700)
        
        self.wintogo_files = {}
        self.local_files = {}
        self.diff_results = []
        self.conflict_decisions = {}
        self.auto_scan_timer = None
        self.ignore_rules = []
        self.sync_rules = []
        self.sync_start_time = None
        self.sync_transferred_bytes = 0
        self._delete_both_dirs = set()
        
        # 强制创建原生窗口句柄（HWND），确保后续 winId() 调用有效
        self.winId()
        
        self._init_ui()
        self._load_saved_paths()
        # 初始化按钮状态
        self._update_sync_type_button()
        self._update_unidirectional_mode_button()
        self._update_extra_items_button()
        self._update_buttons_visibility()
        # 初始化头部箭头显示（根据同步类型和方向动态显示）
        self._update_header_status()
    
    def showEvent(self, event):
        """窗口显示后取消路径框选中态。"""
        super().showEvent(event)
        # 窗口显示后焦点可能落在路径框并自动全选文字，
        # 延迟到事件循环取消选中，避免初次启动路径框文字被高亮
        QTimer.singleShot(0, self._deselect_path_edits)

    def _deselect_path_edits(self):
        """取消路径输入框的选中态，并清除焦点。"""
        self.wintogo_edit.deselect()
        self.local_edit.deselect()
        # 把焦点转移到窗口本身，避免输入框保留焦点
        self.setFocus()
    
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        header_layout = QHBoxLayout()
        title_label = QLabel("📁 SyncGUI")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #339af0;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.version_label = QLabel(self._get_subtitle_text())
        self.version_label.setStyleSheet("font-size: 13px;")
        header_layout.addWidget(self.version_label)
        
        header_layout.addSpacing(16)
        
        self.lang_btn = AnimatedButton(I18n.tr("language_btn", self.current_lang))
        self.lang_btn.setMinimumSize(80, 36)
        hover_bg = "#3a3a3a" if _is_dark_mode() else "#f1f3f5"
        self.lang_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: """ + hover_bg + """;
                border: 1px solid #adb5bd;
            }
            QPushButton:disabled {
                """ + self._disabled_btn_qss("                ") + """
            }
        """)
        self.lang_btn.clicked.connect(self._toggle_language)
        header_layout.addWidget(self.lang_btn)
        
        # 关于按钮（小图标）
        self.about_btn = AnimatedButton("i")
        self.about_btn.setObjectName("aboutBtn")
        self.about_btn.setFixedSize(32, 32)
        self.about_btn.clicked.connect(self._show_about_dialog)
        header_layout.addWidget(self.about_btn)
        
        layout.addLayout(header_layout)
        
        self.dir_group = QGroupBox()
        self.dir_group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 0;
                padding-top: 0;
            }
        """)
        dir_layout = QVBoxLayout(self.dir_group)
        dir_layout.setSpacing(8)
        dir_layout.setContentsMargins(0, 0, 0, 0)

        label_width = 100

        # 移动介质目录行
        wintogo_layout = QHBoxLayout()
        self.wintogo_label = ClickableLabel(self.removable_name)
        self.wintogo_label.setFixedWidth(label_width)
        self.wintogo_label.setStyleSheet("font-size: 13px;")
        self.wintogo_label.clicked.connect(self._rename_removable)
        wintogo_layout.addWidget(self.wintogo_label)
        self.wintogo_edit = QLineEdit()
        self.wintogo_edit.setPlaceholderText(I18n.tr("removable_placeholder", self.current_lang).format(name=self._get_clean_name(self.removable_name)))
        self.wintogo_edit.textChanged.connect(self._on_path_changed)
        wintogo_layout.addWidget(self.wintogo_edit)
        self.wintogo_btn = AnimatedButton(I18n.tr("browse", self.current_lang))
        self.wintogo_btn.setObjectName("browseBtn")
        self.wintogo_btn.setMinimumWidth(80)
        self.wintogo_btn.clicked.connect(self._select_wintogo)
        wintogo_layout.addWidget(self.wintogo_btn)
        dir_layout.addLayout(wintogo_layout)

        # 本地目录行
        local_layout = QHBoxLayout()
        self.local_label = ClickableLabel(self.local_name)
        self.local_label.setFixedWidth(label_width)
        self.local_label.setStyleSheet("font-size: 13px;")
        self.local_label.clicked.connect(self._rename_local)
        local_layout.addWidget(self.local_label)
        self.local_edit = QLineEdit()
        self.local_edit.setPlaceholderText(I18n.tr("local_placeholder", self.current_lang).format(name=self._get_clean_name(self.local_name)))
        self.local_edit.textChanged.connect(self._on_path_changed)
        local_layout.addWidget(self.local_edit)
        self.local_btn = AnimatedButton(I18n.tr("browse", self.current_lang))
        self.local_btn.setObjectName("browseBtn")
        self.local_btn.setMinimumWidth(80)
        self.local_btn.clicked.connect(self._select_local)
        local_layout.addWidget(self.local_btn)
        dir_layout.addLayout(local_layout)
        
        # 提示标签：点击可修改名称（单独一行显示）
        self.rename_hint_label = QLabel(I18n.tr("click_to_rename", self.current_lang))
        self.rename_hint_label.setStyleSheet("font-size: 11px; color: #868e96;")
        dir_layout.addWidget(self.rename_hint_label)

        layout.addWidget(self.dir_group)
        
        # 第一行按钮：同步模式、默认模式、忽略规则、同步规则
        btn_layout_row1 = QHBoxLayout()
        btn_layout_row1.setSpacing(12)
        
        # 同步模式切换按钮（双向/单向）
        self.sync_type_btn = AnimatedButton(I18n.tr("sync_type_bidirectional", self.current_lang))
        self.sync_type_btn.setObjectName("browseBtn")
        self.sync_type_btn.setMinimumHeight(44)
        self.sync_type_btn.setMinimumWidth(110)
        self.sync_type_btn.clicked.connect(self._toggle_sync_type)
        btn_layout_row1.addWidget(self.sync_type_btn)
        
        # 默认模式按钮（默认模式/最新优先）
        self.mode_btn = AnimatedButton(I18n.tr("mode_default", self.current_lang))
        self.mode_btn.setObjectName("browseBtn")
        self.mode_btn.setMinimumHeight(44)
        self.mode_btn.setMinimumWidth(110)
        self.mode_btn.clicked.connect(self._toggle_mode)
        btn_layout_row1.addWidget(self.mode_btn)
        
        # 单向模式子模式按钮（差异同步/覆盖同步）
        self.unidirectional_mode_btn = AnimatedButton(I18n.tr("unidirectional_mode_diff", self.current_lang))
        self.unidirectional_mode_btn.setObjectName("browseBtn")
        self.unidirectional_mode_btn.setMinimumHeight(44)
        self.unidirectional_mode_btn.setMinimumWidth(110)
        self.unidirectional_mode_btn.clicked.connect(self._toggle_unidirectional_mode)
        self.unidirectional_mode_btn.setVisible(False)  # 默认隐藏，只在单向模式下显示
        btn_layout_row1.addWidget(self.unidirectional_mode_btn)
        
        # 方向切换按钮（A→B/B→A）
        direction_text = self._get_direction_text()
        self.direction_btn = AnimatedButton(direction_text)
        self.direction_btn.setObjectName("browseBtn")
        self.direction_btn.setMinimumHeight(44)
        self.direction_btn.setMinimumWidth(150)
        self.direction_btn.clicked.connect(self._change_sync_direction)
        self.direction_btn.setVisible(False)  # 默认隐藏，只在单向模式下显示
        btn_layout_row1.addWidget(self.direction_btn)
        
        # 多余项目处理按钮（保留多余项目/删除多余项目）
        self.extra_items_btn = AnimatedButton(I18n.tr("extra_items_keep", self.current_lang))
        self.extra_items_btn.setObjectName("browseBtn")
        self.extra_items_btn.setMinimumHeight(44)
        self.extra_items_btn.setMinimumWidth(130)
        self.extra_items_btn.clicked.connect(self._toggle_extra_items_mode)
        self.extra_items_btn.setVisible(False)  # 默认隐藏，只在单向模式下显示
        btn_layout_row1.addWidget(self.extra_items_btn)
        
        # 忽略规则按钮
        self.ignore_btn = AnimatedButton(I18n.tr("ignore_btn", self.current_lang))
        self.ignore_btn.setObjectName("browseBtn")
        self.ignore_btn.setMinimumHeight(44)
        self.ignore_btn.setMinimumWidth(100)
        self.ignore_btn.clicked.connect(self._show_ignore_dialog)
        btn_layout_row1.addWidget(self.ignore_btn)
        
        # 同步规则按钮
        self.sync_rule_btn = AnimatedButton(I18n.tr("sync_rule_btn", self.current_lang))
        self.sync_rule_btn.setObjectName("browseBtn")
        self.sync_rule_btn.setMinimumHeight(44)
        self.sync_rule_btn.setMinimumWidth(100)
        self.sync_rule_btn.clicked.connect(self._show_sync_rule_dialog)
        btn_layout_row1.addWidget(self.sync_rule_btn)
        
        btn_layout_row1.addStretch()
        layout.addLayout(btn_layout_row1)
        
        # 第二行按钮：扫描差异、执行同步
        btn_layout_row2 = QHBoxLayout()
        btn_layout_row2.setSpacing(12)
        
        self.scan_btn = AnimatedButton(I18n.tr("scan_btn", self.current_lang))
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.setFixedHeight(44)
        self.scan_btn.setFixedWidth(140)
        self.scan_btn.clicked.connect(self._start_scan)
        btn_layout_row2.addWidget(self.scan_btn)
        
        self.sync_btn = AnimatedButton(I18n.tr("sync_btn", self.current_lang))
        self.sync_btn.setObjectName("syncBtn")
        self.sync_btn.setFixedHeight(44)
        self.sync_btn.setFixedWidth(140)
        self.sync_btn.clicked.connect(self._execute_sync)
        self.sync_btn.setEnabled(False)
        btn_layout_row2.addWidget(self.sync_btn)
        
        btn_layout_row2.addStretch()
        layout.addLayout(btn_layout_row2)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(28)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel(I18n.tr("status_ready", self.current_lang))
        self.status_label.setStyleSheet("font-size: 13px; padding: 4px 0;")
        layout.addWidget(self.status_label)
        
        self.table_group = QGroupBox(I18n.tr("table_group_title", self.current_lang))
        self.table_group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 0;
                padding-top: 0;
                font-weight: 600;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0;
                padding: 0;
            }
        """)
        table_layout = QVBoxLayout(self.table_group)
        table_layout.setContentsMargins(0, 20, 0, 0)
        table_layout.setSpacing(8)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            I18n.tr("col_status", self.current_lang),
            I18n.tr("col_path", self.current_lang),
            I18n.tr("col_removable_size", self.current_lang),
            I18n.tr("col_local_size", self.current_lang)
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 110)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(self._get_table_style())
        table_layout.addWidget(self.table)
        
        layout.addWidget(self.table_group)
    
    def _get_table_style(self, fs=12, hd_fs=13):
        """根据系统深色/浅色模式生成表格交替行 QSS（参考 pyside6-AltRowStyle.md）"""
        dark = _is_dark_mode()
        if dark:
            return f"""
QTableWidget {{
    background-color: #252525;
    alternate-background-color: #2d2d2d;
    border: 1px solid #3a3a3a;
    font-size: {fs}px;
    color: #e0e0e0;
    gridline-color: #3a3a3a;
    selection-background-color: #3a6ba5;
    selection-color: white;
}}
QTableWidget::item {{
    color: #e0e0e0;
    padding: 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: #3a6ba5;
    color: white;
}}
QHeaderView::section {{
    border: 1px solid #3a3a3a;
    background-color: #1a1a1a;
    color: #e0e0e0;
    font-size: {hd_fs}px;
    font-weight: bold;
    padding: 10px;
}}
QHeaderView::section:last {{
    border-right: none;
}}
"""
        return f"""
QTableWidget {{
    background-color: #fafafa;
    alternate-background-color: #f5f5f5;
    border: 1px solid #d0d0d0;
    font-size: {fs}px;
    color: #2c3e50;
    gridline-color: #e0e0e0;
}}
QTableWidget::item {{
    color: #2c3e50;
    padding: 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: #3a6ba5;
    color: white;
}}
QHeaderView::section {{
    border: 1px solid #c0c0c0;
    background-color: #e8e8e8;
    color: #2c3e50;
    font-size: {hd_fs}px;
    font-weight: bold;
    padding: 10px;
}}
QHeaderView::section:last {{
    border-right: none;
}}
"""
    
    def _status_bg_color(self, r, g, b, alpha=200):
        """生成带透明度的状态背景色，使交替行颜色可透过显示"""
        return QColor(r, g, b, alpha)
    
    def _load_saved_paths(self):
        config = load_config()
        wintogo_path = config.get('A_dir', '')
        local_path = config.get('B_dir', '')
        ignore_rules = config.get('ignore_rules', [])
        sync_rules = config.get('sync_rules', [])

        # 加载目录名称并添加尾缀
        removable_prefix = config.get('removable_name', '')
        local_prefix = config.get('local_name', '')
        suffix = self.current_lang == "zh" and "目录" or " Directory"
        self.removable_name = removable_prefix + suffix if removable_prefix else "A" + suffix
        self.local_name = local_prefix + suffix if local_prefix else "B" + suffix

        if wintogo_path:
            self.wintogo_edit.setText(wintogo_path)
        if local_path:
            self.local_edit.setText(local_path)
        self.ignore_rules = ignore_rules
        self.sync_rules = sync_rules

        # 更新目录标签显示
        self._update_dir_labels()

        # 更新模式按钮显示
        self._update_mode_button()
    
    def _toggle_language(self):
        """切换语言"""
        self.current_lang = "en" if self.current_lang == "zh" else "zh"
        self._update_ui_language()
        # 保存语言设置到配置文件
        self._save_paths()
    
    def _toggle_sync_type(self):
        """切换同步类型（双向/单向）"""
        if self.sync_type == "bidirectional":
            self.sync_type = "unidirectional"
        else:
            self.sync_type = "bidirectional"
        # 切换同步类型时清除旧决策，刷新表格
        self.conflict_decisions.clear()
        self._delete_both_dirs.clear()
        self._update_table()
        self._update_sync_type_button()
        self._update_buttons_visibility()
        # 更新头部箭头显示
        self._update_header_status()
        # 保存同步类型设置到配置文件
        self._save_paths()
        # 自动触发扫描差异
        self._auto_scan_on_change()

    def _auto_scan_on_change(self):
        """在切换同步模式或方向时自动触发扫描差异"""
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        # 只有在两个目录都已设置且扫描按钮可用时才触发扫描
        if wintogo_dir and local_dir and self.scan_btn.isEnabled():
            # 检查目录是否存在
            if os.path.exists(wintogo_dir) and os.path.exists(local_dir):
                # 自动触发扫描
                self._start_scan()

    # ---- 扫描/同步期间统一禁用/恢复所有功能按钮 ----
    # 与 scan_btn / sync_btn 的 setEnabled(False) 灰色效果一致，
    # 避免扫描中切换模式导致状态与 diff_results 脱节
    def _get_feature_buttons(self):
        """返回所有功能按钮（不含扫描/同步按钮本身，二者已单独管理）。"""
        return [
            self.sync_type_btn,
            self.mode_btn,
            self.unidirectional_mode_btn,
            self.direction_btn,
            self.extra_items_btn,
            self.ignore_btn,
            self.sync_rule_btn,
            self.lang_btn,
            self.about_btn,
        ]

    def _set_feature_buttons_enabled(self, enabled: bool):
        """统一禁用/恢复功能按钮。"""
        for btn in self._get_feature_buttons():
            btn.setEnabled(enabled)

    @staticmethod
    def _disabled_btn_qss(indent: str = "                ") -> str:
        """返回内联样式中 QPushButton:disabled 块的 QSS，根据深色/浅色模式动态选择。
        indent: 内联样式的缩进字符串（默认 16 空格）。"""
        if _is_dark_mode():
            return (f"{indent}background-color: #2d2d2d;\n"
                    f"{indent}color: #adb5bd;\n"
                    f"{indent}border: 1px solid rgba(255, 255, 255, 0.2);")
        return (f"{indent}background-color: #adb5bd;\n"
                f"{indent}color: #f8f9fa;\n"
                f"{indent}border: none;")

    def _inactive_btn_style(self) -> str:
        """非激活态按钮 QSS：深色模式下使用深灰背景，避免在深色窗口中显为突兀的白块"""
        if _is_dark_mode():
            return """
                QPushButton {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    border: 1px solid rgba(255, 255, 255, 0.4);
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #383838;
                    border: 1px solid rgba(255, 255, 255, 0.7);
                }
                QPushButton:disabled {
                    background-color: #2d2d2d;
                    color: #adb5bd;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
            """
        return """
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
                color: #f8f9fa;
                border: none;
            }
        """

    def _update_sync_type_button(self):
        """更新同步类型按钮显示"""
        if self.sync_type == "unidirectional":
            self.sync_type_btn.setText(I18n.tr("sync_type_unidirectional", self.current_lang))
            self.sync_type_btn.setStyleSheet("""
                QPushButton {
                    background-color: #339af0;
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #228be6;
                }
                QPushButton:disabled {
                    """ + self._disabled_btn_qss("                    ") + """
                }
            """)
        else:
            self.sync_type_btn.setText(I18n.tr("sync_type_bidirectional", self.current_lang))
            # 双向同步模式：使用忽略规则/同步规则按钮的全局 browseBtn 样式（灰边框无背景）
            # 不设置内联样式，让全局 STYLESHEET 的 QPushButton + #browseBtn:disabled 规则生效
            self.sync_type_btn.setStyleSheet("")
        self.sync_type_btn.adjustSize()
    
    def _toggle_unidirectional_mode(self):
        """切换单向同步子模式（差异同步/覆盖同步）"""
        if self.unidirectional_mode == "diff":
            self.unidirectional_mode = "overwrite"
        else:
            self.unidirectional_mode = "diff"
        self._update_unidirectional_mode_button()
        # 保存单向同步子模式设置到配置文件
        self._save_paths()
        # 自动触发扫描差异
        self._auto_scan_on_change()
    
    def _update_unidirectional_mode_button(self):
        """更新单向同步子模式按钮显示"""
        if self.unidirectional_mode == "overwrite":
            self.unidirectional_mode_btn.setText(I18n.tr("unidirectional_mode_overwrite", self.current_lang))
            self.unidirectional_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fa5252;
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #e03131;
                }
                QPushButton:disabled {
                    """ + self._disabled_btn_qss("                    ") + """
                }
            """)
        else:
            self.unidirectional_mode_btn.setText(I18n.tr("unidirectional_mode_diff", self.current_lang))
            self.unidirectional_mode_btn.setStyleSheet(self._inactive_btn_style())
        self.unidirectional_mode_btn.adjustSize()
    
    def _toggle_extra_items_mode(self):
        """切换多余项目处理模式（保留/删除）"""
        if self.extra_items_mode == "keep":
            self.extra_items_mode = "delete"
        else:
            self.extra_items_mode = "keep"
        self._update_extra_items_button()
        # 保存多余项目处理模式设置到配置文件
        self._save_paths()
        # 自动触发扫描差异
        self._auto_scan_on_change()
    
    def _update_extra_items_button(self):
        """更新多余项目处理按钮显示"""
        if self.extra_items_mode == "delete":
            self.extra_items_btn.setText(I18n.tr("extra_items_delete", self.current_lang))
            self.extra_items_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fa5252;
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #e03131;
                }
                QPushButton:disabled {
                    """ + self._disabled_btn_qss("                    ") + """
                }
            """)
        else:
            self.extra_items_btn.setText(I18n.tr("extra_items_keep", self.current_lang))
            self.extra_items_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2f9e44;
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #238636;
                }
                QPushButton:disabled {
                    """ + self._disabled_btn_qss("                    ") + """
                }
            """)
        self.extra_items_btn.adjustSize()
    
    def _change_sync_direction(self):
        """切换同步方向"""
        if self.sync_direction == "removable_to_local":
            self.sync_direction = "local_to_removable"
        else:
            self.sync_direction = "removable_to_local"
        
        # 更新按钮文本和尺寸
        self.direction_btn.setText(self._get_direction_text())
        self.direction_btn.adjustSize()
        
        # 更新头部箭头显示
        self._update_header_status()
        # 保存同步方向设置到配置文件
        self._save_paths()
        # 自动触发扫描差异
        self._auto_scan_on_change()
    
    def _fade_widget(self, widget, visible, duration=200, callback=None):
        """
        淡入淡出动画
        
        Args:
            widget: 要动画的控件
            visible: True 显示（淡入），False 隐藏（淡出）
            duration: 动画持续时间（毫秒）
            callback: 动画完成后的回调函数
        """
        # 创建透明度效果
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        # 创建动画
        animation = QPropertyAnimation(effect, QByteArray(b"opacity"))
        animation.setDuration(duration)
        
        if visible:
            # 淡入：从0到1
            widget.setVisible(True)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
        else:
            # 淡出：从1到0
            animation.setStartValue(1.0)
            animation.setEndValue(0.0)
            # 动画完成后隐藏控件
            animation.finished.connect(lambda: widget.setVisible(False))
        
        # 如果有回调函数，动画完成后执行
        if callback:
            animation.finished.connect(callback)
        
        animation.start()
        
        # 保存动画对象，防止被垃圾回收
        if not hasattr(self, '_fade_animations'):
            self._fade_animations = []
        self._fade_animations.append(animation)
    
    def _update_buttons_visibility(self):
        """更新按钮显示/隐藏逻辑（带淡入淡出动画，先隐藏再显示）"""
        if self.sync_type == "unidirectional":
            # 单向模式下：先隐藏双向模式按钮，等待动画完成后再显示单向模式按钮
            # 第一步：淡出隐藏双向模式按钮
            def fade_in_unidirectional_buttons():
                """淡入显示单向模式按钮"""
                self._fade_widget(self.unidirectional_mode_btn, True)
                self._fade_widget(self.direction_btn, True)
                self._fade_widget(self.extra_items_btn, True)
                # 更新方向按钮文本
                self.direction_btn.setText(self._get_direction_text())
            
            # 先淡出隐藏双向模式按钮，完成后淡入显示单向模式按钮
            self._fade_widget(self.mode_btn, False, callback=fade_in_unidirectional_buttons)
            self._fade_widget(self.sync_rule_btn, False)
        else:
            # 双向模式下：先隐藏单向模式按钮，等待动画完成后再显示双向模式按钮
            # 第一步：淡出隐藏单向模式按钮
            def fade_in_bidirectional_buttons():
                """淡入显示双向模式按钮"""
                self._fade_widget(self.mode_btn, True)
                # 同步规则按钮的显示由_update_mode_button控制
                self._update_mode_button()
            
            # 先淡出隐藏单向模式按钮，完成后淡入显示双向模式按钮
            self._fade_widget(self.unidirectional_mode_btn, False)
            self._fade_widget(self.direction_btn, False)
            self._fade_widget(self.extra_items_btn, False, callback=fade_in_bidirectional_buttons)
    
    def _toggle_mode(self):
        """切换同步模式"""
        if self.sync_mode == "default":
            self.sync_mode = "newest"
        else:
            self.sync_mode = "default"
        # 模式切换时清除之前的冲突决策状态，刷新表格
        self.conflict_decisions.clear()
        self._delete_both_dirs.clear()
        self._update_table()
        self._update_mode_button()
        # 保存同步模式设置到配置文件
        self._save_paths()
        # 自动触发扫描差异，与 _toggle_unidirectional_mode 行为一致
        self._auto_scan_on_change()

    def _rename_removable(self):
        """修改移动介质目录名称"""
        dialog = RenameDialog(self.removable_name, self.current_lang, self)
        if dialog.exec() == QDialog.Accepted:
            # 保存前缀，使用时添加"目录"尾缀
            self.removable_name = dialog.get_new_name() + self._get_suffix()
            self._update_dir_labels()
            self._save_paths()

    def _rename_local(self):
        """修改本地目录名称"""
        dialog = RenameDialog(self.local_name, self.current_lang, self)
        if dialog.exec() == QDialog.Accepted:
            # 保存前缀，使用时添加"目录"尾缀
            self.local_name = dialog.get_new_name() + self._get_suffix()
            self._update_dir_labels()
            self._save_paths()
    
    def _get_suffix(self):
        """获取目录尾缀"""
        return self.current_lang == "zh" and "目录" or " Directory"
    
    def _get_clean_name(self, name):
        """去掉名称的目录尾缀，得到纯名称前缀"""
        if name.endswith("目录"):
            return name[:-2]
        elif name.endswith(" Directory"):
            return name[:-10]
        elif name.endswith("Directory"):
            return name[:-9]
        return name
    
    def _get_subtitle_text(self, status_key="header_subtitle"):
        """获取带自定义名称的 subtitle 文本"""
        # 提取名称前缀（去掉"目录"尾缀）
        removable_prefix = self._get_clean_name(self.removable_name)
        local_prefix = self._get_clean_name(self.local_name)

        # 使用翻译模板并填充自定义名称
        template = I18n.tr(status_key, self.current_lang)
        return template.format(a=removable_prefix, b=local_prefix)

    def _get_direction_text(self):
        """获取方向按钮文本"""
        if self.sync_direction == "removable_to_local":
            template = I18n.tr("direction_removable_to_local", self.current_lang)
        else:
            template = I18n.tr("direction_local_to_removable", self.current_lang)

        # 提取名称前缀（去掉"目录"尾缀）
        removable_prefix = self._get_clean_name(self.removable_name)
        local_prefix = self._get_clean_name(self.local_name)

        return template.format(a=removable_prefix, b=local_prefix)

    def _update_dir_labels(self):
        """更新目录标签显示（根据当前语言动态更新后缀）"""
        # 提取名称前缀（去掉旧后缀）
        removable_prefix = self._get_clean_name(self.removable_name)
        local_prefix = self._get_clean_name(self.local_name)

        # 根据当前语言添加新后缀
        suffix = self._get_suffix()
        self.removable_name = removable_prefix + suffix
        self.local_name = local_prefix + suffix

        # 更新标签显示
        self.wintogo_label.setText(self.removable_name)
        self.local_label.setText(self.local_name)
        self.rename_hint_label.setText(I18n.tr("click_to_rename", self.current_lang))
        # 更新右上角名称显示
        self.version_label.setText(self._get_subtitle_text())
        # 更新方向按钮显示
        if self.sync_type == "unidirectional":
            self.direction_btn.setText(self._get_direction_text())
            self.direction_btn.adjustSize()
        # 刷新差异列表以显示新名称
        self._update_table()

    def _update_mode_button(self):
        """更新模式按钮显示（带淡入淡出动画）"""
        if self.sync_mode == "newest":
            self.mode_btn.setText(I18n.tr("mode_newest", self.current_lang))
            self.mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #339af0;
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #228be6;
                }
                QPushButton:disabled {
                    """ + self._disabled_btn_qss("                    ") + """
                }
            """)
            # 最新优先模式下隐藏同步规则按钮（不使用同步规则）
            self._fade_widget(self.sync_rule_btn, False)
        else:
            self.mode_btn.setText(I18n.tr("mode_default", self.current_lang))
            # 默认模式（手动选择）：使用忽略规则/同步规则按钮的全局 browseBtn 样式（灰边框无背景）
            # 不设置内联样式，让全局 STYLESHEET 的 QPushButton + #browseBtn:disabled 规则生效
            self.mode_btn.setStyleSheet("")
            # 默认模式下显示同步规则按钮（仅在双向模式下）
            if self.sync_type == "bidirectional":
                self._fade_widget(self.sync_rule_btn, True)
        self.mode_btn.adjustSize()
    
    def _update_ui_language(self):
        """更新界面语言"""
        lang = self.current_lang

        # 更新窗口标题
        self.setWindowTitle(I18n.tr("app_title", lang))

        # 更新头部（根据同步类型和方向动态显示箭头）
        self._update_header_status()

        # 强制更新所有按钮文本和大小
        self.lang_btn.setText(I18n.tr("language_btn", lang))
        self.lang_btn.setMinimumWidth(80)
        self.lang_btn.updateGeometry()

        # 更新目录设置（使用自定义名称）
        self._update_dir_labels()
        self.wintogo_edit.setPlaceholderText(I18n.tr("removable_placeholder", lang).format(name=self._get_clean_name(self.removable_name)))
        self.wintogo_btn.setText(I18n.tr("browse", lang))
        self.wintogo_btn.setMinimumWidth(80)
        self.wintogo_btn.updateGeometry()
        self.local_edit.setPlaceholderText(I18n.tr("local_placeholder", lang).format(name=self._get_clean_name(self.local_name)))
        self.local_btn.setText(I18n.tr("browse", lang))
        self.local_btn.setMinimumWidth(80)
        self.local_btn.updateGeometry()
        
        # 更新按钮
        self.scan_btn.setText(I18n.tr("scan_btn", lang))
        self.sync_btn.setText(I18n.tr("sync_btn", lang))
        self.ignore_btn.setText(I18n.tr("ignore_btn", lang))
        self.ignore_btn.setMinimumWidth(100)
        self.ignore_btn.updateGeometry()
        self.sync_rule_btn.setText(I18n.tr("sync_rule_btn", lang))
        self.sync_rule_btn.setMinimumWidth(100)
        self.sync_rule_btn.updateGeometry()
        self._update_sync_type_button()
        self._update_unidirectional_mode_button()
        # 更新方向切换按钮文本
        self.direction_btn.setText(self._get_direction_text())
        self.direction_btn.updateGeometry()
        self._update_mode_button()
        
        # 更新状态
        self.status_label.setText(I18n.tr("status_ready", lang))
        
        # 更新差异列表标题
        self.table_group.setTitle(I18n.tr("table_group_title", lang))
        
        # 更新表格
        self.table.setHorizontalHeaderLabels([
            I18n.tr("col_status", lang),
            I18n.tr("col_path", lang),
            I18n.tr("col_removable_size", lang),
            I18n.tr("col_local_size", lang)
        ])
        self.table.setStyleSheet(self._get_table_style())
        
        # 如果有差异结果，重新刷新表格
        if self.diff_results:
            self._update_table()
    
    def _save_paths(self):
        # 提取前缀（去掉"目录"尾缀）保存到配置
        removable_prefix = self.removable_name
        if removable_prefix.endswith("目录"):
            removable_prefix = removable_prefix[:-2]
        elif removable_prefix.endswith("Directory"):
            removable_prefix = removable_prefix[:-9]
        
        local_prefix = self.local_name
        if local_prefix.endswith("目录"):
            local_prefix = local_prefix[:-2]
        elif local_prefix.endswith("Directory"):
            local_prefix = local_prefix[:-9]
        
        # 先加载现有配置，再更新，避免覆盖其他模块写入的字段（如参考信息）
        config = load_config()
        config.update({
            'A_dir': self.wintogo_edit.text().strip(),
            'B_dir': self.local_edit.text().strip(),
            'ignore_rules': self.ignore_rules,
            'sync_rules': self.sync_rules,
            'language': self.current_lang,
            'sync_mode': self.sync_mode,
            'sync_type': self.sync_type,
            'unidirectional_mode': self.unidirectional_mode,
            'sync_direction': self.sync_direction,
            'extra_items_mode': self.extra_items_mode,
            'removable_name': removable_prefix,
            'local_name': local_prefix
        })
        save_config(config)
    
    def _show_ignore_dialog(self):
        dialog = IgnoreRulesDialog(self.ignore_rules, self.current_lang, self)
        if dialog.exec() == QDialog.Accepted:
            self.ignore_rules = dialog.get_rules()
            self._save_paths()
            saved_text = self.current_lang == "zh" and f"✅ 已保存 {len(self.ignore_rules)} 条忽略规则" or f"✅ Saved {len(self.ignore_rules)} ignore rules"
            self.status_label.setText(saved_text)
            self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
            
            wintogo_dir = self.wintogo_edit.text().strip()
            local_dir = self.local_edit.text().strip()
            if wintogo_dir and local_dir:
                if os.path.exists(wintogo_dir) and os.path.exists(local_dir):
                    if wintogo_dir != local_dir:
                        self._start_scan()
    
    def _show_sync_rule_dialog(self):
        dialog = SyncRulesDialog(self.sync_rules, self.current_lang, self)
        if dialog.exec() == QDialog.Accepted:
            self.sync_rules = dialog.get_rules()
            self._save_paths()
            saved_text = self.current_lang == "zh" and f"✅ 已保存 {len(self.sync_rules)} 条同步规则" or f"✅ Saved {len(self.sync_rules)} sync rules"
            self.status_label.setText(saved_text)
            self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
    
    def _show_about_dialog(self):
        """显示关于弹窗"""
        dialog = AboutDialog(self.current_lang, self)
        dialog.exec()
    
    def _on_path_changed(self):
        if self.auto_scan_timer:
            self.auto_scan_timer.stop()
        
        self.auto_scan_timer = QTimer()
        self.auto_scan_timer.setSingleShot(True)
        self.auto_scan_timer.timeout.connect(self._auto_scan)
        self.auto_scan_timer.start(500)
    
    def _auto_scan(self):
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()
        
        if wintogo_dir and local_dir:
            if os.path.exists(wintogo_dir) and os.path.exists(local_dir):
                if wintogo_dir != local_dir:
                    self._start_scan()
    
    def _select_wintogo(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择 WinToGo 目录")
        if dir_path:
            self.wintogo_edit.setText(dir_path)
            self._save_paths()
    
    def _select_local(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择本地目录")
        if dir_path:
            self.local_edit.setText(dir_path)
            self._save_paths()
    
    def _start_scan(self):
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        if not wintogo_dir or not local_dir:
            QMessageBox.warning(self, "警告", "请选择 WinToGo 目录和本地目录")
            return

        if wintogo_dir == local_dir:
            QMessageBox.warning(self, "警告", "WinToGo 目录和本地目录不能相同")
            return

        if not os.path.exists(wintogo_dir):
            QMessageBox.warning(self, "警告", "WinToGo 目录不存在")
            return

        if not os.path.exists(local_dir):
            QMessageBox.warning(self, "警告", "本地目录不存在")
            return

        self._save_paths()

        self.scan_btn.setEnabled(False)
        self.sync_btn.setEnabled(False)
        self._set_feature_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("扫描中... %p%")
        self.status_label.setText("🔍 正在扫描目录...")
        self.status_label.setStyleSheet("color: #1971c2; font-size: 13px; padding: 4px 0;")
        self.diff_results = []
        self.conflict_decisions = {}

        self.scan_worker = ScanWorker(wintogo_dir, local_dir, self.ignore_rules)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.start()
    
    def _on_scan_progress(self, current: int, total: int):
        if total > 0:
            self.progress_bar.setValue(int(current / total * 50))
    
    def _on_scan_finished(self, wintogo_files: dict, local_files: dict):
        self.wintogo_files = wintogo_files
        self.local_files = local_files
        
        self.progress_bar.setFormat("比对中... %p%")
        self.status_label.setText("🔍 正在比对文件...")
        
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()
        
        self.compare_worker = CompareWorker(
            wintogo_files, local_files, wintogo_dir, local_dir,
            self.sync_type, self.unidirectional_mode, self.sync_direction,
            self.extra_items_mode
        )
        self.compare_worker.progress.connect(self._on_compare_progress)
        self.compare_worker.finished.connect(self._on_compare_finished)
        self.compare_worker.start()
    
    def _on_compare_progress(self, current: int, total: int):
        if total > 0:
            self.progress_bar.setValue(50 + int(current / total * 50))
    
    def _on_compare_finished(self, results: list):
        self.diff_results = results
        self._update_table()

        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self._set_feature_buttons_enabled(True)

        only_one_side = [r for r in results if r.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)]
        conflicts = [r for r in results if r.status == FileStatus.CONFLICT]
        mtime_diffs = [r for r in results if r.status == FileStatus.MTIME_DIFF]
        sync_needed = [r for r in results if r.status != FileStatus.SAME]

        if sync_needed:
            self.sync_btn.setEnabled(True)
            status_parts = []
            if only_one_side:
                status_parts.append(f"{len(only_one_side)} 个独有文件")
            if conflicts:
                status_parts.append(f"{len(conflicts)} 个冲突")
            if mtime_diffs:
                status_parts.append(f"{len(mtime_diffs)} 个时间差异")

            status_text = "、".join(status_parts)
            if conflicts or mtime_diffs:
                self.status_label.setText(f"⚠️ 发现 {len(sync_needed)} 个差异项：{status_text}")
                self.status_label.setStyleSheet("color: #e67700; font-size: 13px; padding: 4px 0;")
            else:
                self.status_label.setText(f"📋 发现 {len(sync_needed)} 个差异项：{status_text}")
                self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
        else:
            self.status_label.setText("✅ 未发现差异项，无需同步")
            self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
    
    def _update_table(self):
        self.table.setRowCount(0)
        
        lang = self.current_lang
        
        # 提取名称前缀（去掉"目录"尾缀）
        removable_prefix = self.removable_name
        if removable_prefix.endswith("目录"):
            removable_prefix = removable_prefix[:-2]
        elif removable_prefix.endswith("Directory"):
            removable_prefix = removable_prefix[:-9]
        
        local_prefix = self.local_name
        if local_prefix.endswith("目录"):
            local_prefix = local_prefix[:-2]
        elif local_prefix.endswith("Directory"):
            local_prefix = local_prefix[:-9]
        
        # 构建状态文字
        removable_only_text = lang == "zh" and f"{removable_prefix}独有" or f"{removable_prefix} Only"
        local_only_text = lang == "zh" and f"{local_prefix}独有" or f"{local_prefix} Only"
        
        # 根据同步模式设置不同的颜色
        if self.sync_type == "unidirectional":
            # 单向同步模式
            if self.unidirectional_mode == "overwrite":
                # 覆盖同步模式
                # 根据同步方向决定颜色：
                # - 源独有：绿色（准备同步至目标的新项目）
                # - 目标独有：红色（准备删除目标的项目）
                if self.sync_direction == "removable_to_local":
                    # 介质 → 本地：源是介质，目标是本地
                    status_map = {
                        FileStatus.WINTOGO_ONLY: (removable_only_text, self._status_bg_color(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.LOCAL_ONLY: (local_only_text, self._status_bg_color(255, 245, 255)),  # 红色：目标独有，将被删除
                        FileStatus.SAME: (I18n.tr("status_same", lang), self._status_bg_color(248, 249, 250)),
                        FileStatus.CONFLICT: (I18n.tr("status_conflict", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (I18n.tr("status_mtime_diff", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
                else:
                    # 本地 → 介质：源是本地，目标是介质
                    status_map = {
                        FileStatus.LOCAL_ONLY: (local_only_text, self._status_bg_color(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.WINTOGO_ONLY: (removable_only_text, self._status_bg_color(255, 245, 245)),  # 纅色：目标独有，准备删除
                        FileStatus.SAME: (I18n.tr("status_same", lang), self._status_bg_color(248, 249, 250)),
                        FileStatus.CONFLICT: (I18n.tr("status_conflict", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (I18n.tr("status_mtime_diff", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
            else:
                # 差异同步模式
                # 根据同步方向决定颜色：
                # - 源独有：绿色（准备同步至目标的新项目）
                # - 目标独有：红色（准备删除目标的项目）
                if self.sync_direction == "removable_to_local":
                    # 介质 → 本地：源是介质，目标是本地
                    status_map = {
                        FileStatus.WINTOGO_ONLY: (removable_only_text, self._status_bg_color(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.LOCAL_ONLY: (local_only_text, self._status_bg_color(255, 245, 255)),  # 红色：目标独有，将被删除
                        FileStatus.SAME: (I18n.tr("status_same", lang), self._status_bg_color(248, 249, 250)),
                        FileStatus.CONFLICT: (I18n.tr("status_conflict", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (I18n.tr("status_mtime_diff", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
                else:
                    # 本地 → 介质：源是本地，目标是介质
                    status_map = {
                        FileStatus.LOCAL_ONLY: (local_only_text, self._status_bg_color(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.WINTOGO_ONLY: (removable_only_text, self._status_bg_color(255, 245, 255)),  # 红色：目标独有，将被删除
                        FileStatus.SAME: (I18n.tr("status_same", lang), self._status_bg_color(248, 249, 250)),
                        FileStatus.CONFLICT: (I18n.tr("status_conflict", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (I18n.tr("status_mtime_diff", lang), self._status_bg_color(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
        else:
            # 双向同步模式
            status_map = {
                FileStatus.WINTOGO_ONLY: (removable_only_text, self._status_bg_color(227, 245, 255)),  # 绿色：仅一方存在
                FileStatus.LOCAL_ONLY: (local_only_text, self._status_bg_color(227, 245, 255)),  # 绿色：仅一方存在
                FileStatus.SAME: (I18n.tr("status_same", lang), self._status_bg_color(248, 249, 250)),
                FileStatus.CONFLICT: (I18n.tr("status_conflict", lang), self._status_bg_color(255, 243, 214)),  # 黄色：双方都存在的差异项目
                FileStatus.MTIME_DIFF: (I18n.tr("status_mtime_diff", lang), self._status_bg_color(255, 243, 214)),  # 黄色：双方都存在的差异项目
            }
        
        for diff in self.diff_results:
            if diff.status == FileStatus.SAME:
                continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            status_text, color = status_map[diff.status]
            status_item = QTableWidgetItem(status_text)
            status_item.setBackground(color)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, status_item)
            
            # 整行设置背景色
            path_item = QTableWidgetItem(diff.relative_path)
            path_item.setBackground(color)
            path_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 1, path_item)
            
            wintogo_size = ""
            if diff.wintogo_info:
                if diff.wintogo_info.is_symlink:
                    wintogo_size = lang == "zh" and "[链接]" or "[Link]"
                elif diff.wintogo_info.is_dir:
                    wintogo_size = lang == "zh" and "[目录]" or "[Dir]"
                else:
                    wintogo_size = self._format_size(diff.wintogo_info.size)
            wintogo_item = QTableWidgetItem(wintogo_size)
            wintogo_item.setBackground(color)
            wintogo_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, wintogo_item)
            
            local_size = ""
            if diff.local_info:
                if diff.local_info.is_symlink:
                    local_size = lang == "zh" and "[链接]" or "[Link]"
                elif diff.local_info.is_dir:
                    local_size = lang == "zh" and "[目录]" or "[Dir]"
                else:
                    local_size = self._format_size(diff.local_info.size)
            local_item = QTableWidgetItem(local_size)
            local_item.setBackground(color)
            local_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, local_item)
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _get_parent_dir(self, relative_path: str) -> str:
        parent = os.path.dirname(relative_path)
        return parent if parent else ""
    
    def _is_in_sync_rule(self, relative_path: str) -> bool:
        normalized = relative_path.replace('\\', '/')
        for rule in self.sync_rules:
            rule_normalized = rule.replace('\\', '/')
            if not rule_normalized.endswith('/'):
                rule_normalized += '/'
            rule_base = rule_normalized.rstrip('/')
            
            if normalized == rule_base:
                return True
            if normalized.startswith(rule_normalized):
                return True
        return False
    
    def _get_subdir_for_rule(self, relative_path: str, is_dir: bool = False) -> str:
        normalized = relative_path.replace('\\', '/')
        for rule in self.sync_rules:
            rule_normalized = rule.replace('\\', '/')
            if not rule_normalized.endswith('/'):
                rule_normalized += '/'
            rule_base = rule_normalized.rstrip('/')
            
            if normalized == rule_base:
                return ""
            
            if normalized.startswith(rule_normalized):
                remaining = normalized[len(rule_normalized):]
                if not remaining:
                    return ""
                
                parts = remaining.split('/')
                first_subdir = parts[0]
                
                if is_dir or len(parts) > 1:
                    return rule_normalized + first_subdir + '/'
                else:
                    return ""
        return ""
    
    def _execute_sync(self):
        sync_needed = [r for r in self.diff_results if r.status != FileStatus.SAME]
        
        lang = self.current_lang
        # 初始化 delete_both 路径记录集，所有同步模式共享此实例变量
        self._delete_both_dirs = set()
        
        if not sync_needed:
            QMessageBox.information(self, 
                lang == "zh" and "提示" or "Info",
                I18n.tr("msg_no_diff", lang))
            return
        
        # 单向同步模式
        if self.sync_type == "unidirectional":
            self._execute_unidirectional_sync(sync_needed, lang)
            return
        
        # 最新优先模式：自动选择较新版本，不弹窗询问
        if self.sync_mode == "newest":
            self._execute_newest_mode_sync(sync_needed, lang)
            return
        
        # 默认模式：弹窗询问
        rule_diffs = defaultdict(list)
        other_diffs = []
        
        for diff in sync_needed:
            if self._is_in_sync_rule(diff.relative_path):
                is_dir = False
                if diff.wintogo_info and diff.wintogo_info.is_dir:
                    is_dir = True
                elif diff.local_info and diff.local_info.is_dir:
                    is_dir = True
                subdir = self._get_subdir_for_rule(diff.relative_path, is_dir)
                if subdir:
                    rule_diffs[subdir].append(diff)
                else:
                    other_diffs.append(diff)
            else:
                other_diffs.append(diff)
        
        for subdir, diff_list in rule_diffs.items():
            dialog = DirSyncDialog(subdir, diff_list, lang, self.removable_name, self.local_name, self)
            if dialog.exec() == QDialog.Accepted:
                direction = dialog.get_direction()
                for diff in diff_list:
                    if direction == "wintogo_to_local":
                        if diff.status == FileStatus.WINTOGO_ONLY:
                            self.conflict_decisions[diff.relative_path] = "to_local"
                        elif diff.status == FileStatus.LOCAL_ONLY:
                            self.conflict_decisions[diff.relative_path] = "delete_local"
                        elif diff.status == FileStatus.CONFLICT:
                            self.conflict_decisions[diff.relative_path] = "wintogo_to_local"
                        elif diff.status == FileStatus.MTIME_DIFF:
                            self.conflict_decisions[diff.relative_path] = "wintogo_to_local"
                        else:
                            self.conflict_decisions[diff.relative_path] = "skip"
                    elif direction == "local_to_wintogo":
                        if diff.status == FileStatus.WINTOGO_ONLY:
                            self.conflict_decisions[diff.relative_path] = "delete_wintogo"
                        elif diff.status == FileStatus.LOCAL_ONLY:
                            self.conflict_decisions[diff.relative_path] = "to_wintogo"
                        elif diff.status == FileStatus.CONFLICT:
                            self.conflict_decisions[diff.relative_path] = "local_to_wintogo"
                        elif diff.status == FileStatus.MTIME_DIFF:
                            self.conflict_decisions[diff.relative_path] = "local_to_wintogo"
                        else:
                            self.conflict_decisions[diff.relative_path] = "skip"
                    elif direction == "delete_both":
                        # 记录此路径，同步完成后清理其下的空目录
                        self._delete_both_dirs.add(subdir)
                        if diff.status == FileStatus.WINTOGO_ONLY:
                            self.conflict_decisions[diff.relative_path] = "delete_wintogo"
                        elif diff.status == FileStatus.LOCAL_ONLY:
                            self.conflict_decisions[diff.relative_path] = "delete_local"
                        elif diff.status == FileStatus.CONFLICT:
                            self.conflict_decisions[diff.relative_path] = "delete_both"
                        elif diff.status == FileStatus.MTIME_DIFF:
                            self.conflict_decisions[diff.relative_path] = "delete_both"
                        else:
                            self.conflict_decisions[diff.relative_path] = "skip"
                    else:
                        self.conflict_decisions[diff.relative_path] = "skip"
                # 更新表格显示
                self._update_table()
            elif dialog.cancel_sync:
                # 取消本次同步，清除已选择的状态并刷新表格
                self.conflict_decisions.clear()
                self._delete_both_dirs.clear()
                self._update_table()
                return
            else:
                for diff in diff_list:
                    self.conflict_decisions[diff.relative_path] = "skip"
                # 更新表格显示
                self._update_table()
        
        dir_diffs = defaultdict(list)
        for diff in other_diffs:
            parent_dir = self._get_parent_dir(diff.relative_path)
            dir_diffs[parent_dir].append(diff)

        # 收集需要逐个决策的 diff（按 独有 → 冲突 → 时间差异 顺序）
        manual_diffs = []
        for diff in other_diffs:
            if diff.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY,
                               FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
                if diff.relative_path not in self.conflict_decisions:
                    manual_diffs.append(diff)

        # 计算每个 diff 的 same_dir_count（同目录同状态未决策数量 - 1）
        same_dir_counts = {}
        for diff in manual_diffs:
            parent_dir = self._get_parent_dir(diff.relative_path)
            same_dir = [d for d in dir_diffs[parent_dir]
                        if d.status == diff.status
                        and d.relative_path not in self.conflict_decisions]
            same_dir_counts[diff.relative_path] = len(same_dir) - 1

        if manual_diffs:
            wizard = ManualSyncWizard(manual_diffs, same_dir_counts, lang,
                                       self.removable_name, self.local_name, self)
            wizard.exec()

            if wizard.cancel_sync:
                self.conflict_decisions.clear()
                self._delete_both_dirs.clear()
                self._update_table()
                return

            # 合并向导决策
            self.conflict_decisions.update(wizard.decisions)

            # 向导未触及的项（用户中途关闭窗口等）默认跳过
            for diff in manual_diffs:
                if diff.relative_path not in self.conflict_decisions:
                    self.conflict_decisions[diff.relative_path] = "skip"

        self._update_table()
        
        # 统计源独有项目（WINTOGO_ONLY 和 LOCAL_ONLY）
        copy_count = len([r for r in self.diff_results 
                         if r.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)
                         and self.conflict_decisions.get(r.relative_path, "").startswith("to_")])
        delete_count = len([r for r in self.diff_results 
                           if r.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)
                           and self.conflict_decisions.get(r.relative_path, "").startswith("delete_")])
        
        # 统计冲突项和时间差异项的同步数量
        conflict_sync_count = len([r for r in self.diff_results 
                                   if r.status == FileStatus.CONFLICT
                                   and "_to_" in self.conflict_decisions.get(r.relative_path, "")])
        conflict_delete_count = len([r for r in self.diff_results 
                                     if r.status == FileStatus.CONFLICT
                                     and self.conflict_decisions.get(r.relative_path, "") == "delete_both"])
        mtime_sync_count = len([r for r in self.diff_results 
                                if r.status == FileStatus.MTIME_DIFF
                                and "_to_" in self.conflict_decisions.get(r.relative_path, "")])
        mtime_delete_count = len([r for r in self.diff_results 
                                  if r.status == FileStatus.MTIME_DIFF
                                  and self.conflict_decisions.get(r.relative_path, "") == "delete_both"])
        
        # 统计跳过项目
        skip_count = len([r for r in self.diff_results 
                         if self.conflict_decisions.get(r.relative_path) == "skip"])
        
        # 总同步数量 = 源独有 + 冲突项同步 + 时间差异项同步
        sync_count = copy_count + conflict_sync_count + mtime_sync_count
        # 总删除数量 = 源独有删除 + 冲突项删除 + 时间差异项删除
        total_delete_count = delete_count + conflict_delete_count + mtime_delete_count
        
        msg = f"确定要执行同步操作吗？\n\n"
        if sync_count > 0:
            msg += f"📋 同步文件: {sync_count} 个\n"
        if total_delete_count > 0:
            msg += f"🗑️ 删除文件: {total_delete_count} 个\n"
        if skip_count > 0:
            msg += f"⏭️ 跳过: {skip_count} 个\n"
        msg += "\n此操作不可撤销！"
        
        dialog = ConfirmSyncDialog("确认同步", msg, self.current_lang, self)
        dialog.exec()
        if not dialog.is_confirmed():
            # 取消同步：清除已选决策并刷新表格
            self.conflict_decisions.clear()
            self._delete_both_dirs.clear()
            self._update_table()
            return
        
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        self.sync_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self._set_feature_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("同步中... 准备中")
        self.status_label.setText("📤 正在同步文件...")
        self.status_label.setStyleSheet("color: #1971c2; font-size: 13px; padding: 4px 0;")

        self.sync_start_time = time.time()
        self.sync_transferred_bytes = 0

        self.sync_worker = SyncWorker(
            self.diff_results, self.conflict_decisions,
            wintogo_dir, local_dir
        )
        self.sync_worker.progress.connect(self._on_sync_progress)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.start()
    
    def _execute_unidirectional_sync(self, sync_needed, lang):
        """单向同步模式处理"""
        # 根据 extra_items_mode 处理目标多余项目
        # 不再弹窗询问，直接根据按钮切换来决定处理方式
        target_extra_items = []
        if self.sync_direction == "removable_to_local":
            # 介质 → 本地：源是介质，目标是本地
            # 目标（本地）多余项目：源不存在，目标存在，状态为 LOCAL_ONLY
            target_extra_items = [d for d in sync_needed if d.status == FileStatus.LOCAL_ONLY]
        else:
            # 本地 → 介质：源是本地，目标是介质
            # 目标（介质）多余项目：源不存在，目标存在，状态为 WINTOGO_ONLY
            target_extra_items = [d for d in sync_needed if d.status == FileStatus.WINTOGO_ONLY]
        
        # 根据 extra_items_mode 处理目标多余项目
        if target_extra_items and self.extra_items_mode == "delete":
            # "删除多余项目"模式：删除目标多余项目
            for diff in target_extra_items:
                if self.sync_direction == "removable_to_local":
                    self.conflict_decisions[diff.relative_path] = "delete_local"
                else:
                    self.conflict_decisions[diff.relative_path] = "delete_wintogo"
        # else: "保留多余项目"模式，忽略目标多余项目（不设置决策）
        
        # 设置其他同步项目的决策
        for diff in sync_needed:
            if diff.relative_path in self.conflict_decisions:
                continue
            
            if self.sync_direction == "removable_to_local":
                # 介质 → 本地：源是介质，目标是本地
                # WINTOGO_ONLY：源（介质）独有，准备同步
                if diff.status == FileStatus.WINTOGO_ONLY:
                    self.conflict_decisions[diff.relative_path] = "to_local"
                # LOCAL_ONLY：目标（本地）独有，已在 extra_items_mode 中处理
                elif diff.status == FileStatus.CONFLICT or diff.status == FileStatus.MTIME_DIFF:
                    if self.unidirectional_mode == "diff":
                        # 差异同步模式：若源新于目标，则覆盖目标；若目标新于源，则忽略此项目
                        if diff.wintogo_info and diff.local_info:
                            if diff.wintogo_info.mtime > diff.local_info.mtime:
                                # 源新于目标，覆盖目标
                                self.conflict_decisions[diff.relative_path] = "wintogo_to_local"
                            else:
                                # 目标新于源，忽略此项目
                                self.conflict_decisions[diff.relative_path] = "skip"
                        else:
                            # 无法比较时间，默认跳过
                            self.conflict_decisions[diff.relative_path] = "skip"
                    else:  # overwrite模式
                        # 覆盖同步模式：源优先，始终以源覆盖目标
                        self.conflict_decisions[diff.relative_path] = "wintogo_to_local"
            else:
                # 本地 → 介质：源是本地，目标是介质
                # LOCAL_ONLY：源（本地）独有，准备同步
                if diff.status == FileStatus.LOCAL_ONLY:
                    self.conflict_decisions[diff.relative_path] = "to_wintogo"
                # WINTOGO_ONLY：目标（介质）独有，已在 extra_items_mode 中处理
                elif diff.status == FileStatus.CONFLICT or diff.status == FileStatus.MTIME_DIFF:
                    if self.unidirectional_mode == "diff":
                        # 差异同步模式：若源新于目标，则覆盖目标；若目标新于源，则忽略此项目
                        if diff.wintogo_info and diff.local_info:
                            if diff.local_info.mtime > diff.wintogo_info.mtime:
                                # 源（本地）新于目标（介质），覆盖目标
                                self.conflict_decisions[diff.relative_path] = "local_to_wintogo"
                            else:
                                # 目标（介质）新于源（本地），忽略此项目
                                self.conflict_decisions[diff.relative_path] = "skip"
                        else:
                            # 无法比较时间，默认跳过
                            self.conflict_decisions[diff.relative_path] = "skip"
                    else:  # overwrite模式
                        # 覆盖同步模式：源优先，始终以源覆盖目标
                        self.conflict_decisions[diff.relative_path] = "local_to_wintogo"
        
        # 更新表格显示
        self._update_table()
        
        # 显示确认弹窗
        # 统计源独有项目（to_local 或 to_wintogo）
        source_only_count = len([r for r in self.diff_results 
                                 if self.conflict_decisions.get(r.relative_path, "") in ("to_local", "to_wintogo")])
        # 统计差异项目（包含 "_to_" 的决策，如 wintogo_to_local, local_to_wintogo）
        conflict_count = len([r for r in self.diff_results 
                             if "_to_" in self.conflict_decisions.get(r.relative_path, "")])
        # 统计删除项目（delete_local 或 delete_wintogo）
        delete_count = len([r for r in self.diff_results 
                           if self.conflict_decisions.get(r.relative_path, "").startswith("delete_")])
        # 统计跳过项目
        skip_count = len([r for r in self.diff_results 
                         if self.conflict_decisions.get(r.relative_path) == "skip"])
        
        # 总同步数量 = 源独有 + 差异项
        sync_count = source_only_count + conflict_count
        
        msg = lang == "zh" and \
            f"确定要执行单向同步操作吗？\n\n" or \
            f"Confirm unidirectional sync operation?\n\n"
        
        if sync_count > 0:
            msg += lang == "zh" and f"📋 同步文件: {sync_count} 个\n" or f"📋 Sync files: {sync_count} items\n"
        if delete_count > 0:
            msg += lang == "zh" and f"🗑️ 删除文件: {delete_count} 个\n" or f"🗑️ Delete files: {delete_count} items\n"
        if skip_count > 0:
            msg += lang == "zh" and f"⏭️ 跳过: {skip_count} 个\n" or f"⏭️ Skip: {skip_count} items\n"
        
        msg += lang == "zh" and "\n此操作不可撤销！" or "\nThis operation cannot be undone!"
        
        title = lang == "zh" and "确认同步" or "Confirm Sync"
        dialog = ConfirmSyncDialog(title, msg, lang, self)
        dialog.exec()
        if not dialog.is_confirmed():
            # 取消同步：清除已选决策并刷新表格
            self.conflict_decisions.clear()
            self._delete_both_dirs.clear()
            self._update_table()
            return
        
        # 执行同步
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        self.sync_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self._set_feature_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.sync_start_time = time.time()
        self.sync_transferred_bytes = 0

        self.sync_worker = SyncWorker(
            self.diff_results, self.conflict_decisions,
            wintogo_dir, local_dir
        )
        self.sync_worker.progress.connect(self._on_sync_progress)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.start()

    def _update_header_status(self, status: str = "default"):
        """
        更新主界面右上角的同步状态显示（根据同步类型和方向动态显示箭头）

        Args:
            status: 状态类型，可选值：
                - "default": 默认状态（↔）
                - "scanning": 扫描状态（🔍）
                - "syncing": 同步状态（📤）
                - "done": 完成状态（✅）
                - "error": 错误状态（❌）
        """
        # 根据同步类型和方向动态显示箭头
        if self.sync_type == "bidirectional":
            # 双向同步：显示 ↔
            status_key = "header_subtitle_bidirectional"
        else:
            # 单向同步：根据方向显示 → 或 ←
            if self.sync_direction == "removable_to_local":
                # A → B
                status_key = "header_subtitle_to_local"
            else:
                # A ← B
                status_key = "header_subtitle_to_removable"

        self.version_label.setText(self._get_subtitle_text(status_key))
    
    def _execute_newest_mode_sync(self, sync_needed, lang):
        """最新优先模式：自动选择较新版本"""
        # 提取名称前缀（去掉"目录"尾缀）
        removable_prefix = self.removable_name
        if removable_prefix.endswith("目录"):
            removable_prefix = removable_prefix[:-2]
        elif removable_prefix.endswith("Directory"):
            removable_prefix = removable_prefix[:-9]
        
        local_prefix = self.local_name
        if local_prefix.endswith("目录"):
            local_prefix = local_prefix[:-2]
        elif local_prefix.endswith("Directory"):
            local_prefix = local_prefix[:-9]
        
        # 自动为所有差异文件选择较新版本
        for diff in sync_needed:
            if diff.status == FileStatus.WINTOGO_ONLY:
                # 移动介质独有，同步到本地
                self.conflict_decisions[diff.relative_path] = "to_local"
            elif diff.status == FileStatus.LOCAL_ONLY:
                # 本地独有，同步到移动介质
                self.conflict_decisions[diff.relative_path] = "to_wintogo"
            elif diff.status == FileStatus.CONFLICT:
                # 冲突：选择较新的版本
                if diff.wintogo_info and diff.local_info:
                    if diff.wintogo_info.mtime > diff.local_info.mtime:
                        self.conflict_decisions[diff.relative_path] = "wintogo_to_local"
                    else:
                        self.conflict_decisions[diff.relative_path] = "local_to_wintogo"
                else:
                    self.conflict_decisions[diff.relative_path] = "skip"
            elif diff.status == FileStatus.MTIME_DIFF:
                # 时间差异：选择较新的版本
                if diff.wintogo_info and diff.local_info:
                    if diff.wintogo_info.mtime > diff.local_info.mtime:
                        self.conflict_decisions[diff.relative_path] = "wintogo_to_local"
                    else:
                        self.conflict_decisions[diff.relative_path] = "local_to_wintogo"
                else:
                    self.conflict_decisions[diff.relative_path] = "skip"
        
        # 统计同步操作
        to_local_count = len([d for d in sync_needed if self.conflict_decisions[d.relative_path] == "to_local"])
        to_wintogo_count = len([d for d in sync_needed if self.conflict_decisions[d.relative_path] == "to_wintogo"])
        wintogo_to_local_count = len([d for d in sync_needed if self.conflict_decisions[d.relative_path] == "wintogo_to_local"])
        local_to_wintogo_count = len([d for d in sync_needed if self.conflict_decisions[d.relative_path] == "local_to_wintogo"])
        
        # 显示汇总弹窗
        msg = lang == "zh" and "📋 最新优先模式同步汇总\n\n" or "📋 Newest First Mode Summary\n\n"
        msg += lang == "zh" and f"{removable_prefix} → {local_prefix}: {to_local_count + wintogo_to_local_count} 个\n" or f"{removable_prefix} → {local_prefix}: {to_local_count + wintogo_to_local_count} files\n"
        msg += lang == "zh" and f"{local_prefix} → {removable_prefix}: {to_wintogo_count + local_to_wintogo_count} 个\n" or f"{local_prefix} → {removable_prefix}: {to_wintogo_count + local_to_wintogo_count} files\n"
        msg += lang == "zh" and f"\n总计: {len(sync_needed)} 个文件将被同步\n\n此操作不可撤销！" or f"\nTotal: {len(sync_needed)} files will be synced\n\nThis action cannot be undone!"
        
        title = lang == "zh" and "确认同步" or "Confirm Sync"
        dialog = ConfirmSyncDialog(title, msg, lang, self)
        dialog.exec()
        if not dialog.is_confirmed():
            # 取消同步：清除已选决策并刷新表格
            self.conflict_decisions.clear()
            self._delete_both_dirs.clear()
            self._update_table()
            return
        
        # 执行同步
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        self.sync_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self._set_feature_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(lang == "zh" and "同步中... 准备中" or "Syncing... Preparing")
        self.status_label.setText(lang == "zh" and "📤 正在同步文件..." or "📤 Syncing files...")
        self.status_label.setStyleSheet("color: #1971c2; font-size: 13px; padding: 4px 0;")

        self.sync_start_time = time.time()
        self.sync_transferred_bytes = 0

        self.sync_worker = SyncWorker(
            self.diff_results, self.conflict_decisions,
            wintogo_dir, local_dir
        )
        self.sync_worker.progress.connect(self._on_sync_progress)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.start()
    
    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    
    def _format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}时{minutes}分"
    
    def _on_sync_progress(self, transferred: int, total: int, file_transferred: int, file_size: int, filename: str):
        if total > 0:
            percent = int(transferred / total * 100)
            self.progress_bar.setValue(percent)
            
            elapsed = time.time() - self.sync_start_time if self.sync_start_time else 0
            if elapsed > 0 and transferred > 0:
                speed = transferred / elapsed
                
                if speed > 0:
                    remaining_bytes = total - transferred
                    remaining_time = remaining_bytes / speed
                    speed_str = self._format_size(speed) + "/s"
                    time_str = self._format_time(remaining_time)
                    self.progress_bar.setFormat(f"同步中 {percent}% | {speed_str} | 剩余 {time_str}")
                else:
                    self.progress_bar.setFormat(f"同步中 {percent}%")
            else:
                self.progress_bar.setFormat(f"同步中 {percent}%")
        
        short_name = filename if len(filename) <= 50 else "..." + filename[-47:]
        self.status_label.setText(f"📤 正在同步: {short_name}")
    
    def _on_sync_finished(self, success_count: int, fail_count: int, skip_count: int):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self._set_feature_buttons_enabled(True)

        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        # 第一步：处理 DirSyncDialog 的"删除两端此目录"——整体 rmtree_safe
        if hasattr(self, '_delete_both_dirs') and self._delete_both_dirs:
            for raw_subdir in self._delete_both_dirs:
                subdir = raw_subdir.strip('/\\')
                if wintogo_dir:
                    wintogo_path = os.path.normpath(os.path.join(wintogo_dir, subdir))
                    if os.path.isdir(wintogo_path):
                        rmtree_safe(wintogo_path)
                        print(f"删除两端（移动介质端）: {wintogo_path}")
                if local_dir:
                    local_path = os.path.normpath(os.path.join(local_dir, subdir))
                    if os.path.isdir(local_path):
                        rmtree_safe(local_path)
                        print(f"删除两端（本地端）: {local_path}")
            self._delete_both_dirs.clear()

        # 第二步：处理逐文件删除留下的空目录
        # 用户通过 OnlyOneSideDialog/ConflictDialog 选择了删文件，
        # 文件已由 SyncWorker 逐个删除，但父目录可能残留在另一端
        if self.conflict_decisions:
            cleanup_parents = set()
            for rel_path, decision in self.conflict_decisions.items():
                if decision not in ('delete_wintogo', 'delete_local', 'delete_both'):
                    continue
                parent = os.path.dirname(rel_path)
                if parent:
                    cleanup_parents.add(parent)
            # 去重后清理每个父目录的空目录链
            for parent in cleanup_parents:
                if wintogo_dir:
                    wintogo_parent = os.path.normpath(os.path.join(wintogo_dir, parent))
                    if os.path.isdir(wintogo_parent):
                        _remove_empty_path_chain(wintogo_parent)
                if local_dir:
                    local_parent = os.path.normpath(os.path.join(local_dir, parent))
                    if os.path.isdir(local_parent):
                        _remove_empty_path_chain(local_parent)

        self.table.setRowCount(0)
        self.diff_results = []
        self.conflict_decisions = {}

        self.status_label.setText(f"✅ 同步完成 - 成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
        self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
