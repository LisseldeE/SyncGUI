# SyncGUI - Two-Endpoint File Synchronization Tool

## Project Introduction

SyncGUI is a simple and efficient bidirectional file synchronization tool between two endpoints. It supports intelligent difference detection, multiple sync modes, real-time progress display, providing a smooth user experience. Built with PyQt5 architecture, Windows API efficient file copying, and MD5 hash content comparison.

## Project Information

- **Project Name**: SyncGUI
- **Project Version**: R11
- **Project Author**: Lisselde_E
- **Contact Email**: Lisselde.E@outlook.com
- **Project Repository**: https://github.com/LisseldeE/SyncGUI
- **China Download Mirror**: https://gitee.com/Lisselde_E/SyncGUI (Recommended for users in China)

## Download

- **GitHub Releases**: https://github.com/LisseldeE/SyncGUI/releases
- **Gitee Mirror Download**: https://gitee.com/Lisselde_E/SyncGUI/releases (Recommended for users in China)

## Features

### Core Features

- **Bidirectional Sync** - Supports bidirectional file sync between two endpoints
- **Smart Difference Detection** - Automatically identifies new, modified, and conflicting files
- **Directory-Level Sync** - Configurable directory-level sync to reduce repetitive operations
- **Empty Directory Sync** - Correctly handles empty directories and their structure
- **Symbolic Link Support** - Full support for symbolic link identification and synchronization
- **File Attribute Sync** - Syncs read-only, hidden, system, and other file attributes

### Sync Modes

#### Bidirectional Sync
- **Manual Selection** - Popup for each difference file to ask sync direction
- **Newest First** - Automatically choose newer version to sync, reducing popup prompts

#### Unidirectional Sync
Supports one-way sync between two endpoints, with two sub-modes:

**Diff Sync Mode**:
- Source missing items: Based on "Keep/Delete Extra Items" button
- Target missing items: Automatically fill
- Difference items: If source is newer than target, overwrite; if target is newer than source, ignore

**Overwrite Sync Mode**:
- Source missing items: Based on "Keep/Delete Extra Items" button
- Target missing items: Automatically fill
- Difference items: Ignore timestamps, always source overwrites target

**Extra Items Handling**:
- "Keep Extra Items" (Green): Keep extra files on target side
- "Delete Extra Items" (Red): Delete extra files on target side

### Difference Handling Strategies

| Status | Description |
|--------|-------------|
| One-side Only | Popup to sync to other side or delete |
| Content Conflict | Popup to choose which version to keep |
| Time Difference | Popup to choose overwrite direction |
| Directory Sync | Sync as a whole based on configured rules |

### Custom Names

- Support custom names for two endpoints
- Name configuration auto-saved, restored on next startup
- Click name label to quickly modify display name

### Multi-language Support

- Support Chinese/English interface switching
- Real-time language switching without restarting
- Adapted to multi-language environment

### Interface Optimization

- PyQt5 GUI, simple and intuitive interface
- Unified popup style for intuitive operation
- Support for viewing detailed file lists
- Real-time progress display
- All settings automatically saved, restored on next startup
- Button click animation effect (move down 1px when pressed)
- Mode switch button fade-in/fade-out transition animation (200ms smooth transition)
- Check for updates feature

### Configuration Management

- Configuration file automatically saves user settings
- Configuration path located in AppData, adapted for Microsoft Store environment
- Support ignore rules, sync rules configuration
- Support custom ignore rule syntax

## Usage

1. Run `SyncGUI.exe` or `python main.py`
2. Select two sync directories (customizable names)
3. Click "Scan" to detect file differences
4. Follow popup prompts to choose sync direction (can click "Cancel Sync" to abort)
5. Click "Sync" to execute operations

## Configuration

The configuration file `config.json` automatically saves user settings, no manual modification needed:

```json
{
  "A_dir": "A path",
  "B_dir": "B path",
  "ignore_rules": [
    "SyncGUI/",
    "**/.git/"
  ],
  "sync_rules": [
    "Python/",
    "Servers/"
  ],
  "language": "en",
  "sync_mode": "newest",
  "removable_name": "A",
  "local_name": "B"
}
```

### Configuration Fields

| Field | Description |
|-------|-------------|
| `A_dir` | A endpoint directory path |
| `B_dir` | B endpoint directory path |
| `ignore_rules` | Ignore rules list |
| `sync_rules` | Sync rules list |
| `language` | Interface language (`zh` Chinese / `en` English) |
| `sync_mode` | Sync mode (`default` Manual Selection / `newest` Newest First / `unidirectional` Unidirectional Sync) |
| `removable_name` | A endpoint custom name |
| `local_name` | B endpoint custom name |

### Ignore Rule Syntax

| Rule | Match Scope |
|------|-------------|
| `dirname/` | Only matches specified directory at root |
| `**/dirname/` | Matches specified directory at any location |
| `.extension` | Matches all files with specified extension |

### Sync Rules

After configuring `sync_rules`, first-level subdirectories under specified directories will sync as a whole, reducing file-by-file prompts.

## Technical Implementation

- Python + PyQt5 GUI
- Windows API for efficient file copying
- MD5 hash content comparison
- Progress callback throttling optimization

## System Requirements

- Windows 10/11
- Python 3.8+ (for source code execution)

## Changelog

### R10 (2026.6.27)
**#01**
- Changed config file field names: wintogo_dir → A_dir, local_dir → B_dir
- Configuration file storage path migrated to AppData\\Roaming\\SyncGUI
- Adapted for Microsoft Store MSIX packaging environment sandbox permissions
- Added custom two-endpoint names feature
- Changed "Default Mode" to "Manual Selection"
- Initial startup default mode changed to "Newest First"
- Ignore rules tip added `**/` usage description
- Optimized popup interface style, removed hardcoded background color and text color
- Optimized language switch button size, complete display of icon and text
- Optimized about dialog text size

**#02**
- Fixed missing name suffix when loading config
- Fixed difference list not refreshing after modifying name
- Fixed hardcoded text in difference list status
- Improved all popup interface text display logic

### R10 (2026.6.6)
**#01**
- Added! Unidirectional sync mode and its accessory settings
- Added auto-refresh when switching modes
- Optimized button display logic
- Fixed file path reading logic
- Fixed popup logic and option content during sync
- Fully standardized file sync logic
- Completely refactored the file deletion logic and the handling logic for empty parent directories
- Added missing statistics items in sync confirmation window
- Added transition animation and click effect for interface button elements
- Added check update feature

### R9 (2026.6.4)
**#01**
- Fixed high DPI scaling issue (150% scaling oversized interface)
- Auto-hide sync rules button in Newest First mode
- Adjusted button layout order, mode switch button next to sync button
- Optimized interface display on high-resolution monitors

### R8 (2026.6.4)
**#01**
- Added Chinese/English interface switching
- Adapted all interface elements to English mode
- Added "Newest First" sync mode
- Fixed button display logic, optimized details
- Fixed some interface element update logic
- Updated configuration file structure for new features

### R7 (2026.5.28)
**#01**
- Added `**/` global folder exclusion syntax
- Fixed file attribute loss during sync

### R6 (2026.5.28)
**#01**
- Fixed sync logic exceptions
- Fixed ignore rule handling issues

### R5 (2026.5.28)
**#01**
- Fixed empty folder sync issue
- Unified popup interface style

### R4 (2026.5.16)
**#01**
- Comprehensive sync algorithm optimization
- Fixed multiple popups for large directories

### R3 (2026.5.15)
**#01**
- Fixed configuration path issues

### R2 (2026.5.14)
**#01**
- Added ignore configuration
- Added detailed progress bar
- Updated software name

### R1 (2026.5.13)
**#01**
- Initial build
- Basic sync functionality implemented

## Open Source Declaration

This project uses MIT open source license.

## Contact & Feedback

**This app is under development, if you have questions or new ideas, please contact me!**

- 📧 Email: Lisselde.E@outlook.com
- 🐙 GitHub: https://github.com/LisseldeE/SyncGUI

Welcome to submit Issues and Pull Requests!