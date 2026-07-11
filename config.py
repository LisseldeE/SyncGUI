"""
SyncGUI 配置文件
"""

class Config:
    """应用配置"""

    # 应用信息
    APP_NAME = "SyncGUI"
    APP_VERSION = "R11.6" 
    STORE_VERSION = "11.6.1.0"
    APP_AUTHOR = "Lisselde_E"
    APP_AUTHOR_LINK = "https://lisseldee.github.io"

    # 功能开关
    # True = 开源直装版，False = 微软商店版
    ENABLE_CHECK_UPDATE = False

    # 显示用版本号：微软商店版显示四段式版本号，开源直装版显示 Rxx 内部版本号
    DISPLAY_VERSION = STORE_VERSION if not ENABLE_CHECK_UPDATE else APP_VERSION

    # 仓库信息
    GITHUB_REPO = "LisseldeE/SyncGUI"
    GITEE_REPO = "Lisselde_E/SyncGUI"

    # API 端点
    GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
    GITEE_API = f"https://gitee.com/api/v5/repos/{GITEE_REPO}/tags"
    GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases"
    GITEE_RELEASES = f"https://gitee.com/{GITEE_REPO}/releases"