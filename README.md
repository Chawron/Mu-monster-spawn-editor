# Monster Spawn Editor for MU Online

A visual editor for managing monster spawns in MU Online game files. Special version for Season 6 by Louis.

## Features
- Visual map editor for monster spawns
- Support for NPCs, monsters, and traps
- Interactive coordinate system
- Search and filter functionality
- Undo/Redo functionality (Ctrl+Z, Ctrl+Y)
- Memory system to retain changes when switching maps
- Coordinate display with improved visibility
- Zoom controls for better navigation (Ctrl+/-, Ctrl+0)
- Automatic directory creation
- Warning when exiting with unsaved changes

## Installation
1. Download the latest release from [Releases](https://github.com/OneAboveAlly/editmonstersetbase/releases)
2. Extract the ZIP file
3. Run `MonsterSpawnEditor.exe`

## Requirements
- Windows 10 or later
- No additional software required

## Usage
1. Select a map from the Map Selection panel
2. Choose a monster from the monster list
3. Click or drag on the map to add spawns
4. Use the quantity and range fields to control spawn properties
5. Select a direction using the direction control
6. Save your changes using File > Save

## Changelog

### Version 1.02
- **Enhanced Map & Image Handling**:
  - improved map file parser to support irregular filenames (e.g., Stadium, Icarus, Land of Trials).
  - Added support for "Swamp of Calmness" rendering using 'Swamp_of_Peace.png'.
  - Added Graceful handling of missing map images (no longer crashes, shows warning).
- **Advanced Spawn Management**:
  - **Stacked Mobs**: Visual indicator `xN` (e.g., `x2`) appears above coordinates with multiple monsters.
  - **Smart Selection**: Clicking a spawn now highlights ONLY that specific instance (raised to top) instead of all mobs of that type.
  - **Quick Edit**: Clicking a point on the map immediately loads its properties (Quantity, Range, etc.) into the editor panel.
  - **Improved List**: "Mobs on Selected Map" list is now sorted by coordinate `(X, Y)` for better grouping and readability.
- **Bug Fixes**:
  - Fixed startup crashes related to missing variables (`status_var`).
  - Fixed `AttributeError` crash when resizing the window.
  - Fixed issue where tooltips showed generic group data instead of specific instance data.

### Version 1.01
- Added Undo/Redo functionality with keyboard shortcuts (Ctrl+Z, Ctrl+Y)
- Implemented memory system for map changes - your edits are now preserved when switching between maps
- Added "Modified*" indicator for maps with unsaved changes
- Added warning dialog when exiting with unsaved changes
- Added ability to edit existing spawns (coordinates, direction, quantity)
- Fixed coordinate mapping to match exactly the coordinates displayed in tooltips
- Added custom program icon visible in both application window and taskbar
- Implemented zoom functionality (Ctrl+/- and Ctrl+0) for better navigation on large maps
- Added automatic creation of required directories if missing (MonsterSetBase, Monster, Images)
- Improved handling of different screen resolutions - better UI scaling
- Added horizontal scrollbars for monster and spawn lists
- Enhanced error handling - protection against division by zero in coordinate calculations
- Added status bar showing current coordinates and scale
- Improved coordinate tooltip visibility with better contrast and positioning

### Version Alpha 0.1
- Basic monster spawn editor functionality
- Ability to add new monster and NPC spawns
- Map and spawn display
- Basic monster stats editing
- Saving changes to MonsterSetBase files

## Development
If you want to build from source:
```bash
pip install -r requirements.txt
python src/monster_spawn_editor.py
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits
- Created by Shizoo
- Original game files from MU Online