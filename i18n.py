"""
SyncGUI - 国际化支持模块

Author: Lisselde_E
GitHub: https://github.com/LisseldeE
Email: Lisselde.E@outlook.com
License: MIT
"""

from typing import Dict


class I18n:
    """国际化管理器"""
    
    # 当前语言
    _current_lang = "zh"
    
    # 翻译字典
    _translations: Dict[str, Dict[str, str]] = {
        "zh": {
            # 窗口标题
            "app_title": "SyncGUI",
            "header_subtitle": "{a} ↔ {b}",
            "header_subtitle_bidirectional": "{a} ↔ {b}",
            "header_subtitle_to_local": "{a} → {b}",
            "header_subtitle_to_removable": "{a} ← {b}",
            
            # 目录设置
            "dir_group": "目录设置",
            "removable_label": "移动介质目录",
            "removable_placeholder": "选择 {name} 上的文件夹路径",
            "local_label": "本地目录",
            "local_placeholder": "选择 {name} 上的文件夹路径",
            "browse": "浏览...",
            "dir_group_title": "目录设置",

            # 目录名称
            "removable_name_default": "A",
            "local_name_default": "B",
            "click_to_rename": "点击名称可自定义",
            "rename_dialog_title": "修改目录名称",
            "rename_old_name": "原名称",
            "rename_new_name": "新名称",
            
            # 按钮
            "scan_btn": "🔄 扫描差异",
            "sync_btn": "▶ 执行同步",
            "ignore_btn": "⚙ 忽略规则",
            "sync_rule_btn": "📁 同步规则",
            "mode_btn": "手动选择",
            "mode_newest": "最新优先",
            "mode_default": "手动选择",
            "language_btn": "🌐 EN",
            
            # 进度和状态
            "status_ready": "就绪 - 请选择两个目录",
            "status_scanning": "正在扫描...",
            "status_comparing": "正在比较...",
            "status_syncing": "正在同步...",
            "status_done": "完成",
            
            # 表格
            "table_group": "差异列表",
            "col_status": "状态",
            "col_path": "文件路径",
            "col_removable_size": "移动介质",
            "col_local_size": "本地",
            "table_group_title": "差异列表",
            "col_operation": "同步操作",
            
            # 状态文本
            "status_same": "相同",
            "status_removable_only": "移动介质独有",
            "status_local_only": "本地独有",
            "status_conflict": "冲突",
            "status_mtime_diff": "时间差异",
            
            # 弹窗标题
            "dialog_conflict": "文件冲突",
            "dialog_diff": "文件差异处理",
            "dialog_mtime": "时间差异处理",
            "dialog_dir_sync": "目录同步",
            "dialog_ignore": "忽略规则设置",
            "dialog_sync_rule": "同步规则设置",
            "dialog_summary": "同步完成",
            
            # 弹窗内容
            "conflict_title": "⚠️ 检测到文件冲突",
            "diff_title": "📄 检测到文件差异",
            "mtime_title": "⏰ 检测到时间差异",
            "dir_sync_title": "📁 目录同步",
            "file_label": "📄 {path}",
            
            # 时间显示
            "removable_time": "移动介质",
            "local_time": "本地",
            "newer_hint": "💡 {side}文件较新",
            
            # 选择选项
            "choice_label": "请选择处理方式：",
            "keep_newest": "✨ 保留最新 ({side}版本)",
            "keep_older": "📜 保留旧版 ({side}版本)",
            "skip_file": "⏭️ 跳过此文件",
            "sync_to_local": "➡️ 同步到本地",
            "sync_to_removable": "➡️ 同步到移动介质",
            "delete_removable": "🗑️ 删除移动介质上的文件",
            "delete_local": "🗑️ 删除本地上的文件",
            "delete_both": "🗑️ 删除两端此文件",
            "sync_newer": "⏰ 同步较新版本",
            "sync_removable": "⏰ 使用移动介质时间",
            "sync_local": "⏰ 使用本地时间",
            
            # 目录同步
            "dir_choice": "请选择同步方向：",
            "dir_to_local": "➡️ 移动介质 → 本地 (覆盖本地)",
            "dir_to_removable": "➡️ 本地 → 移动介质 (覆盖移动介质)",
            "dir_delete_both": "🗑️ 删除两端此目录",
            "apply_dir_files": "📁 同时处理此目录下其他 {count} 个文件",
            "view_detail": "📋 查看详细文件列表",
            
            # 消息框
            "msg_no_diff": "没有需要同步的文件",
            "msg_scan_complete": "扫描完成！发现 {count} 个差异文件",
            "msg_sync_complete": "同步完成！\n成功: {success}\n失败: {fail}\n跳过: {skip}",
            "msg_confirm_sync": "确定要执行同步操作吗？",
            
            # 按钮
            "btn_confirm": "确认",
            "btn_cancel": "取消",
            "btn_close": "关闭",
            "btn_save": "保存",
            "btn_add": "添加",
            "btn_remove": "删除",
            "btn_yes": "是",
            "btn_no": "否",
            "btn_cancel_sync": "❌ 取消本次同步",
            "btn_about": "关于",

            # 手动选择向导
            "wizard_title": "手动选择向导",
            "wizard_progress": "第 {current}/{total} 项",
            "wizard_prev": "上一个",
            "wizard_skip": "跳过此项",
            "wizard_finish": "完成",
            
            # 同步模式
            "sync_type_bidirectional": "双向同步",
            "sync_type_unidirectional": "单向同步",
            "unidirectional_mode_diff": "差异同步",
            "unidirectional_mode_overwrite": "覆盖同步",
            "direction_removable_to_local": "{a} → {b}",
            "direction_local_to_removable": "{b} → {a}",
            "extra_items_keep": "保留多余项目",
            "extra_items_delete": "删除多余项目",
            
            # 关于弹窗
            "about_title": "关于 SyncGUI",
            "about_version_label": "版本",
            "about_author_label": "作者",
            "about_description": "一个简洁高效的双端文件同步工具",
            
            # 检查更新
            "btn_check_update": "检查更新",
            "update_title": "检查更新",
            "update_no_tags": "未找到版本标签",
            "update_version_error": "无法解析当前版本号",
            "update_tag_error": "无法解析远程版本号",
            "update_found": "发现新版本 {version}！\n是否前往下载？",
            "update_latest": "当前已是最新版本",
            "update_network_error": "网络错误：{error}\n请检查网络连接",
            "update_error": "检查更新失败：{error}",
            
            # 忽略规则
            "ignore_title": "当前忽略规则：",
            "ignore_hint": "提示：目录以 / 结尾，扩展名以 . 开头。**/ 可匹配任意层级子目录（如 **/temp/ 匹配所有层级下的temp目录）",
            "ignore_add_placeholder": "输入忽略规则",
            
            # 同步规则
            "sync_rule_title": "当前同步规则：",
            "sync_rule_hint": "提示：配置目录下的第一级子目录将按整体同步",
            "sync_rule_add_placeholder": "输入同步规则",
        },
        "en": {
            # Window title
            "app_title": "SyncGUI",
            "header_subtitle": "{a} ↔ {b}",
            "header_subtitle_bidirectional": "{a} ↔ {b}",
            "header_subtitle_to_local": "{a} → {b}",
            "header_subtitle_to_removable": "{a} ← {b}",
            
            # Directory settings
            "dir_group": "Directory Settings",
            "removable_label": "Removable Media",
            "removable_placeholder": "Select folder path on {name}",
            "local_label": "Local Directory",
            "local_placeholder": "Select folder path on {name}",
            "browse": "Browse...",
            "dir_group_title": "Directory Settings",

            # Directory names
            "removable_name_default": "A",
            "local_name_default": "B",
            "click_to_rename": "Click directory name to rename",
            "rename_dialog_title": "Rename Directory",
            "rename_old_name": "Old Name",
            "rename_new_name": "New Name",
            
            # Buttons
            "scan_btn": "🔄 Scan",
            "sync_btn": "▶ Sync",
            "ignore_btn": "⚙ Ignore Rules",
            "sync_rule_btn": "📁 Sync Rules",
            "mode_btn": "Manual Selection",
            "mode_newest": "Newest First",
            "mode_default": "Manual Selection",
            "language_btn": "🌐 中文",
            
            # Progress and status
            "status_ready": "Ready - Please select two directories",
            "status_scanning": "Scanning...",
            "status_comparing": "Comparing...",
            "status_syncing": "Syncing...",
            "status_done": "Done",
            
            # Table
            "table_group": "Difference List",
            "col_status": "Status",
            "col_path": "File Path",
            "col_removable_size": "Removable",
            "col_local_size": "Local",
            "table_group_title": "Difference List",
            "col_operation": "Sync Operation",
            
            # Status text
            "status_same": "Same",
            "status_removable_only": "Removable Only",
            "status_local_only": "Local Only",
            "status_conflict": "Conflict",
            "status_mtime_diff": "Time Diff",
            
            # Dialog titles
            "dialog_conflict": "File Conflict",
            "dialog_diff": "File Difference",
            "dialog_mtime": "Time Difference",
            "dialog_dir_sync": "Directory Sync",
            "dialog_ignore": "Ignore Rules",
            "dialog_sync_rule": "Sync Rules",
            "dialog_summary": "Sync Complete",
            
            # Dialog content
            "conflict_title": "⚠️ File conflict detected",
            "diff_title": "📄 File difference detected",
            "mtime_title": "⏰ Time difference detected",
            "dir_sync_title": "📁 Directory Sync",
            "file_label": "📄 {path}",
            
            # Time display
            "removable_time": "Removable",
            "local_time": "Local",
            "newer_hint": "💡 {side} file is newer",
            
            # Choice options
            "choice_label": "Choose action:",
            "keep_newest": "✨ Keep newest ({side} version)",
            "keep_older": "📜 Keep older ({side} version)",
            "skip_file": "⏭️ Skip this file",
            "sync_to_local": "➡️ Sync to local",
            "sync_to_removable": "➡️ Sync to removable",
            "delete_removable": "🗑️ Delete file on removable",
            "delete_local": "🗑️ Delete file on local",
            "delete_both": "🗑️ Delete from both sides",
            "sync_newer": "⏰ Sync newer version",
            "sync_removable": "⏰ Use removable time",
            "sync_local": "⏰ Use local time",
            
            # Directory sync
            "dir_choice": "Choose sync direction:",
            "dir_to_local": "➡️ Removable → Local (overwrite local)",
            "dir_to_removable": "➡️ Local → Removable (overwrite removable)",
            "dir_delete_both": "🗑️ Delete this directory from both sides",
            "apply_dir_files": "📁 Also process {count} other files in this directory",
            "view_detail": "📋 View detailed file list",
            
            # Message box
            "msg_no_diff": "No files need to be synced",
            "msg_scan_complete": "Scan complete! Found {count} difference files",
            "msg_sync_complete": "Sync complete!\nSuccess: {success}\nFailed: {fail}\nSkipped: {skip}",
            "msg_confirm_sync": "Are you sure to execute sync?",
            
            # Buttons
            "btn_confirm": "Confirm",
            "btn_cancel": "Cancel",
            "btn_close": "Close",
            "btn_save": "Save",
            "btn_add": "Add",
            "btn_remove": "Remove",
            "btn_yes": "Yes",
            "btn_no": "No",
            "btn_cancel_sync": "❌ Cancel Sync",
            "btn_about": "About",

            # Manual sync wizard
            "wizard_title": "Manual Sync Wizard",
            "wizard_progress": "Item {current}/{total}",
            "wizard_prev": "Previous",
            "wizard_skip": "Skip Item",
            "wizard_finish": "Finish",
            
            # Sync mode
            "sync_type_bidirectional": "Bidirectional Sync",
            "sync_type_unidirectional": "Unidirectional Sync",
            "unidirectional_mode_diff": "Diff Sync",
            "unidirectional_mode_overwrite": "Overwrite Sync",
            "direction_removable_to_local": "{a} → {b}",
            "direction_local_to_removable": "{b} → {a}",
            "extra_items_keep": "Keep Extra Items",
            "extra_items_delete": "Delete Extra Items",
            
            # About dialog
            "about_title": "About SyncGUI",
            "about_version_label": "Version",
            "about_author_label": "Author",
            "about_description": "A simple and efficient dual-endpoint file synchronization tool",
            
            # Check update
            "btn_check_update": "Check Update",
            "update_title": "Check Update",
            "update_no_tags": "No version tags found",
            "update_version_error": "Cannot parse current version number",
            "update_tag_error": "Cannot parse remote version number",
            "update_found": "Found new version {version}!\nDo you want to download?",
            "update_latest": "Current version is up to date",
            "update_network_error": "Network error: {error}\nPlease check your network connection",
            "update_error": "Check update failed: {error}",
            
            # Ignore rules
            "ignore_title": "Current ignore rules:",
            "ignore_hint": "Tip: directories end with /, extensions start with . **/ matches any subdirectory level (e.g., **/temp/ matches temp at all levels)",
            "ignore_add_placeholder": "Enter ignore rule",
            
            # Sync rules
            "sync_rule_title": "Current sync rules:",
            "sync_rule_hint": "Tip: first-level subdirectories under configured directories will sync as a whole",
            "sync_rule_add_placeholder": "Enter sync rule",
        }
    }
    
    @classmethod
    def set_language(cls, lang: str):
        """设置语言"""
        if lang in cls._translations:
            cls._current_lang = lang
    
    @classmethod
    def get_language(cls) -> str:
        """获取当前语言"""
        return cls._current_lang
    
    @classmethod
    def tr(cls, key: str, lang: str = None, **kwargs) -> str:
        """翻译文本
        
        Args:
            key: 翻译键
            lang: 可选的语言代码，如果提供则临时使用该语言翻译
            **kwargs: 格式化参数
        """
        # 如果指定了语言，临时使用该语言的字典
        if lang and lang in cls._translations:
            lang_dict = cls._translations[lang]
        else:
            lang_dict = cls._translations.get(cls._current_lang, cls._translations["zh"])
        
        text = lang_dict.get(key, cls._translations["zh"].get(key, key))
        
        # 格式化参数
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return text
    
    @classmethod
    def get_available_languages(cls) -> list:
        """获取可用语言列表"""
        return list(cls._translations.keys())


# 兼容旧接口
def get_text(key: str, lang: str = None, **kwargs) -> str:
    """获取指定语言的文本（兼容旧接口）"""
    if lang:
        I18n.set_language(lang)
    return I18n.tr(key, **kwargs)


LANGUAGES = I18n._translations