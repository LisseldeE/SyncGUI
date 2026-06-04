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
    QFrame, QSizePolicy, QCheckBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette

from sync_core import (
    scan_directory, compare_files, sync_file,
    FileStatus, DiffResult
)
from language import get_text, LANGUAGES


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
                 wintogo_dir: str, local_dir: str):
        super().__init__()
        self.wintogo_files = wintogo_files
        self.local_files = local_files
        self.wintogo_dir = wintogo_dir
        self.local_dir = local_dir
    
    def run(self):
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
        self.rb_skip = QRadioButton(get_text("skip_file", self.lang))
        
        newer_side = get_text("removable_time", self.lang) if self.wintogo_newer else get_text("local_time", self.lang)
        older_side = get_text("local_time", self.lang) if self.wintogo_newer else get_text("removable_time", self.lang)
        self.rb_newer.setText(get_text("keep_newest", self.lang, side=newer_side))
        self.rb_older.setText(get_text("keep_older", self.lang, side=older_side))
        
        self.rb_newer.setChecked(True)
        
        self.button_group.addButton(self.rb_newer, 0)
        self.button_group.addButton(self.rb_older, 1)
        self.button_group.addButton(self.rb_skip, 2)
        
        layout.addWidget(self.rb_newer)
        layout.addWidget(self.rb_older)
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
        
        copy_text = self.lang == "zh" and f"📋 复制到{other_side}（补充缺少的文件）" or f"📋 Copy to {other_side}"
        delete_text = self.lang == "zh" and f"🗑️ 删除此文件（移除多余的文件）" or "🗑️ Delete this file"
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
        self.button_group.addButton(self.rb_skip, 2)
        
        layout.addWidget(self.rb_newer)
        layout.addWidget(self.rb_older)
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 先加载配置文件中的语言设置
        config = load_config()
        self.current_lang = config.get('language', 'zh')
        self.sync_mode = config.get('sync_mode', 'default')  # "default" or "newest"
        
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
        
        self.lang_btn = QPushButton(get_text("language_btn", self.current_lang))
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
        self.wintogo_btn = QPushButton(get_text("browse", self.current_lang))
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
        self.local_btn = QPushButton(get_text("browse", self.current_lang))
        self.local_btn.setObjectName("browseBtn")
        self.local_btn.setMinimumWidth(80)
        self.local_btn.clicked.connect(self._select_local)
        local_layout.addWidget(self.local_btn)
        dir_layout.addLayout(local_layout)
        
        layout.addWidget(dir_group)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.scan_btn = QPushButton(get_text("scan_btn", self.current_lang))
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.setFixedHeight(44)
        self.scan_btn.setFixedWidth(140)
        self.scan_btn.clicked.connect(self._start_scan)
        btn_layout.addWidget(self.scan_btn)
        
        self.sync_btn = QPushButton(get_text("sync_btn", self.current_lang))
        self.sync_btn.setObjectName("syncBtn")
        self.sync_btn.setFixedHeight(44)
        self.sync_btn.setFixedWidth(140)
        self.sync_btn.clicked.connect(self._execute_sync)
        self.sync_btn.setEnabled(False)
        btn_layout.addWidget(self.sync_btn)
        
        self.ignore_btn = QPushButton(get_text("ignore_btn", self.current_lang))
        self.ignore_btn.setObjectName("browseBtn")
        self.ignore_btn.setMinimumHeight(44)
        self.ignore_btn.setMinimumWidth(100)
        self.ignore_btn.clicked.connect(self._show_ignore_dialog)
        btn_layout.addWidget(self.ignore_btn)
        
        self.sync_rule_btn = QPushButton(get_text("sync_rule_btn", self.current_lang))
        self.sync_rule_btn.setObjectName("browseBtn")
        self.sync_rule_btn.setMinimumHeight(44)
        self.sync_rule_btn.setMinimumWidth(100)
        self.sync_rule_btn.clicked.connect(self._show_sync_rule_dialog)
        btn_layout.addWidget(self.sync_rule_btn)
        
        self.mode_btn = QPushButton(get_text("mode_default", self.current_lang))
        self.mode_btn.setObjectName("browseBtn")
        self.mode_btn.setMinimumHeight(44)
        self.mode_btn.setMinimumWidth(110)
        self.mode_btn.clicked.connect(self._toggle_mode)
        btn_layout.addWidget(self.mode_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
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
        """更新模式按钮显示"""
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
        self.mode_btn.adjustSize()
    
    def _update_ui_language(self):
        """更新界面语言"""
        lang = self.current_lang
        
        # 更新窗口标题
        self.setWindowTitle(get_text("app_title", lang))
        
        # 更新头部
        self.version_label.setText(get_text("header_subtitle", lang))
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
            'sync_mode': self.sync_mode
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
            wintogo_files, local_files, wintogo_dir, local_dir
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
        
        status_map = {
            FileStatus.WINTOGO_ONLY: (get_text("status_removable_only", lang), QColor(227, 245, 255)),
            FileStatus.LOCAL_ONLY: (get_text("status_local_only", lang), QColor(235, 251, 238)),
            FileStatus.SAME: (get_text("status_same", lang), QColor(248, 249, 250)),
            FileStatus.CONFLICT: (get_text("status_conflict", lang), QColor(255, 243, 214)),
            FileStatus.MTIME_DIFF: (get_text("status_mtime_diff", lang), QColor(255, 243, 214)),
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
            
            path_item = QTableWidgetItem(diff.relative_path)
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
        
        if not sync_needed:
            QMessageBox.information(self, 
                lang == "zh" and "提示" or "Info",
                get_text("msg_no_diff", lang))
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
                self._update_table()
                return
            else:
                self.conflict_decisions[diff.relative_path] = "skip"
                # 更新表格显示
                self._update_table()
        
        self._update_table()
        
        copy_count = len([r for r in self.diff_results 
                         if r.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)
                         and self.conflict_decisions.get(r.relative_path, "").startswith("to_")])
        delete_count = len([r for r in self.diff_results 
                           if r.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)
                           and self.conflict_decisions.get(r.relative_path, "").startswith("delete_")])
        conflict_count = len([r for r in self.diff_results if r.status == FileStatus.CONFLICT])
        mtime_count = len([r for r in self.diff_results if r.status == FileStatus.MTIME_DIFF])
        skip_count = len([r for r in self.diff_results 
                         if self.conflict_decisions.get(r.relative_path) == "skip"])
        
        msg = f"确定要执行同步操作吗？\n\n"
        if copy_count > 0:
            msg += f"📋 复制文件: {copy_count} 个\n"
        if delete_count > 0:
            msg += f"🗑️ 删除文件: {delete_count} 个\n"
        if conflict_count > 0:
            msg += f"⚠️ 冲突处理: {conflict_count} 个\n"
        if mtime_count > 0:
            msg += f"⏰ 时间差异: {mtime_count} 个\n"
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
        
        self.table.setRowCount(0)
        self.diff_results = []
        self.conflict_decisions = {}
        
        self.status_label.setText(f"✅ 同步完成 - 成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
        self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
