# SyncGUI

A simple and efficient bidirectional file synchronization tool between local storage and removable media.

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

```json
{
  "source_dir": "Local path",
  "target_dir": "Removable media path",
  "ignore_rules": [
    "SyncGUI/",
    "**/.git/"
  ],
  "sync_rules": [
    "Python/",
    "Servers/"
  ]
}
```

#### Ignore Rule Syntax

| Rule | Match Scope |
|------|-------------|
| `dirname/` | Only matches specified directory at root |
| `**/dirname/` | Matches specified directory at any location |
| `.extension` | Matches all files with specified extension |

#### Sync Rules

After configuring `sync_rules`, first-level subdirectories under specified directories will sync as a whole, reducing file-by-file prompts.

## Usage

1. Modify `config.json` to set sync paths
2. Run `SyncGUI.exe` or `python main.py`
3. Click "Scan" to detect differences
4. Follow popup prompts to choose sync direction
5. Click "Sync" to execute operations

## Interface

- Main window displays scan progress and difference statistics
- Unified popup style for intuitive operation
- Support for viewing detailed file lists

## Technical Implementation

- Python + PyQt5 GUI
- Windows API for efficient file copying
- MD5 hash content comparison
- Progress callback throttling optimization

## System Requirements

- Windows 10/11
- Python 3.8+ (for source code execution)

## Changelog

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