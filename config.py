"""
SyncGUI 配置文件
"""

class Config:
    """应用配置"""

    # 应用信息
    APP_NAME = "SyncGUI"
    APP_VERSION = "R11"
    APP_AUTHOR = "Lisselde_E"
    APP_EMAIL = "Lisselde.E@outlook.com"

    # 功能开关
    # 检查更新按钮：True=显示（GitHub 版本），False=隐藏（微软商店版本）
    ENABLE_CHECK_UPDATE = True

    # 仓库信息
    GITHUB_REPO = "LisseldeE/SyncGUI"
    GITEE_REPO = "Lisselde_E/SyncGUI"

    # API 端点
    GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
    GITEE_API = f"https://gitee.com/api/v5/repos/{GITEE_REPO}/tags"
    GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases"
    GITEE_RELEASES = f"https://gitee.com/{GITEE_REPO}/releases"