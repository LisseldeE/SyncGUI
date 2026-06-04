# 语言配置文件

LANGUAGES = {
    "zh": {
        # 窗口标题
        "app_title": "SyncGUI",
        "header_subtitle": "移动介质 ↔ 本地",
        
        # 目录设置
        "dir_group": "目录设置",
        "removable_label": "移动介质目录",
        "removable_placeholder": "选择移动介质上的文件夹路径",
        "local_label": "本地目录",
        "local_placeholder": "选择本地电脑上的文件夹路径",
        "browse": "浏览...",
        
        # 按钮
        "scan_btn": "🔄 扫描差异",
        "sync_btn": "▶ 执行同步",
        "ignore_btn": "⚙ 忽略规则",
        "sync_rule_btn": "📁 同步规则",
        "mode_btn": "📋 默认模式",
        "mode_newest": "📋 最新优先",
        "mode_default": "📋 默认模式",
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
        
        # 忽略规则
        "ignore_title": "当前忽略规则：",
        "ignore_hint": "提示：目录以 / 结尾，扩展名以 . 开头",
        "ignore_add_placeholder": "输入忽略规则",
        
        # 同步规则
        "sync_rule_title": "当前同步规则：",
        "sync_rule_hint": "提示：配置目录下的第一级子目录将按整体同步",
        "sync_rule_add_placeholder": "输入同步规则",
    },
    "en": {
        # Window title
        "app_title": "SyncGUI",
        "header_subtitle": "Removable ↔ Local",
        
        # Directory settings
        "dir_group": "Directory Settings",
        "removable_label": "Removable Media",
        "removable_placeholder": "Select folder path on removable media",
        "local_label": "Local Directory",
        "local_placeholder": "Select folder path on local computer",
        "browse": "Browse...",
        
        # Buttons
        "scan_btn": "🔄 Scan",
        "sync_btn": "▶ Sync",
        "ignore_btn": "⚙ Ignore Rules",
        "sync_rule_btn": "📁 Sync Rules",
        "mode_btn": "📋 Default Mode",
        "mode_newest": "📋 Newest First",
        "mode_default": "📋 Default Mode",
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
        
        # Ignore rules
        "ignore_title": "Current ignore rules:",
        "ignore_hint": "Tip: directories end with /, extensions start with .",
        "ignore_add_placeholder": "Enter ignore rule",
        
        # Sync rules
        "sync_rule_title": "Current sync rules:",
        "sync_rule_hint": "Tip: first-level subdirectories under configured directories will sync as a whole",
        "sync_rule_add_placeholder": "Enter sync rule",
    }
}

def get_text(key: str, lang: str = "zh", **kwargs) -> str:
    """获取指定语言的文本"""
    texts = LANGUAGES.get(lang, LANGUAGES["zh"])
    text = texts.get(key, LANGUAGES["zh"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text