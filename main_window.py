"""
SyncGUI - 本地与移动介质双向文件同步工具

Author: Lisselde_E
GitHub: https://github.com/LisseldeE
Email: Lisselde.E@outlook.com
License: MIT
"""

import sys
import os
import json
import time
from datetime import datetime
from collections import defaultdict
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QProgressBar, QMessageBox, QHeaderView,
    QDialog, QDialogButtonBox, QGroupBox, QRadioButton, QButtonGroup,
    QFrame, QSizePolicy, QCheckBox, QListWidget, QListWidgetItem,
    QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QPropertyAnimation, QByteArray
from PyQt5.QtGui import QColor, QFont, QPalette

from sync_core import (
    scan_directory, compare_files, compare_files_unidirectional, sync_file,
    rmtree_safe, _remove_empty_path_chain, FileStatus, DiffResult
)
from language import get_text, LANGUAGES


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
        if self.original_pos is None:
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


def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


CONFIG_FILE = os.path.join(get_app_dir(), 'config.json')


STYLESHEET = """
QMainWindow {
    background-color: #f8f9fa;
}
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    background-color: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #495057;
}
QLineEdit {
    padding: 10px 12px;
    border: 1px solid #ced4da;
    border-radius: 6px;
    background-color: white;
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
    background-color: #e9ecef;
    color: #495057;
    border: 1px solid #ced4da;
}
QPushButton:hover {
    background-color: #dee2e6;
}
QPushButton:disabled {
    background-color: #adb5bd;
    color: #868e96;
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
    background-color: #adb5bd;
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
    background-color: #adb5bd;
}
QPushButton#browseBtn {
    background-color: #e9ecef;
    color: #495057;
    border: 1px solid #ced4da;
}
QPushButton#browseBtn:hover {
    background-color: #dee2e6;
}
QComboBox {
    background-color: #e9ecef;
    color: #495057;
    border: 1px solid #ced4da;
    border-radius: 6px;
    padding: 8px;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
QComboBox:hover {
    background-color: #dee2e6;
    border: 1px solid #adb5bd;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #495057;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: white;
    border: 1px solid #ced4da;
    selection-background-color: #339af0;
    selection-color: white;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
QTableWidget {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    background-color: white;
    gridline-color: #e9ecef;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
QTableWidget::item {
    padding: 8px;
}
QHeaderView::section {
    background-color: #f1f3f5;
    padding: 10px;
    border: none;
    border-bottom: 1px solid #dee2e6;
    font-weight: 600;
    color: #495057;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #e9ecef;
    text-align: center;
    font-weight: 500;
}
QProgressBar::chunk {
    background-color: #339af0;
    border-radius: 6px;
}
QMessageBox {
    background-color: white;
}
QMessageBox QLabel {
    color: #495057;
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
"""


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
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass


class ScanWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(dict, dict)
    
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
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    
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
    progress = pyqtSignal(object, object, object, object, str)
    finished = pyqtSignal(int, int, int)
    
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


class ConflictDialog(QDialog):
    def __init__(self, diff: DiffResult, same_dir_count: int = 0, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(get_text("dialog_conflict", lang))
        self.result_direction = None
        self.apply_to_dir = False
        self.cancel_sync = False
        self.same_dir_count = same_dir_count
        self.setMinimumWidth(500)
        
        self.wintogo_newer = diff.wintogo_info.mtime > diff.local_info.mtime
        self._init_ui(diff)
    
    def _init_ui(self, diff: DiffResult):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox {
                padding: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
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
        
        title_label = QLabel(get_text("conflict_title", self.lang))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e03131;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        file_label = QLabel(get_text("file_label", self.lang, path=diff.relative_path))
        file_label.setStyleSheet("""
            font-size: 13px; 
            padding: 12px; 
            background-color: #f8f9fa; 
            border-radius: 6px;
            border: 1px solid #e9ecef;
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
        wintogo_title = QLabel(get_text("removable_time", self.lang))
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
        local_title = QLabel(get_text("local_time", self.lang))
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
        
        newer = get_text("removable_time", self.lang) if self.wintogo_newer else get_text("local_time", self.lang)
        hint_label = QLabel(get_text("newer_hint", self.lang, side=newer))
        hint_label.setStyleSheet("color: #fd7e14; font-size: 13px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line2)
        
        choice_label = QLabel(get_text("choice_label", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)

        self.rb_newer = QRadioButton()
        self.rb_older = QRadioButton()
        self.rb_delete_both = QRadioButton(self.lang == "zh" and "🗑️ 双端删除此项目" or "🗑️ Delete from both sides")
        self.rb_skip = QRadioButton(get_text("skip_file", self.lang))

        newer_side = get_text("removable_time", self.lang) if self.wintogo_newer else get_text("local_time", self.lang)
        older_side = get_text("local_time", self.lang) if self.wintogo_newer else get_text("removable_time", self.lang)
        self.rb_newer.setText(get_text("keep_newest", self.lang, side=newer_side))
        self.rb_older.setText(get_text("keep_older", self.lang, side=older_side))

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
            self.apply_dir_check = QCheckBox(get_text("apply_dir_files", self.lang, count=self.same_dir_count))
            self.apply_dir_check.setStyleSheet("color: #1971c2; font-weight: 500;")
            self.apply_dir_check.setChecked(True)
            layout.addWidget(self.apply_dir_check)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(get_text("btn_confirm", self.lang))
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
        
        cancel_btn = QPushButton(get_text("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(get_text("btn_cancel_sync", self.lang))
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


class OnlyOneSideDialog(QDialog):
    def __init__(self, diff: DiffResult, same_dir_count: int = 0, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(get_text("dialog_diff", lang))
        self.diff = diff
        self.result_direction = None
        self.apply_to_dir = False
        self.cancel_sync = False
        self.same_dir_count = same_dir_count
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox {
                padding: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
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
        side_name = get_text("removable_time", self.lang) if is_wintogo_only else get_text("local_time", self.lang)
        other_side = get_text("local_time", self.lang) if is_wintogo_only else get_text("removable_time", self.lang)
        
        title_label = QLabel(get_text("diff_title", self.lang) + f" ({side_name})")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1971c2;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        file_label = QLabel(get_text("file_label", self.lang, path=self.diff.relative_path))
        file_label.setStyleSheet("""
            font-size: 13px; 
            padding: 12px; 
            background-color: #f8f9fa; 
            border-radius: 6px;
            border: 1px solid #e9ecef;
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
        
        choice_label = QLabel(get_text("choice_label", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)

        # 根据文件状态动态显示正确的同步方向
        if is_wintogo_only:
            # 介质存在，本地不存在：显示"介质 → 本地"
            copy_text = self.lang == "zh" and "➡️ 介质 → 本地（补充本地缺失的文件）" or "➡️ Removable → Local"
        else:
            # 本地存在，介质不存在：显示"本地 → 介质"
            copy_text = self.lang == "zh" and "➡️ 本地 → 介质（补充介质缺失的文件）" or "➡️ Local → Removable"

        delete_text = self.lang == "zh" and f"🗑️ 删除此文件（移除{side_name}多余的文件）" or f"🗑️ Delete this file"
        self.rb_copy = QRadioButton(copy_text)
        self.rb_delete = QRadioButton(delete_text)
        self.rb_skip = QRadioButton(get_text("skip_file", self.lang))

        self.rb_copy.setChecked(True)

        self.button_group.addButton(self.rb_copy, 0)
        self.button_group.addButton(self.rb_delete, 1)
        self.button_group.addButton(self.rb_skip, 2)

        layout.addWidget(self.rb_copy)
        layout.addWidget(self.rb_delete)
        layout.addWidget(self.rb_skip)
        
        if self.same_dir_count > 0:
            self.apply_dir_check = QCheckBox(get_text("apply_dir_files", self.lang, count=self.same_dir_count))
            self.apply_dir_check.setStyleSheet("color: #1971c2; font-weight: 500;")
            self.apply_dir_check.setChecked(True)
            layout.addWidget(self.apply_dir_check)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(get_text("btn_confirm", self.lang))
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
        
        cancel_btn = QPushButton(get_text("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(get_text("btn_cancel_sync", self.lang))
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


class MtimeDiffDialog(QDialog):
    def __init__(self, diff: DiffResult, same_dir_count: int = 0, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(get_text("dialog_mtime", lang))
        self.diff = diff
        self.result_direction = None
        self.apply_to_dir = False
        self.cancel_sync = False
        self.same_dir_count = same_dir_count
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox {
                padding: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
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
        
        title_label = QLabel(get_text("mtime_title", self.lang))
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
        
        file_label = QLabel(get_text("file_label", self.lang, path=self.diff.relative_path))
        file_label.setStyleSheet("""
            font-size: 13px; 
            padding: 12px; 
            background-color: #f8f9fa; 
            border-radius: 6px;
            border: 1px solid #e9ecef;
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
        wintogo_title = QLabel(get_text("removable_time", self.lang))
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
        local_title = QLabel(get_text("local_time", self.lang))
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
        newer = get_text("removable_time", self.lang) if self.wintogo_newer else get_text("local_time", self.lang)
        hint_label2 = QLabel(get_text("newer_hint", self.lang, side=newer))
        hint_label2.setStyleSheet("color: #fd7e14; font-size: 13px;")
        hint_label2.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label2)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line2)
        
        choice_label = QLabel(get_text("choice_label", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)

        self.rb_newer = QRadioButton()
        self.rb_older = QRadioButton()
        self.rb_delete_both = QRadioButton(self.lang == "zh" and "🗑️ 双端删除此项目" or "🗑️ Delete from both sides")
        self.rb_skip = QRadioButton(self.lang == "zh" and "⏭️ 跳过（保持现状）" or "⏭️ Skip (keep current)")

        newer_side = get_text("removable_time", self.lang) if self.wintogo_newer else get_text("local_time", self.lang)
        older_side = get_text("local_time", self.lang) if self.wintogo_newer else get_text("removable_time", self.lang)
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
            self.apply_dir_check = QCheckBox(get_text("apply_dir_files", self.lang, count=self.same_dir_count))
            self.apply_dir_check.setStyleSheet("color: #1971c2; font-weight: 500;")
            self.apply_dir_check.setChecked(True)
            layout.addWidget(self.apply_dir_check)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton(get_text("btn_confirm", self.lang))
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
        
        cancel_btn = QPushButton(get_text("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(get_text("btn_cancel_sync", self.lang))
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


class IgnoreRulesDialog(QDialog):
    def __init__(self, rules, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(get_text("dialog_ignore", lang))
        self.setMinimumSize(500, 400)
        self.rules = rules.copy()
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: white;
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
            }
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
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
        
        hint_label = QLabel(get_text("ignore_hint", self.lang))
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
        self.rule_input.setPlaceholderText(get_text("ignore_add_placeholder", self.lang))
        self.rule_input.returnPressed.connect(self._add_rule)
        add_layout.addWidget(self.rule_input)
        
        add_btn = QPushButton(get_text("btn_add", self.lang))
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
        
        confirm_btn = QPushButton(get_text("btn_confirm", self.lang))
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
        
        cancel_btn = QPushButton(get_text("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dee2e6;
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


class DirSyncDialog(QDialog):
    def __init__(self, dir_path: str, diff_list: list, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(get_text("dialog_dir_sync", lang))
        self.dir_path = dir_path
        self.diff_list = diff_list
        self.result_direction = None
        self.cancel_sync = False
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
            QRadioButton {
                padding: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
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
        
        title_label = QLabel(get_text("dir_sync_title", self.lang))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1971c2;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        path_text = self.lang == "zh" and f"路径: {self.dir_path}" or f"Path: {self.dir_path}"
        dir_label = QLabel(path_text)
        dir_label.setStyleSheet("""
            font-size: 14px; 
            padding: 10px; 
            background-color: #f8f9fa; 
            border-radius: 6px;
            border: 1px solid #e9ecef;
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
            wintogo_title = QLabel(self.lang == "zh" and "移动介质独有" or "Removable Only")
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
            local_title = QLabel(self.lang == "zh" and "本地独有" or "Local Only")
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
        detail_btn = QPushButton(get_text("view_detail", self.lang))
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
        
        choice_label = QLabel(get_text("dir_choice", self.lang))
        choice_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)
        
        self.rb_wintogo = QRadioButton(get_text("dir_to_local", self.lang))
        self.rb_local = QRadioButton(get_text("dir_to_removable", self.lang))
        self.rb_delete_both = QRadioButton(get_text("dir_delete_both", self.lang))
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
        
        confirm_btn = QPushButton(get_text("btn_confirm", self.lang))
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
        
        cancel_btn = QPushButton(get_text("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        cancel_sync_btn = QPushButton(get_text("btn_cancel_sync", self.lang))
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
        detail_dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
        """)
        
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
            
            if diff.status == FileStatus.WINTOGO_ONLY:
                status_text = "[WinToGo独有]"
                status_color = "#1971c2"
            elif diff.status == FileStatus.LOCAL_ONLY:
                status_text = "[本地独有]"
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
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
        """)
        close_btn.clicked.connect(detail_dialog.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        detail_dialog.exec_()


class SyncRulesDialog(QDialog):
    def __init__(self, rules, lang: str = "zh", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(get_text("dialog_sync_rule", lang))
        self.setMinimumSize(500, 400)
        self.rules = rules.copy()
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: white;
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
            }
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
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
        
        hint_label = QLabel(get_text("sync_rule_hint", self.lang))
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
        self.rule_input.setPlaceholderText(get_text("sync_rule_add_placeholder", self.lang))
        self.rule_input.returnPressed.connect(self._add_rule)
        add_layout.addWidget(self.rule_input)
        
        add_btn = QPushButton(get_text("btn_add", self.lang))
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
        
        confirm_btn = QPushButton(get_text("btn_confirm", self.lang))
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
        
        cancel_btn = QPushButton(get_text("btn_cancel", self.lang))
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dee2e6;
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


class AboutDialog(QDialog):
    """关于弹窗"""
    def __init__(self, lang='zh', parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(get_text("about_title", lang))
        self.setModal(True)
        # 移除右上角的问号按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(400, 320)  # 增加高度以容纳检查更新按钮
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 标题
        title_label = QLabel("SyncGUI")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #339af0;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 版本信息
        version_label = QLabel(get_text("about_version", self.lang))
        version_label.setStyleSheet("font-size: 11px; color: #495057;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # 描述
        desc_label = QLabel(get_text("about_description", self.lang))
        desc_label.setStyleSheet("font-size: 10px; color: #868e96;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addSpacing(8)
        
        # 作者信息
        author_label = QLabel(get_text("about_author", self.lang))
        author_label.setStyleSheet("font-size: 10px; color: #495057;")
        author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_label)
        
        # GitHub（可点击打开浏览器）
        github_label = QLabel(get_text("about_github", self.lang))
        github_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #339af0;
            }
            QLabel:hover {
                color: #228be6;
            }
        """)
        github_label.setAlignment(Qt.AlignCenter)
        github_label.setCursor(Qt.PointingHandCursor)
        github_label.mousePressEvent = lambda event: self._open_github()
        layout.addWidget(github_label)
        
        # 邮箱（可点击复制）
        email_label = QLabel(get_text("about_email", self.lang))
        email_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #495057;
            }
            QLabel:hover {
                color: #339af0;
            }
        """)
        email_label.setAlignment(Qt.AlignCenter)
        email_label.setCursor(Qt.PointingHandCursor)
        email_label.mousePressEvent = lambda event: self._copy_email()
        layout.addWidget(email_label)
        
        layout.addStretch()
        
        # 检查更新按钮和关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # 检查更新按钮
        check_update_btn = QPushButton(get_text("btn_check_update", self.lang))
        check_update_btn.setMinimumWidth(120)
        check_update_btn.setFixedHeight(36)
        check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #339af0;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #228be6;
            }
        """)
        check_update_btn.adjustSize()
        check_update_btn.clicked.connect(self._check_update)
        btn_layout.addWidget(check_update_btn)
        
        btn_layout.addSpacing(10)
        
        # 关闭按钮
        close_btn = QPushButton(get_text("btn_close", self.lang))
        close_btn.setFixedSize(100, 36)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _open_github(self):
        """打开GitHub链接"""
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl("https://github.com/LisseldeE"))
    
    def _copy_email(self):
        """复制邮箱到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText("Lisselde.E@outlook.com")
    
    def _check_update(self):
        """检查更新"""
        import urllib.request
        import json
        import re
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        
        try:
            # 获取GitHub仓库的tags列表
            url = "https://api.github.com/repos/LisseldeE/SyncGUI/tags"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'SyncGUI')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            if not data:
                QMessageBox.information(self, get_text("update_title", self.lang), 
                                       get_text("update_no_tags", self.lang))
                return
            
            # 找到最新的tag（假设tags按时间倒序排列）
            latest_tag = data[0]['name']
            
            # 从当前版本信息中提取版本号（如"版本：SyncGUI_R10"）
            current_version_text = get_text("about_version", self.lang)
            current_version_match = re.search(r'R(\d+)', current_version_text)
            
            if not current_version_match:
                QMessageBox.warning(self, get_text("update_title", self.lang),
                                   get_text("update_version_error", self.lang))
                return
            
            current_version = int(current_version_match.group(1))
            
            # 从最新tag中提取版本号（如"R10"）
            latest_version_match = re.search(r'R(\d+)', latest_tag)
            
            if not latest_version_match:
                QMessageBox.warning(self, get_text("update_title", self.lang),
                                   get_text("update_tag_error", self.lang))
                return
            
            latest_version = int(latest_version_match.group(1))
            
            # 比较版本号
            if latest_version > current_version:
                # 发现新版本，弹窗询问是否前往下载
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(get_text("update_title", self.lang))
                msg_box.setText(get_text("update_found", self.lang).format(latest_tag))
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
                yes_btn = msg_box.addButton(get_text("btn_yes", self.lang), QMessageBox.YesRole)
                no_btn = msg_box.addButton(get_text("btn_no", self.lang), QMessageBox.NoRole)
                
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
                
                msg_box.exec_()
                
                if msg_box.clickedButton() == yes_btn:
                    # 打开GitHub releases页面
                    QDesktopServices.openUrl(QUrl("https://github.com/LisseldeE/SyncGUI/releases"))
            else:
                # 当前已是最新版本（移除图标）
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(get_text("update_title", self.lang))
                msg_box.setText(get_text("update_latest", self.lang))
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
                
                msg_box.exec_()
        
        except urllib.error.URLError as e:
            # 网络错误
            QMessageBox.warning(self, get_text("update_title", self.lang),
                               get_text("update_network_error", self.lang).format(str(e)))
        except Exception as e:
            # 其他错误
            QMessageBox.warning(self, get_text("update_title", self.lang),
                               get_text("update_error", self.lang).format(str(e)))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 先加载配置文件中的语言设置
        config = load_config()
        self.current_lang = config.get('language', 'zh')
        self.sync_mode = config.get('sync_mode', 'default')  # "default" or "newest"
        self.sync_type = config.get('sync_type', 'bidirectional')  # "bidirectional" or "unidirectional"
        self.unidirectional_mode = config.get('unidirectional_mode', 'diff')  # "diff" or "overwrite"
        self.sync_direction = config.get('sync_direction', 'removable_to_local')  # "removable_to_local" or "local_to_removable"
        self.extra_items_mode = config.get('extra_items_mode', 'keep')  # "keep" or "delete"
        
        self.setWindowTitle(get_text("app_title", self.current_lang))
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
        
        self._init_ui()
        self._load_saved_paths()
        # 初始化按钮状态
        self._update_sync_type_button()
        self._update_unidirectional_mode_button()
        self._update_extra_items_button()
        self._update_buttons_visibility()
        # 初始化头部箭头显示（根据同步类型和方向动态显示）
        self._update_header_status()
    
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        header_layout = QHBoxLayout()
        title_label = QLabel("📁 SyncGUI")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #212529;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.version_label = QLabel(get_text("header_subtitle", self.current_lang))
        self.version_label.setStyleSheet("color: #868e96; font-size: 13px;")
        header_layout.addWidget(self.version_label)
        
        header_layout.addSpacing(16)
        
        self.lang_btn = AnimatedButton(get_text("language_btn", self.current_lang))
        self.lang_btn.setMinimumSize(70, 32)
        self.lang_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
        """)
        self.lang_btn.clicked.connect(self._toggle_language)
        header_layout.addWidget(self.lang_btn)
        
        # 关于按钮（小图标）
        self.about_btn = AnimatedButton("i")
        self.about_btn.setFixedSize(32, 32)
        self.about_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #6c757d;
                border: 1px solid #dee2e6;
                border-radius: 16px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                color: #495057;
                border-color: #adb5bd;
            }
        """)
        self.about_btn.clicked.connect(self._show_about_dialog)
        header_layout.addWidget(self.about_btn)
        
        layout.addLayout(header_layout)
        
        dir_group = QGroupBox("目录设置")
        dir_layout = QVBoxLayout(dir_group)
        dir_layout.setSpacing(12)
        dir_layout.setContentsMargins(16, 20, 16, 16)
        
        label_width = 100
        
        wintogo_layout = QHBoxLayout()
        self.wintogo_label = QLabel(get_text("removable_label", self.current_lang))
        self.wintogo_label.setFixedWidth(label_width)
        self.wintogo_label.setStyleSheet("font-size: 13px; color: #495057;")
        wintogo_layout.addWidget(self.wintogo_label)
        self.wintogo_edit = QLineEdit()
        self.wintogo_edit.setPlaceholderText(get_text("removable_placeholder", self.current_lang))
        self.wintogo_edit.textChanged.connect(self._on_path_changed)
        wintogo_layout.addWidget(self.wintogo_edit)
        self.wintogo_btn = AnimatedButton(get_text("browse", self.current_lang))
        self.wintogo_btn.setObjectName("browseBtn")
        self.wintogo_btn.setMinimumWidth(80)
        self.wintogo_btn.clicked.connect(self._select_wintogo)
        wintogo_layout.addWidget(self.wintogo_btn)
        dir_layout.addLayout(wintogo_layout)
        
        local_layout = QHBoxLayout()
        self.local_label = QLabel(get_text("local_label", self.current_lang))
        self.local_label.setFixedWidth(label_width)
        self.local_label.setStyleSheet("font-size: 13px; color: #495057;")
        local_layout.addWidget(self.local_label)
        self.local_edit = QLineEdit()
        self.local_edit.setPlaceholderText(get_text("local_placeholder", self.current_lang))
        self.local_edit.textChanged.connect(self._on_path_changed)
        local_layout.addWidget(self.local_edit)
        self.local_btn = AnimatedButton(get_text("browse", self.current_lang))
        self.local_btn.setObjectName("browseBtn")
        self.local_btn.setMinimumWidth(80)
        self.local_btn.clicked.connect(self._select_local)
        local_layout.addWidget(self.local_btn)
        dir_layout.addLayout(local_layout)
        
        layout.addWidget(dir_group)
        
        # 第一行按钮：同步模式、默认模式、忽略规则、同步规则
        btn_layout_row1 = QHBoxLayout()
        btn_layout_row1.setSpacing(12)
        
        # 同步模式切换按钮（双向/单向）
        self.sync_type_btn = AnimatedButton(get_text("sync_type_bidirectional", self.current_lang))
        self.sync_type_btn.setObjectName("browseBtn")
        self.sync_type_btn.setMinimumHeight(44)
        self.sync_type_btn.setMinimumWidth(110)
        self.sync_type_btn.clicked.connect(self._toggle_sync_type)
        btn_layout_row1.addWidget(self.sync_type_btn)
        
        # 默认模式按钮（默认模式/最新优先）
        self.mode_btn = AnimatedButton(get_text("mode_default", self.current_lang))
        self.mode_btn.setObjectName("browseBtn")
        self.mode_btn.setMinimumHeight(44)
        self.mode_btn.setMinimumWidth(110)
        self.mode_btn.clicked.connect(self._toggle_mode)
        btn_layout_row1.addWidget(self.mode_btn)
        
        # 单向模式子模式按钮（差异同步/覆盖同步）
        self.unidirectional_mode_btn = AnimatedButton(get_text("unidirectional_mode_diff", self.current_lang))
        self.unidirectional_mode_btn.setObjectName("browseBtn")
        self.unidirectional_mode_btn.setMinimumHeight(44)
        self.unidirectional_mode_btn.setMinimumWidth(110)
        self.unidirectional_mode_btn.clicked.connect(self._toggle_unidirectional_mode)
        self.unidirectional_mode_btn.setVisible(False)  # 默认隐藏，只在单向模式下显示
        btn_layout_row1.addWidget(self.unidirectional_mode_btn)
        
        # 方向切换按钮（介质→本地/本地→介质）
        self.direction_btn = AnimatedButton(get_text("direction_removable_to_local", self.current_lang))
        self.direction_btn.setObjectName("browseBtn")
        self.direction_btn.setMinimumHeight(44)
        self.direction_btn.setMinimumWidth(150)
        self.direction_btn.clicked.connect(self._change_sync_direction)
        self.direction_btn.setVisible(False)  # 默认隐藏，只在单向模式下显示
        btn_layout_row1.addWidget(self.direction_btn)
        
        # 多余项目处理按钮（保留多余项目/删除多余项目）
        self.extra_items_btn = AnimatedButton(get_text("extra_items_keep", self.current_lang))
        self.extra_items_btn.setObjectName("browseBtn")
        self.extra_items_btn.setMinimumHeight(44)
        self.extra_items_btn.setMinimumWidth(130)
        self.extra_items_btn.clicked.connect(self._toggle_extra_items_mode)
        self.extra_items_btn.setVisible(False)  # 默认隐藏，只在单向模式下显示
        btn_layout_row1.addWidget(self.extra_items_btn)
        
        # 忽略规则按钮
        self.ignore_btn = AnimatedButton(get_text("ignore_btn", self.current_lang))
        self.ignore_btn.setObjectName("browseBtn")
        self.ignore_btn.setMinimumHeight(44)
        self.ignore_btn.setMinimumWidth(100)
        self.ignore_btn.clicked.connect(self._show_ignore_dialog)
        btn_layout_row1.addWidget(self.ignore_btn)
        
        # 同步规则按钮
        self.sync_rule_btn = AnimatedButton(get_text("sync_rule_btn", self.current_lang))
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
        
        self.scan_btn = AnimatedButton(get_text("scan_btn", self.current_lang))
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.setFixedHeight(44)
        self.scan_btn.setFixedWidth(140)
        self.scan_btn.clicked.connect(self._start_scan)
        btn_layout_row2.addWidget(self.scan_btn)
        
        self.sync_btn = AnimatedButton(get_text("sync_btn", self.current_lang))
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
        
        self.status_label = QLabel(get_text("status_ready", self.current_lang))
        self.status_label.setStyleSheet("color: #868e96; font-size: 13px; padding: 4px 0;")
        layout.addWidget(self.status_label)
        
        table_group = QGroupBox("差异列表")
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(16, 20, 16, 16)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            get_text("col_status", self.current_lang),
            get_text("col_path", self.current_lang),
            get_text("col_removable_size", self.current_lang),
            get_text("col_local_size", self.current_lang),
            get_text("col_operation", self.current_lang)
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 130)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        table_layout.addWidget(self.table)
        
        layout.addWidget(table_group)
    
    def _load_saved_paths(self):
        config = load_config()
        wintogo_path = config.get('wintogo_dir', '')
        local_path = config.get('local_dir', '')
        ignore_rules = config.get('ignore_rules', [])
        sync_rules = config.get('sync_rules', [])
        
        if wintogo_path:
            self.wintogo_edit.setText(wintogo_path)
        if local_path:
            self.local_edit.setText(local_path)
        self.ignore_rules = ignore_rules
        self.sync_rules = sync_rules
        
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
    
    def _update_sync_type_button(self):
        """更新同步类型按钮显示"""
        if self.sync_type == "unidirectional":
            self.sync_type_btn.setText(get_text("sync_type_unidirectional", self.current_lang))
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
            """)
        else:
            self.sync_type_btn.setText(get_text("sync_type_bidirectional", self.current_lang))
            self.sync_type_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e9ecef;
                    color: #495057;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #dee2e6;
                }
            """)
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
            self.unidirectional_mode_btn.setText(get_text("unidirectional_mode_overwrite", self.current_lang))
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
            """)
        else:
            self.unidirectional_mode_btn.setText(get_text("unidirectional_mode_diff", self.current_lang))
            self.unidirectional_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e9ecef;
                    color: #495057;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #dee2e6;
                }
            """)
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
            self.extra_items_btn.setText(get_text("extra_items_delete", self.current_lang))
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
            """)
        else:
            self.extra_items_btn.setText(get_text("extra_items_keep", self.current_lang))
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
            """)
        self.extra_items_btn.adjustSize()
    
    def _change_sync_direction(self):
        """切换同步方向"""
        if self.sync_direction == "removable_to_local":
            self.sync_direction = "local_to_removable"
            self.direction_btn.setText(get_text("direction_local_to_removable", self.current_lang))
        else:
            self.sync_direction = "removable_to_local"
            self.direction_btn.setText(get_text("direction_removable_to_local", self.current_lang))
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
                if self.sync_direction == "local_to_removable":
                    self.direction_btn.setText(get_text("direction_local_to_removable", self.current_lang))
                else:
                    self.direction_btn.setText(get_text("direction_removable_to_local", self.current_lang))
            
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
        self._update_mode_button()
        # 保存同步模式设置到配置文件
        self._save_paths()
    
    def _update_mode_button(self):
        """更新模式按钮显示（带淡入淡出动画）"""
        if self.sync_mode == "newest":
            self.mode_btn.setText(get_text("mode_newest", self.current_lang))
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
            """)
            # 最新优先模式下隐藏同步规则按钮（不使用同步规则）
            self._fade_widget(self.sync_rule_btn, False)
        else:
            self.mode_btn.setText(get_text("mode_default", self.current_lang))
            self.mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e9ecef;
                    color: #495057;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #dee2e6;
                }
            """)
            # 默认模式下显示同步规则按钮（仅在双向模式下）
            if self.sync_type == "bidirectional":
                self._fade_widget(self.sync_rule_btn, True)
        self.mode_btn.adjustSize()
    
    def _update_ui_language(self):
        """更新界面语言"""
        lang = self.current_lang

        # 更新窗口标题
        self.setWindowTitle(get_text("app_title", lang))

        # 更新头部（根据同步类型和方向动态显示箭头）
        self._update_header_status()

        self.lang_btn.setText(get_text("language_btn", lang))
        self.lang_btn.adjustSize()
        
        # 更新目录设置
        self.wintogo_label.setText(get_text("removable_label", lang))
        self.wintogo_edit.setPlaceholderText(get_text("removable_placeholder", lang))
        self.wintogo_btn.setText(get_text("browse", lang))
        self.wintogo_btn.adjustSize()
        self.local_label.setText(get_text("local_label", lang))
        self.local_edit.setPlaceholderText(get_text("local_placeholder", lang))
        self.local_btn.setText(get_text("browse", lang))
        self.local_btn.adjustSize()
        
        # 更新按钮
        self.scan_btn.setText(get_text("scan_btn", lang))
        self.sync_btn.setText(get_text("sync_btn", lang))
        self.ignore_btn.setText(get_text("ignore_btn", lang))
        self.ignore_btn.adjustSize()
        self.sync_rule_btn.setText(get_text("sync_rule_btn", lang))
        self.sync_rule_btn.adjustSize()
        self._update_sync_type_button()
        self._update_unidirectional_mode_button()
        # 更新方向切换按钮文本
        if self.sync_direction == "local_to_removable":
            self.direction_btn.setText(get_text("direction_local_to_removable", lang))
        else:
            self.direction_btn.setText(get_text("direction_removable_to_local", lang))
        self._update_mode_button()
        
        # 更新状态
        self.status_label.setText(get_text("status_ready", lang))
        
        # 更新表格
        self.table.setHorizontalHeaderLabels([
            get_text("col_status", lang),
            get_text("col_path", lang),
            get_text("col_removable_size", lang),
            get_text("col_local_size", lang),
            get_text("col_operation", lang)
        ])
        
        # 如果有差异结果，重新刷新表格
        if self.diff_results:
            self._update_table()
    
    def _save_paths(self):
        config = {
            'wintogo_dir': self.wintogo_edit.text().strip(),
            'local_dir': self.local_edit.text().strip(),
            'ignore_rules': self.ignore_rules,
            'sync_rules': self.sync_rules,
            'language': self.current_lang,
            'sync_mode': self.sync_mode,
            'sync_type': self.sync_type,
            'unidirectional_mode': self.unidirectional_mode,
            'sync_direction': self.sync_direction,
            'extra_items_mode': self.extra_items_mode
        }
        save_config(config)
    
    def _show_ignore_dialog(self):
        dialog = IgnoreRulesDialog(self.ignore_rules, self.current_lang, self)
        if dialog.exec_() == QDialog.Accepted:
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
        if dialog.exec_() == QDialog.Accepted:
            self.sync_rules = dialog.get_rules()
            self._save_paths()
            saved_text = self.current_lang == "zh" and f"✅ 已保存 {len(self.sync_rules)} 条同步规则" or f"✅ Saved {len(self.sync_rules)} sync rules"
            self.status_label.setText(saved_text)
            self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
    
    def _show_about_dialog(self):
        """显示关于弹窗"""
        dialog = AboutDialog(self.current_lang, self)
        dialog.exec_()
    
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
                        FileStatus.WINTOGO_ONLY: (get_text("status_removable_only", lang), QColor(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.LOCAL_ONLY: (get_text("status_local_only", lang), QColor(255, 245, 255)),  # 红色：目标独有，将被删除
                        FileStatus.SAME: (get_text("status_same", lang), QColor(248, 249, 250)),
                        FileStatus.CONFLICT: (get_text("status_conflict", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (get_text("status_mtime_diff", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
                else:
                    # 本地 → 介质：源是本地，目标是介质
                    status_map = {
                        FileStatus.LOCAL_ONLY: (get_text("status_local_only", lang), QColor(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.WINTOGO_ONLY: (get_text("status_removable_only", lang), QColor(255, 245, 245)),  # 纅色：目标独有，准备删除
                        FileStatus.SAME: (get_text("status_same", lang), QColor(248, 249, 250)),
                        FileStatus.CONFLICT: (get_text("status_conflict", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (get_text("status_mtime_diff", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
            else:
                # 差异同步模式
                # 根据同步方向决定颜色：
                # - 源独有：绿色（准备同步至目标的新项目）
                # - 目标独有：红色（准备删除目标的项目）
                if self.sync_direction == "removable_to_local":
                    # 介质 → 本地：源是介质，目标是本地
                    status_map = {
                        FileStatus.WINTOGO_ONLY: (get_text("status_removable_only", lang), QColor(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.LOCAL_ONLY: (get_text("status_local_only", lang), QColor(255, 245, 255)),  # 红色：目标独有，将被删除
                        FileStatus.SAME: (get_text("status_same", lang), QColor(248, 249, 250)),
                        FileStatus.CONFLICT: (get_text("status_conflict", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (get_text("status_mtime_diff", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
                else:
                    # 本地 → 介质：源是本地，目标是介质
                    status_map = {
                        FileStatus.LOCAL_ONLY: (get_text("status_local_only", lang), QColor(227, 245, 255)),  # 绿色：源独有，准备同步至目标
                        FileStatus.WINTOGO_ONLY: (get_text("status_removable_only", lang), QColor(255, 245, 255)),  # 红色：目标独有，将被删除
                        FileStatus.SAME: (get_text("status_same", lang), QColor(248, 249, 250)),
                        FileStatus.CONFLICT: (get_text("status_conflict", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                        FileStatus.MTIME_DIFF: (get_text("status_mtime_diff", lang), QColor(255, 243, 214)),  # 黄色：准备同步至目标的差异项目
                    }
        else:
            # 双向同步模式
            status_map = {
                FileStatus.WINTOGO_ONLY: (get_text("status_removable_only", lang), QColor(227, 245, 255)),  # 绿色：仅一方存在
                FileStatus.LOCAL_ONLY: (get_text("status_local_only", lang), QColor(227, 245, 255)),  # 绿色：仅一方存在
                FileStatus.SAME: (get_text("status_same", lang), QColor(248, 249, 250)),
                FileStatus.CONFLICT: (get_text("status_conflict", lang), QColor(255, 243, 214)),  # 黄色：双方都存在的差异项目
                FileStatus.MTIME_DIFF: (get_text("status_mtime_diff", lang), QColor(255, 243, 214)),  # 黄色：双方都存在的差异项目
            }
        
        action_map = {
            FileStatus.WINTOGO_ONLY: get_text("status_ready", lang).replace("就绪 - 请选择两个目录", "待选择").replace("Ready - Please select two directories", "Pending"),
            FileStatus.LOCAL_ONLY: get_text("status_ready", lang).replace("就绪 - 请选择两个目录", "待选择").replace("Ready - Please select two directories", "Pending"),
            FileStatus.SAME: lang == "zh" and "无操作" or "No action",
            FileStatus.CONFLICT: get_text("status_ready", lang).replace("就绪 - 请选择两个目录", "待选择").replace("Ready - Please select two directories", "Pending"),
            FileStatus.MTIME_DIFF: get_text("status_ready", lang).replace("就绪 - 请选择两个目录", "待选择").replace("Ready - Please select two directories", "Pending"),
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
            path_item.setForeground(QColor("#495057"))
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
            
            action_text = action_map[diff.status]
            if diff.relative_path in self.conflict_decisions:
                decision = self.conflict_decisions[diff.relative_path]
                if decision == "skip":
                    action_text = lang == "zh" and "跳过" or "Skip"
                elif diff.status == FileStatus.WINTOGO_ONLY:
                    if decision == "to_local":
                        action_text = lang == "zh" and "复制到本地" or "Copy to local"
                    elif decision == "delete_wintogo":
                        action_text = lang == "zh" and "删除文件" or "Delete file"
                elif diff.status == FileStatus.LOCAL_ONLY:
                    if decision == "to_wintogo":
                        action_text = lang == "zh" and "复制到移动介质" or "Copy to removable"
                    elif decision == "delete_local":
                        action_text = lang == "zh" and "删除文件" or "Delete file"
                elif diff.status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
                    if diff.wintogo_info and diff.local_info:
                        wintogo_newer = diff.wintogo_info.mtime > diff.local_info.mtime
                        if decision == "wintogo_to_local":
                            action_text = "保留最新" if wintogo_newer else "保留旧版"
                        elif decision == "local_to_wintogo":
                            action_text = "保留旧版" if wintogo_newer else "保留最新"
                    else:
                        action_text = "已选择"
            
            action_item = QTableWidgetItem(action_text)
            action_item.setBackground(color)
            action_item.setTextAlignment(Qt.AlignCenter)
            if diff.status in (FileStatus.CONFLICT, FileStatus.MTIME_DIFF):
                action_item.setForeground(QColor("#e67700"))
            elif diff.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY):
                if diff.relative_path in self.conflict_decisions:
                    action_item.setForeground(QColor("#2f9e44"))
                else:
                    action_item.setForeground(QColor("#e67700"))
            else:
                action_item.setForeground(QColor("#2f9e44"))
            self.table.setItem(row, 4, action_item)
    
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
                get_text("msg_no_diff", lang))
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
            dialog = DirSyncDialog(subdir, diff_list, lang, self)
            if dialog.exec_() == QDialog.Accepted:
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
        
        processed_dirs = set()
        
        only_one_side = [d for d in other_diffs if d.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)]
        conflicts = [d for d in other_diffs if d.status == FileStatus.CONFLICT]
        mtime_diffs = [d for d in other_diffs if d.status == FileStatus.MTIME_DIFF]
        
        for diff in only_one_side:
            if diff.relative_path in self.conflict_decisions:
                continue
            
            parent_dir = self._get_parent_dir(diff.relative_path)
            
            same_dir_diffs = [d for d in dir_diffs[parent_dir] 
                              if d.relative_path not in self.conflict_decisions 
                              and d.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)]
            same_dir_count = len(same_dir_diffs) - 1
            
            dialog = OnlyOneSideDialog(diff, same_dir_count, lang, self)
            if dialog.exec_() == QDialog.Accepted:
                direction = dialog.get_direction()
                self.conflict_decisions[diff.relative_path] = direction
                
                if dialog.should_apply_to_dir() and parent_dir not in processed_dirs:
                    for other_diff in same_dir_diffs:
                        if other_diff.relative_path != diff.relative_path:
                            self.conflict_decisions[other_diff.relative_path] = direction
                    processed_dirs.add(parent_dir)
                # 更新表格显示
                self._update_table()
            elif dialog.cancel_sync:
                # 取消本次同步，清除已选择的状态并刷新表格
                self.conflict_decisions.clear()
                self._delete_both_dirs.clear()
                self._update_table()
                return
            else:
                self.conflict_decisions[diff.relative_path] = "skip"
                # 更新表格显示
                self._update_table()
        
        processed_dirs = set()
        
        for diff in conflicts:
            if diff.relative_path in self.conflict_decisions:
                continue
            
            parent_dir = self._get_parent_dir(diff.relative_path)
            
            same_dir_conflicts = [d for d in dir_diffs[parent_dir] 
                                  if d.relative_path not in self.conflict_decisions
                                  and d.status == FileStatus.CONFLICT]
            same_dir_count = len(same_dir_conflicts) - 1
            
            dialog = ConflictDialog(diff, same_dir_count, lang, self)
            if dialog.exec_() == QDialog.Accepted:
                direction = dialog.get_direction()
                self.conflict_decisions[diff.relative_path] = direction
                
                if dialog.should_apply_to_dir() and parent_dir not in processed_dirs:
                    for other_diff in same_dir_conflicts:
                        if other_diff.relative_path != diff.relative_path:
                            self.conflict_decisions[other_diff.relative_path] = direction
                    processed_dirs.add(parent_dir)
                # 更新表格显示
                self._update_table()
            elif dialog.cancel_sync:
                # 取消本次同步，清除已选择的状态并刷新表格
                self.conflict_decisions.clear()
                self._delete_both_dirs.clear()
                self._update_table()
                return
            else:
                self.conflict_decisions[diff.relative_path] = "skip"
                # 更新表格显示
                self._update_table()
        
        processed_dirs = set()
        
        for diff in mtime_diffs:
            if diff.relative_path in self.conflict_decisions:
                continue
            
            parent_dir = self._get_parent_dir(diff.relative_path)
            
            same_dir_mtime = [d for d in dir_diffs[parent_dir] 
                              if d.relative_path not in self.conflict_decisions
                              and d.status == FileStatus.MTIME_DIFF]
            same_dir_count = len(same_dir_mtime) - 1
            
            dialog = MtimeDiffDialog(diff, same_dir_count, lang, self)
            if dialog.exec_() == QDialog.Accepted:
                direction = dialog.get_direction()
                self.conflict_decisions[diff.relative_path] = direction
                
                if dialog.should_apply_to_dir() and parent_dir not in processed_dirs:
                    for other_diff in same_dir_mtime:
                        if other_diff.relative_path != diff.relative_path:
                            self.conflict_decisions[other_diff.relative_path] = direction
                    processed_dirs.add(parent_dir)
                # 更新表格显示
                self._update_table()
            elif dialog.cancel_sync:
                # 取消本次同步，清除已选择的状态并刷新表格
                self.conflict_decisions.clear()
                self._delete_both_dirs.clear()
                self._update_table()
                return
            else:
                self.conflict_decisions[diff.relative_path] = "skip"
                # 更新表格显示
                self._update_table()
        
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
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认同步")
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Question)
        
        confirm_btn = msg_box.addButton("确定", QMessageBox.YesRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() != confirm_btn:
            return
        
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        self.sync_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
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
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(lang == "zh" and "确认同步" or "Confirm Sync")
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Question)
        
        confirm_btn = msg_box.addButton(lang == "zh" and "确定" or "Confirm", QMessageBox.YesRole)
        cancel_btn = msg_box.addButton(lang == "zh" and "取消" or "Cancel", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() != confirm_btn:
            return
        
        # 执行同步
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        self.sync_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

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
                # 介质 → 本地
                status_key = "header_subtitle_to_local"
            else:
                # 本地 → 介质（显示为 ←）
                status_key = "header_subtitle_to_removable"

        self.version_label.setText(get_text(status_key, self.current_lang))
    
    def _execute_newest_mode_sync(self, sync_needed, lang):
        """最新优先模式：自动选择较新版本"""
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
        msg += lang == "zh" and f"移动介质 → 本地: {to_local_count + wintogo_to_local_count} 个\n" or f"Removable → Local: {to_local_count + wintogo_to_local_count} files\n"
        msg += lang == "zh" and f"本地 → 移动介质: {to_wintogo_count + local_to_wintogo_count} 个\n" or f"Local → Removable: {to_wintogo_count + local_to_wintogo_count} files\n"
        msg += lang == "zh" and f"\n总计: {len(sync_needed)} 个文件将被同步\n\n此操作不可撤销！" or f"\nTotal: {len(sync_needed)} files will be synced\n\nThis action cannot be undone!"
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(lang == "zh" and "确认同步" or "Confirm Sync")
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Question)
        
        confirm_btn = msg_box.addButton(lang == "zh" and "确定" or "Confirm", QMessageBox.YesRole)
        cancel_btn = msg_box.addButton(lang == "zh" and "取消" or "Cancel", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() != confirm_btn:
            return
        
        # 执行同步
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        self.sync_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
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
