# SyncGUI

A simple and efficient bidirectional file synchronization tool between local storage and removable media.

**Version**: SyncGUI_R10

## Author

- **Author**: Lisselde_E
- **GitHub**: [https://github.com/LisseldeE](https://github.com/LisseldeE)
- **Email**: Lisselde.E@outlook.com

## Features

### Core Features

- **Bidirectional Sync** - Supports bidirectional file sync between local and removable media
- **Smart Difference Detection** - Automatically identifies new, modified, and conflicting files
- **Directory-Level Sync** - Configurable directory-level sync to reduce repetitive operations
- **Empty Directory Sync** - Correctly handles empty directories and their structure
- **Symbolic Link Support** - Full support for symbolic link identification and synchronization
- **File Attribute Sync** - Syncs read-only, hidden, system, and other file attributes

### Sync Strategies

| Status | Description |
|--------|-------------|
| One-side Only | Popup to sync to other side or delete |
| Content Conflict | Popup to choose which version to keep |
| Time Difference | Popup to choose overwrite direction |
| Directory Sync | Sync as a whole based on configured rules |

### Configuration

The configuration file `config.json` automatically saves user settings, no manual modification needed:

```json
{
  "wintogo_dir": "Removable media path",
  "local_dir": "Local path",
  "ignore_rules": [
    "SyncGUI/",
    "**/.git/"
  ],
  "sync_rules": [
    "Python/",
    "Servers/"
  ],
  "language": "en",
  "sync_mode": "default"
}
```

#### Configuration Fields

| Field | Description |
|-------|-------------|
| `wintogo_dir` | Removable media directory path |
| `local_dir` | Local directory path |
| `ignore_rules` | Ignore rules list |
| `sync_rules` | Sync rules list |
| `language` | Interface language (`zh` Chinese / `en` English) |
| `sync_mode` | Sync mode (`default` Default / `newest` Newest First / `unidirectional` Unidirectional Sync) |

#### Ignore Rule Syntax

| Rule | Match Scope |
|------|-------------|
| `dirname/` | Only matches specified directory at root |
| `**/dirname/` | Matches specified directory at any location |
| `.extension` | Matches all files with specified extension |

#### Sync Rules

After configuring `sync_rules`, first-level subdirectories under specified directories will sync as a whole, reducing file-by-file prompts.

## Usage

1. Run `SyncGUI.exe` or `python main.py`
2. Select removable media directory and local directory
3. Click "Scan" to detect file differences
4. Follow popup prompts to choose sync direction (can click "Cancel Sync" to abort)
5. Click "Sync" to execute operations

### Sync Modes

- **Default Mode** - Popup for each difference file to ask sync direction
- **Newest First** - Automatically choose newer version to sync, reducing popup prompts
- **Unidirectional Sync** - Supports one-way sync from removable to local or local to removable, with diff/overwrite mode options, and keep/delete extra items toggle

## Interface

- Main window displays scan progress and difference statistics
- Unified popup style for intuitive operation
- Support for viewing detailed file lists
- Support Chinese/English interface switching (click language button)
- All settings automatically saved, restored on next startup

## Technical Implementation

- Python + PyQt5 GUI
- Windows API for efficient file copying
- MD5 hash content comparison
- Progress callback throttling optimization

## System Requirements

- Windows 10/11
- Python 3.8+ (for source code execution)

## Changelog

### R10 (2026.6.6)
- Added! Unidirectional sync mode and its accessory settings
- Added auto-refresh when switching modes
- Optimized button display logic
- Fixed file path reading logic
- Fixed popup logic and option content during sync
- Fully standardized file sync logic
- Completely refactored the file deletion logic and the handling logic for empty parent directories

### R9 (2026.6.4)
- Fixed high DPI scaling issue (150% scaling oversized interface)
- Auto-hide sync rules button in Newest First mode
- Adjusted button layout order, mode switch button next to sync button
- Optimized interface display on high-resolution monitors

### R8 (2026.6.4)
- Added Chinese/English interface switching
- Adapted all interface elements to English mode
- Added "Newest First" sync mode
- Fixed button display logic, optimized details
- Fixed some interface element update logic
- Updated configuration file structure for new features

### R7 (2026.5.28)
- Added `**/` global folder exclusion syntax
- Fixed file attribute loss during sync

### R6 (2026.5.28)
- Fixed sync logic exceptions
- Fixed ignore rule handling issues

### R5 (2026.5.28)
- Fixed empty folder sync issue
- Unified popup interface style

### R4 (2026.5.16)
- Comprehensive sync algorithm optimization
- Fixed multiple popups for large directories

### R3 (2026.5.15)
- Fixed configuration path issues

### R2 (2026.5.14)
- Added ignore configuration
- Added detailed progress bar
- Updated software name

### R1 (2026.5.13)
- Initial build
- Basic sync functionality implemented

## License

MIT License