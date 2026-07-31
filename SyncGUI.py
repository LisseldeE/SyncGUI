"""
SyncGUI - 双端文件同步工具

Author: Lisselde_E
GitHub: https://github.com/LisseldeE
License: MIT
Copyright (c) 2026 Lisselde_E.
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt
from main_window import MainWindow, STYLESHEET, load_config, save_config
from config import Config

# Windows任务栏图标设置
if sys.platform == 'win32':
    import ctypes
    # 设置应用程序ID，确保Windows任务栏正确显示图标
    app_id = f"Lisselde_E.SyncGUI.{Config.DISPLAY_VERSION}"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，兼容打包和未打包两种情况
    
    Args:
        relative_path: 相对路径（如 'icon.ico'）
    
    Returns:
        资源文件的绝对路径
    """
    try:
        # PyInstaller 打包后，会创建临时文件夹，路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except AttributeError:
        # 未打包时，使用当前文件所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def main():
    # 写入版本信息到配置文件（仅在 ENABLE_CHECK_UPDATE=True 时）
    if Config.ENABLE_CHECK_UPDATE:
        try:
            # 获取当前可执行文件路径
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包：exe 完整路径
                exe_path = sys.executable
            else:
                # 开发环境：主脚本路径
                exe_path = os.path.abspath(__file__)

            data = load_config()
            data["version"] = Config.APP_VERSION
            data["exe_path"] = exe_path
            data["app_name"] = Config.APP_NAME
            save_config(data)
        except Exception:
            pass  # 静默失败，不影响程序启动

    # PySide6 默认启用高DPI支持
    # 设置高DPI缩放因子舍入策略，避免150%缩放时界面过大
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLESHEET)
    
    # 设置应用程序信息（确保Windows任务栏图标正确显示）
    app.setApplicationName("SyncGUI")
    app.setApplicationVersion(Config.DISPLAY_VERSION)
    app.setOrganizationName("Lisselde_E")
    
    # 设置应用程序字体，启用抗锯齿
    # 根据系统DPI自动调整字体大小
    font = QFont("Microsoft YaHei", 9)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    
    # 使用 get_resource_path 获取图标路径，兼容打包和未打包情况
    icon_path = get_resource_path('icon.ico')
    
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)
    
    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    
    # Windows任务栏图标设置（必须在窗口显示后）
    if sys.platform == 'win32' and os.path.exists(icon_path):
        try:
            import ctypes
            # 获取GUI窗口句柄
            hwnd = int(window.winId())
            # 加载图标文件
            hicon = ctypes.windll.user32.LoadImageW(
                None, icon_path, 1,  # IMAGE_ICON
                0, 0, 0x10  # LR_LOADFROMFILE
            )
            if hicon:
                # 设置窗口图标
                ctypes.windll.user32.SendMessageW(hwnd, 0x80, 0, hicon)  # WM_SETICON, ICON_SMALL
                ctypes.windll.user32.SendMessageW(hwnd, 0x80, 1, hicon)  # WM_SETICON, ICON_BIG
        except Exception:
            pass
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
