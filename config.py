"""
SyncGUI 配置文件

Copyright (c) 2026 Lisselde_E.
"""

class Config:
    """应用配置"""

    # 应用信息
    APP_NAME = "SyncGUI"
    APP_VERSION = "R11.7" 
    STORE_VERSION = "11.7.0.0"
    APP_AUTHOR = "Lisselde_E"
    APP_AUTHOR_LINK = "https://lisseldee.github.io/#2"

    # 功能开关
    # True = 开源直装版，False = 微软商店版
    ENABLE_CHECK_UPDATE = True

    # 显示用版本号：微软商店版显示四段式版本号，开源直装版显示 Rxx 内部版本号
    DISPLAY_VERSION = STORE_VERSION if not ENABLE_CHECK_UPDATE else APP_VERSION

    # 仓库信息
    GITHUB_REPO = "LisseldeE/SyncGUI"
    GITEE_REPO = "Lisselde_E/SyncGUI"

    # 版本号托管于 GitHub Pages 纯文本文件，避免 raw 外链滥用/API tags 频率限制
    UPDATE_URL = "https://lisseldee.github.io/version/syncgui"
    # 下载落地页（按语言区分，保持不变）
    GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases"
    GITEE_RELEASES = f"https://gitee.com/{GITEE_REPO}/releases"