"""
SyncGUI - 本地与移动介质双向文件同步工具

Author: Lisselde_E
GitHub: https://github.com/LisseldeE
Email: Lisselde.E@outlook.com
License: MIT
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt
from main_window import MainWindow, STYLESHEET


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，兼容打包和未打包两种情况
    
    Args:
        relative_path: 相对路径（如 '1.ico'）
    
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
    # 高DPI支持设置（必须在QApplication创建之前设置）
    # 使用PassThrough策略，避免过度缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 设置高DPI缩放因子舍入策略，避免150%缩放时界面过大
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        # PyQt5版本较低时不支持此方法
        pass
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLESHEET)
    
    # 设置应用程序字体，启用抗锯齿
    # 根据系统DPI自动调整字体大小
    font = QFont("Microsoft YaHei", 9)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    
    # 使用 get_resource_path 获取图标路径，兼容打包和未打包情况
    icon_path = get_resource_path('1.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
