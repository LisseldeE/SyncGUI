import sys
import os
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QProgressBar, QMessageBox, QHeaderView,
    QDialog, QDialogButtonBox, QGroupBox, QRadioButton, QButtonGroup,
    QFrame, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette

from sync_core import (
    scan_directory, compare_files, sync_file,
    FileStatus, DiffResult
)


CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')


class CustomMessageBox(QDialog):
    def __init__(self, title: str, message: str, msg_type: str = "info", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.msg_type = msg_type
        self._init_ui(title, message)
    
    def _init_ui(self, title: str, message: str):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #495057;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        icon_map = {
            "warning": ("⚠️", "#e67700"),
            "error": ("❌", "#e03131"),
            "info": ("ℹ️", "#1971c2"),
            "success": ("✅", "#2f9e44"),
            "question": ("❓", "#1971c2")
        }
        
        icon, color = icon_map.get(self.msg_type, ("ℹ️", "#1971c2"))
        
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        msg_label = QLabel(message)
        msg_label.setStyleSheet("font-size: 14px; line-height: 1.5;")
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(msg_label)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if self.msg_type == "question":
            self.yes_btn = QPushButton("确认")
            self.yes_btn.setFixedSize(100, 38)
            self.yes_btn.setStyleSheet("""
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
            self.yes_btn.clicked.connect(self.accept)
            
            self.no_btn = QPushButton("取消")
            self.no_btn.setFixedSize(100, 38)
            self.no_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fa5252;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #f03e3e;
                }
                QPushButton:pressed {
                    background-color: #e03131;
                }
            """)
            self.no_btn.clicked.connect(self.reject)
            
            btn_layout.addWidget(self.yes_btn)
            btn_layout.addSpacing(12)
            btn_layout.addWidget(self.no_btn)
        else:
            self.ok_btn = QPushButton("完成")
            self.ok_btn.setFixedSize(100, 38)
            self.ok_btn.setStyleSheet("""
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
            self.ok_btn.clicked.connect(self.accept)
            btn_layout.addWidget(self.ok_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    @staticmethod
    def warning(parent, title: str, message: str):
        dialog = CustomMessageBox(title, message, "warning", parent)
        return dialog.exec_()
    
    @staticmethod
    def information(parent, title: str, message: str):
        dialog = CustomMessageBox(title, message, "info", parent)
        return dialog.exec_()
    
    @staticmethod
    def success(parent, title: str, message: str):
        dialog = CustomMessageBox(title, message, "success", parent)
        return dialog.exec_()
    
    @staticmethod
    def question(parent, title: str, message: str):
        dialog = CustomMessageBox(title, message, "question", parent)
        if dialog.exec_() == QDialog.Accepted:
            return QMessageBox.Yes
        return QMessageBox.No


STYLESHEET = """
QMainWindow {
    background-color: #f8f9fa;
}
QGroupBox {
    font-weight: bold;
    font-size: 13px;
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
}
QLineEdit:focus {
    border: 2px solid #4dabf7;
}
QPushButton {
    padding: 10px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
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
    
    def __init__(self, wintogo_dir: str, local_dir: str):
        super().__init__()
        self.wintogo_dir = wintogo_dir
        self.local_dir = local_dir
    
    def run(self):
        wintogo_files = scan_directory(self.wintogo_dir, self._progress_callback)
        local_files = scan_directory(self.local_dir, self._progress_callback)
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
    progress = pyqtSignal(int, int, str)
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
        total = len(to_sync)
        
        for idx, diff in enumerate(to_sync):
            self.progress.emit(idx + 1, total, diff.relative_path)
            
            if diff.status == FileStatus.WINTOGO_ONLY:
                if sync_file(diff, self.wintogo_dir, self.local_dir, "to_local"):
                    success_count += 1
                else:
                    fail_count += 1
            elif diff.status == FileStatus.LOCAL_ONLY:
                if sync_file(diff, self.wintogo_dir, self.local_dir, "to_wintogo"):
                    success_count += 1
                else:
                    fail_count += 1
            elif diff.status == FileStatus.CONFLICT:
                decision = self.conflict_decisions.get(diff.relative_path, "skip")
                if decision == "skip":
                    skip_count += 1
                elif sync_file(diff, self.wintogo_dir, self.local_dir, decision):
                    success_count += 1
                else:
                    fail_count += 1
        
        self.finished.emit(success_count, fail_count, skip_count)


class ConflictDialog(QDialog):
    def __init__(self, diff: DiffResult, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件冲突")
        self.result_direction = None
        self.setMinimumWidth(480)
        
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
        
        title_label = QLabel("⚠️ 检测到文件冲突")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e03131;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line)
        
        file_label = QLabel(f"📄 {diff.relative_path}")
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
        wintogo_title = QLabel("WinToGo")
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
        local_title = QLabel("本地")
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
        
        newer = "WinToGo" if self.wintogo_newer else "本地"
        hint_label = QLabel(f"💡 {newer}文件较新")
        hint_label.setStyleSheet("color: #fd7e14; font-size: 13px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(line2)
        
        choice_label = QLabel("请选择处理方式：")
        choice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(choice_label)
        
        self.button_group = QButtonGroup(self)
        
        self.rb_newer = QRadioButton()
        self.rb_older = QRadioButton()
        self.rb_skip = QRadioButton("⏭️ 跳过此文件")
        
        if self.wintogo_newer:
            self.rb_newer.setText("✨ 保留最新 (WinToGo版本)")
            self.rb_older.setText("📜 保留旧版 (本地版本)")
        else:
            self.rb_newer.setText("✨ 保留最新 (本地版本)")
            self.rb_older.setText("📜 保留旧版 (WinToGo版本)")
        
        self.rb_newer.setChecked(True)
        
        self.button_group.addButton(self.rb_newer, 0)
        self.button_group.addButton(self.rb_older, 1)
        self.button_group.addButton(self.rb_skip, 2)
        
        layout.addWidget(self.rb_newer)
        layout.addWidget(self.rb_older)
        layout.addWidget(self.rb_skip)
        
        layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        confirm_btn = QPushButton("确认")
        confirm_btn.setFixedSize(100, 38)
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
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #fa5252;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f03e3e;
            }
            QPushButton:pressed {
                background-color: #e03131;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(confirm_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件同步器")
        self.setMinimumSize(1000, 700)
        
        self.wintogo_files = {}
        self.local_files = {}
        self.diff_results = []
        self.conflict_decisions = {}
        self.auto_scan_timer = None
        
        self._init_ui()
        self._load_saved_paths()
    
    def _init_ui(self):
        self.setStyleSheet(STYLESHEET)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        header_layout = QHBoxLayout()
        title_label = QLabel("📁 文件同步器")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #212529;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        version_label = QLabel("WinToGo ↔ 本地")
        version_label.setStyleSheet("color: #868e96; font-size: 13px;")
        header_layout.addWidget(version_label)
        layout.addLayout(header_layout)
        
        dir_group = QGroupBox("目录设置")
        dir_layout = QVBoxLayout(dir_group)
        dir_layout.setSpacing(12)
        dir_layout.setContentsMargins(16, 20, 16, 16)
        
        label_width = 100
        
        wintogo_layout = QHBoxLayout()
        wintogo_label = QLabel("WinToGo 目录")
        wintogo_label.setFixedWidth(label_width)
        wintogo_label.setStyleSheet("font-size: 13px; color: #495057;")
        wintogo_layout.addWidget(wintogo_label)
        self.wintogo_edit = QLineEdit()
        self.wintogo_edit.setPlaceholderText("选择 WinToGo 上的文件夹路径")
        self.wintogo_edit.textChanged.connect(self._on_path_changed)
        wintogo_layout.addWidget(self.wintogo_edit)
        self.wintogo_btn = QPushButton("浏览...")
        self.wintogo_btn.setObjectName("browseBtn")
        self.wintogo_btn.setFixedWidth(90)
        self.wintogo_btn.clicked.connect(self._select_wintogo)
        wintogo_layout.addWidget(self.wintogo_btn)
        dir_layout.addLayout(wintogo_layout)
        
        local_layout = QHBoxLayout()
        local_label = QLabel("本地目录")
        local_label.setFixedWidth(label_width)
        local_label.setStyleSheet("font-size: 13px; color: #495057;")
        local_layout.addWidget(local_label)
        self.local_edit = QLineEdit()
        self.local_edit.setPlaceholderText("选择本地电脑上的文件夹路径")
        self.local_edit.textChanged.connect(self._on_path_changed)
        local_layout.addWidget(self.local_edit)
        self.local_btn = QPushButton("浏览...")
        self.local_btn.setObjectName("browseBtn")
        self.local_btn.setFixedWidth(90)
        self.local_btn.clicked.connect(self._select_local)
        local_layout.addWidget(self.local_btn)
        dir_layout.addLayout(local_layout)
        
        layout.addWidget(dir_group)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.scan_btn = QPushButton("🔄 扫描差异")
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.setFixedHeight(44)
        self.scan_btn.setFixedWidth(140)
        self.scan_btn.clicked.connect(self._start_scan)
        btn_layout.addWidget(self.scan_btn)
        
        self.sync_btn = QPushButton("▶ 执行同步")
        self.sync_btn.setObjectName("syncBtn")
        self.sync_btn.setFixedHeight(44)
        self.sync_btn.setFixedWidth(140)
        self.sync_btn.clicked.connect(self._execute_sync)
        self.sync_btn.setEnabled(False)
        btn_layout.addWidget(self.sync_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(28)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪 - 请选择两个目录")
        self.status_label.setStyleSheet("color: #868e96; font-size: 13px; padding: 4px 0;")
        layout.addWidget(self.status_label)
        
        table_group = QGroupBox("差异列表")
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(16, 20, 16, 16)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "文件路径", "状态", "WinToGo大小", "本地大小", "同步操作"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
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
        
        if wintogo_path:
            self.wintogo_edit.setText(wintogo_path)
        if local_path:
            self.local_edit.setText(local_path)
    
    def _save_paths(self):
        config = {
            'wintogo_dir': self.wintogo_edit.text().strip(),
            'local_dir': self.local_edit.text().strip()
        }
        save_config(config)
    
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
            CustomMessageBox.warning(self, "警告", "请选择 WinToGo 目录和本地目录")
            return
        
        if wintogo_dir == local_dir:
            CustomMessageBox.warning(self, "警告", "WinToGo 目录和本地目录不能相同")
            return
        
        if not os.path.exists(wintogo_dir):
            CustomMessageBox.warning(self, "警告", "WinToGo 目录不存在")
            return
        
        if not os.path.exists(local_dir):
            CustomMessageBox.warning(self, "警告", "本地目录不存在")
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
        
        self.scan_worker = ScanWorker(wintogo_dir, local_dir)
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
        
        conflicts = [r for r in results if r.status == FileStatus.CONFLICT]
        sync_needed = [r for r in results if r.status != FileStatus.SAME]
        
        if sync_needed:
            self.sync_btn.setEnabled(True)
            if conflicts:
                self.status_label.setText(f"⚠️ 发现 {len(sync_needed)} 个差异项，其中 {len(conflicts)} 个冲突需要处理")
                self.status_label.setStyleSheet("color: #e67700; font-size: 13px; padding: 4px 0;")
            else:
                self.status_label.setText(f"📋 发现 {len(sync_needed)} 个差异项，将自动同步")
                self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
        else:
            self.status_label.setText("✅ 两个目录完全一致，无需同步")
            self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
    
    def _update_table(self):
        self.table.setRowCount(0)
        
        status_map = {
            FileStatus.WINTOGO_ONLY: ("WinToGo独有", QColor(227, 245, 255)),
            FileStatus.LOCAL_ONLY: ("本地独有", QColor(235, 251, 238)),
            FileStatus.SAME: ("相同", QColor(248, 249, 250)),
            FileStatus.CONFLICT: ("冲突", QColor(255, 243, 214)),
        }
        
        action_map = {
            FileStatus.WINTOGO_ONLY: "自动: 复制到本地",
            FileStatus.LOCAL_ONLY: "自动: 复制到WinToGo",
            FileStatus.SAME: "无操作",
            FileStatus.CONFLICT: "待选择",
        }
        
        for diff in self.diff_results:
            if diff.status == FileStatus.SAME:
                continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            path_item = QTableWidgetItem(diff.relative_path)
            path_item.setForeground(QColor("#495057"))
            self.table.setItem(row, 0, path_item)
            
            status_text, color = status_map[diff.status]
            status_item = QTableWidgetItem(status_text)
            status_item.setBackground(color)
            self.table.setItem(row, 1, status_item)
            
            wintogo_size = ""
            if diff.wintogo_info:
                wintogo_size = self._format_size(diff.wintogo_info.size)
            self.table.setItem(row, 2, QTableWidgetItem(wintogo_size))
            
            local_size = ""
            if diff.local_info:
                local_size = self._format_size(diff.local_info.size)
            self.table.setItem(row, 3, QTableWidgetItem(local_size))
            
            action_text = action_map[diff.status]
            if diff.status == FileStatus.CONFLICT and diff.relative_path in self.conflict_decisions:
                decision = self.conflict_decisions[diff.relative_path]
                if decision == "skip":
                    action_text = "跳过"
                else:
                    wintogo_newer = diff.wintogo_info.mtime > diff.local_info.mtime
                    if decision == "wintogo_to_local":
                        action_text = "保留最新" if wintogo_newer else "保留旧版"
                    else:
                        action_text = "保留旧版" if wintogo_newer else "保留最新"
            
            action_item = QTableWidgetItem(action_text)
            if diff.status == FileStatus.CONFLICT:
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
    
    def _execute_sync(self):
        conflicts = [r for r in self.diff_results if r.status == FileStatus.CONFLICT]
        
        for diff in conflicts:
            if diff.relative_path not in self.conflict_decisions:
                dialog = ConflictDialog(diff, self)
                if dialog.exec_() == QDialog.Accepted:
                    self.conflict_decisions[diff.relative_path] = dialog.get_direction()
                else:
                    self.conflict_decisions[diff.relative_path] = "skip"
        
        self._update_table()
        
        auto_count = len([r for r in self.diff_results if r.status in (FileStatus.WINTOGO_ONLY, FileStatus.LOCAL_ONLY)])
        conflict_count = len([r for r in self.diff_results if r.status == FileStatus.CONFLICT])
        
        msg = f"确定要执行同步操作吗？\n\n"
        msg += f"📁 自动同步: {auto_count} 个文件\n"
        msg += f"⚠️ 冲突处理: {conflict_count} 个文件\n\n"
        msg += "此操作不可撤销！"
        
        reply = CustomMessageBox.question(self, "确认同步", msg)
        
        if reply != QMessageBox.Yes:
            return
        
        wintogo_dir = self.wintogo_edit.text().strip()
        local_dir = self.local_edit.text().strip()
        
        self.sync_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("同步中... %p%")
        self.status_label.setText("📤 正在同步文件...")
        self.status_label.setStyleSheet("color: #1971c2; font-size: 13px; padding: 4px 0;")
        
        self.sync_worker = SyncWorker(
            self.diff_results, self.conflict_decisions,
            wintogo_dir, local_dir
        )
        self.sync_worker.progress.connect(self._on_sync_progress)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.start()
    
    def _on_sync_progress(self, current: int, total: int, filename: str):
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))
        self.status_label.setText(f"📤 正在同步: {filename}")
    
    def _on_sync_finished(self, success_count: int, fail_count: int, skip_count: int):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        
        self.status_label.setText(f"✅ 同步完成 - 成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
        self.status_label.setStyleSheet("color: #2f9e44; font-size: 13px; padding: 4px 0;")
        
        CustomMessageBox.success(
            self, "同步完成",
            f"同步完成！\n\n✅ 成功: {success_count}\n❌ 失败: {fail_count}\n⏭️ 跳过: {skip_count}"
        )
        
        QTimer.singleShot(500, self._start_scan)
