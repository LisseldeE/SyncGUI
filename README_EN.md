# SyncGUI - Two-Endpoint File Synchronization Tool

## Project Introduction

SyncGUI is a simple and efficient dual-endpoint file synchronization tool. It supports intelligent difference detection, multiple sync modes, real-time progress display, providing a smooth user experience. Built with Pyside6 architecture, Windows API efficient file copying, and MD5 hash content comparison.

## Project Information

- **Project Name**: SyncGUI
- **Project Author**: Lisselde_E
- **Project Repository**: https://github.com/LisseldeE/SyncGUI

## Download
<a href="https://apps.microsoft.com/detail/9ncs5fmkwq6l?referrer=appbadge&mode=full" target="_blank"  rel="noopener noreferrer">
	<img src="https://get.microsoft.com/images/en-us%20dark.svg" width="200"/>
</a>

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

- PySide6 GUI, simple and intuitive interface
- Unified popup style for intuitive operation
- Support for viewing detailed file lists
- Real-time progress display
- All settings automatically saved, restored on next startup
- Button click animation effect (move down 1px when pressed)
- Mode switch button fade-in/fade-out transition animation (200ms smooth transition)
- Check for updates feature

### Configuration Management

- Configuration file automatically saves user settings
- Configuration path located in user directory (e.g., C:\Users\Username\SyncGUI)
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

- Python + PySide6 GUI
- Windows API for efficient file copying
- MD5 hash content comparison
- Progress callback throttling optimization

## System Requirements

- Windows 10/11
- Python 3.8+ (for source code execution)

## Changelog

### R11 (2026.6.27)

**#06**
- Changed configuration file save path to avoid using MSIX virtual environment

See: [CHANGELOG.md](https://github.com/LisseldeE/SyncGUI/blob/main/CHANGELOG.md)

## Open Source Declaration

This project uses MIT open source license.

## Contact & Feedback

**This app is under development, if you have questions or new ideas, please contact me!**

Welcome to submit Issues and Pull Requests!